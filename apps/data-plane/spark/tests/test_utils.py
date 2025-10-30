from __future__ import annotations

import os
from datetime import datetime

import pytest
from pyspark.sql import SparkSession, Row
from pyspark.sql.types import (StructField, StructType, StringType, TimestampType,
                               DoubleType)

from apps.data_plane.spark.spark_delivery_score import score_kpis
from apps.data_plane.spark.spark_recon import aggregate_features
from apps.data_plane.spark.utils import load_avro_schema


@pytest.fixture(scope="session")
def spark():
    session = (
        SparkSession.builder.master("local[1]")
        .appName("prep-tests")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()


def test_load_avro_schema_reads_contract(tmp_path):
    schema_dir = tmp_path / "avro"
    schema_dir.mkdir()
    schema_path = schema_dir / "pos_txn.avsc"
    schema_path.write_text("{\"type\":\"record\"}", encoding="utf-8")

    previous = os.getenv("SCHEMA_REGISTRY_DIR")
    os.environ["SCHEMA_REGISTRY_DIR"] = str(schema_dir)
    try:
        result = load_avro_schema("prep.pos.PosTxn")
    finally:
        if previous is None:
            os.environ.pop("SCHEMA_REGISTRY_DIR")
        else:
            os.environ["SCHEMA_REGISTRY_DIR"] = previous

    assert "\"type\"" in result


def test_aggregate_features_computes_atv(spark):
    rows = [
        Row(kitchen_id="k1", gross_cents=1000, ts_event=datetime(2024, 1, 1, 0, 0, 0)),
        Row(kitchen_id="k1", gross_cents=500, ts_event=datetime(2024, 1, 1, 0, 1, 0)),
    ]
    df = spark.createDataFrame(rows)

    result = aggregate_features(df)
    payload = result.collect()[0]

    assert payload.kitchen_id == "k1"
    assert pytest.approx(payload.atv_cents, rel=1e-6) == 750


def test_score_kpis_combines_components(spark):
    window_schema = StructType(
        [
            StructField("start", TimestampType(), False),
            StructField("end", TimestampType(), False),
        ]
    )
    schema = StructType(
        [
            StructField("provider", StringType(), False),
            StructField("zip", StringType(), False),
            StructField("window", window_schema, False),
            StructField("p50_latency_ms", DoubleType(), False),
            StructField("p95_latency_ms", DoubleType(), False),
            StructField("success_rate", DoubleType(), False),
            StructField("avg_cost_cents", DoubleType(), False),
        ]
    )
    row = Row(
        provider="UBER_DIRECT",
        zip="94107",
        window=Row(start=datetime(2024, 1, 1, 0, 0, 0), end=datetime(2024, 1, 1, 0, 5, 0)),
        p50_latency_ms=400.0,
        p95_latency_ms=800.0,
        success_rate=0.9,
        avg_cost_cents=500.0,
    )
    df = spark.createDataFrame([row], schema=schema)

    result = score_kpis(df)
    payload = result.collect()[0]

    expected_score = 0.6 * 0.9 + 0.3 * (1 - 0.8) + 0.1 * (1 - 0.5)
    assert pytest.approx(payload.score, rel=1e-6) == expected_score
    assert payload.provider == "UBER_DIRECT"
    assert payload.zip == "94107"
