"""Airflow DAG scheduling the hourly pricing refresh job."""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from jobs.pricing_hourly_refresh import run_pricing_refresh


def _run_job(**context):
    summary = run_pricing_refresh()
    return summary.as_dict()


def _create_dag() -> DAG:
    with DAG(
        dag_id="pricing_hourly_refresh",
        description="Refresh cached pricing recommendations for published kitchens",
        start_date=datetime(2024, 1, 1),
        schedule_interval="@hourly",
        catchup=False,
        tags=["pricing", "cache"],
    ) as dag:
        PythonOperator(
            task_id="refresh_pricing",
            python_callable=_run_job,
        )
    return dag


dag = _create_dag()

__all__ = ["dag"]
