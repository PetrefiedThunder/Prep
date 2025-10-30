"""Spark Structured Streaming job for POS reconciliation and feature extraction."""
from __future__ import annotations

import os

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.avro.functions import from_avro

from .utils import ge_validate, load_avro_schema

APP_NAME = "prep-pos-recon"
KAFKA_TOPIC = "pos.transactions"
KAFKA_GROUP_ID = "spark-recon"
CHECKPOINT_BASE = os.getenv("CHECKPOINT_BASE", "s3://prep-checkpoints/spark")
CHECKPOINT_LOCATION = f"{CHECKPOINT_BASE}/recon/"
KAFKA_CHECKPOINT_LOCATION = f"{CHECKPOINT_BASE}/recon-kafka/"


def build_spark_session() -> SparkSession:
    return (
        SparkSession.builder.appName(APP_NAME)
        .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE_PARTITIONS", "400"))
        .getOrCreate()
    )


def read_pos_transactions(spark: SparkSession):
    return (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", os.getenv("KAFKA_BROKERS"))
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", os.getenv("KAFKA_STARTING_OFFSETS", "latest"))
        .option("kafka.group.id", KAFKA_GROUP_ID)
        .load()
    )


def deserialize_pos_transactions(df):
    schema = load_avro_schema("prep.pos.PosTxn")
    value = from_avro(F.col("value"), schema)
    return df.select(value.alias("payload"), F.col("key")).select("payload.*", "key")


def quality_gate(df):
    return ge_validate(df=df, suite="pos_transactions_suite", on_fail="to_dlq")


def aggregate_features(df):
    return (
        df.withWatermark("ts_event", "30 minutes")
        .groupBy("kitchen_id", F.window("ts_event", "5 minutes"))
        .agg(
            F.sum("gross_cents").alias("gross_5m"),
            F.count(F.lit(1)).alias("orders_5m"),
        )
        .select(
            F.col("kitchen_id"),
            F.col("window.start").alias("window_start"),
            F.col("window.end").alias("window_end"),
            "gross_5m",
            "orders_5m",
            F.when(F.col("orders_5m") > 0, F.col("gross_5m") / F.col("orders_5m"))
            .otherwise(F.lit(None))
            .alias("atv_cents"),
        )
    )


def write_cassandra(batch_df, _):
    (
        batch_df.write.format("org.apache.spark.sql.cassandra")
        .mode("append")
        .options(table="pricing_features_5m", keyspace="prep")
        .save()
    )


def start_feature_sinks(features_df):
    cassandra_query = (
        features_df.writeStream.outputMode("update").foreachBatch(write_cassandra).option(
            "checkpointLocation", CHECKPOINT_LOCATION
        ).start()
    )

    kafka_payload = features_df.select(
        F.col("kitchen_id").alias("key"), F.to_json(F.struct(*features_df.columns)).alias("value")
    )

    kafka_query = (
        kafka_payload.writeStream.format("kafka")
        .option("kafka.bootstrap.servers", os.getenv("KAFKA_BROKERS"))
        .option("topic", "optimizer.features.pricing")
        .option("checkpointLocation", KAFKA_CHECKPOINT_LOCATION)
        .start()
    )

    return cassandra_query, kafka_query


def main():
    spark = build_spark_session()
    source_df = read_pos_transactions(spark)
    deserialized = deserialize_pos_transactions(source_df)
    validated = quality_gate(deserialized)
    features = aggregate_features(validated)
    queries = start_feature_sinks(features)
    spark.streams.awaitAnyTermination()
    for query in queries:
        query.awaitTermination()


if __name__ == "__main__":
    main()
