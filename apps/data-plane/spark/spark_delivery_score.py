"""Spark Structured Streaming job that scores delivery providers by ZIP code."""
from __future__ import annotations

import os

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.avro.functions import from_avro

from .utils import load_avro_schema

APP_NAME = "prep-delivery-score"
KAFKA_TOPIC = "delivery.status"
KAFKA_GROUP_ID = "spark-delivery-score"
CHECKPOINT_BASE = os.getenv("CHECKPOINT_BASE", "s3://prep-checkpoints/spark")
CHECKPOINT_LOCATION = f"{CHECKPOINT_BASE}/delivery-score/"
KAFKA_CHECKPOINT_LOCATION = f"{CHECKPOINT_BASE}/delivery-score-kafka/"
REDIS_EXPIRY_SECONDS = int(os.getenv("REDIS_EXPIRY_SECONDS", "600"))


def build_spark_session() -> SparkSession:
    return (
        SparkSession.builder.appName(APP_NAME)
        .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE_PARTITIONS", "400"))
        .getOrCreate()
    )


def read_delivery_status(spark: SparkSession):
    return (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", os.getenv("KAFKA_BROKERS"))
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", os.getenv("KAFKA_STARTING_OFFSETS", "latest"))
        .option("kafka.group.id", KAFKA_GROUP_ID)
        .load()
    )


def deserialize_delivery_status(df):
    schema = load_avro_schema("prep.delivery.DeliveryStatus")
    value = from_avro(F.col("value"), schema)
    return df.select(value.alias("payload"), F.col("key")).select("payload.*", "key")


def compute_kpis(df):
    delivered = F.when(F.col("status") == "DELIVERED", F.lit(1)).otherwise(F.lit(0))
    aggregated = (
        df.withWatermark("ts_event", "10 minutes")
        .groupBy("provider", "zip", F.window("ts_event", "5 minutes", "1 minute"))
        .agg(
            F.avg("latency_ms").alias("p50_latency_ms"),
            F.expr("percentile_approx(latency_ms, 0.95)").alias("p95_latency_ms"),
            F.sum(delivered).alias("delivered_count"),
            F.count(F.lit(1)).alias("event_count"),
            F.avg("cost_cents").alias("avg_cost_cents"),
        )
    )
    return aggregated.select(
        "provider",
        "zip",
        "window",
        "p50_latency_ms",
        "p95_latency_ms",
        F.col("delivered_count"),
        F.col("event_count"),
        "avg_cost_cents",
        F.when(F.col("event_count") > 0, F.col("delivered_count") / F.col("event_count"))
        .otherwise(F.lit(None))
        .alias("success_rate"),
    )


def score_kpis(df):
    latency_component = 1 - (F.col("p95_latency_ms") / 1000.0)
    cost_component = 1 - (F.col("avg_cost_cents") / 1000.0)
    return df.select(
        "provider",
        "zip",
        F.col("window.start").alias("window_start"),
        F.col("window.end").alias("window_end"),
        "p50_latency_ms",
        "p95_latency_ms",
        "success_rate",
        "avg_cost_cents",
        (
            0.6 * F.col("success_rate")
            + 0.3 * latency_component
            + 0.1 * cost_component
        ).alias("score"),
    )


def write_redis(batch_df, _):
    import redis

    cluster = redis.RedisCluster(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )
    for row in batch_df.collect():
        key = f"routing:{row['zip']}"
        cluster.hset(key, row["provider"], row["score"])
        cluster.expire(key, REDIS_EXPIRY_SECONDS)


def start_sinks(scored_df):
    redis_query = (
        scored_df.writeStream.outputMode("update").foreachBatch(write_redis).option(
            "checkpointLocation", CHECKPOINT_LOCATION
        ).start()
    )

    kafka_payload = scored_df.select(
        F.concat(F.col("zip"), F.lit(":"), F.col("provider")).alias("key"),
        F.to_json(F.struct(*scored_df.columns)).alias("value"),
    )

    kafka_query = (
        kafka_payload.writeStream.format("kafka")
        .option("kafka.bootstrap.servers", os.getenv("KAFKA_BROKERS"))
        .option("topic", "optimizer.features.routing")
        .option("checkpointLocation", KAFKA_CHECKPOINT_LOCATION)
        .start()
    )

    return redis_query, kafka_query


def main():
    spark = build_spark_session()
    source_df = read_delivery_status(spark)
    deserialized = deserialize_delivery_status(source_df)
    kpis = compute_kpis(deserialized)
    scored = score_kpis(kpis)
    queries = start_sinks(scored)
    spark.streams.awaitAnyTermination()
    for query in queries:
        query.awaitTermination()


if __name__ == "__main__":
    main()
