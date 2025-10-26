"""Airflow DAG for Foodcode ingestion pipeline."""
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator


def _fetch_raw() -> None:
    """Placeholder task that would download raw data."""
    # TODO: Implement actual fetch logic.
    print("Fetching raw foodcode data")


def _parse_docs() -> None:
    """Placeholder task that would parse downloaded documents."""
    # TODO: Implement actual parsing logic.
    print("Parsing foodcode documents")


def _load_postgres() -> None:
    """Placeholder task that would load parsed data into Postgres."""
    # TODO: Implement actual load logic.
    print("Loading parsed data into Postgres")


def _create_dag() -> DAG:
    with DAG(
        dag_id="foodcode_ingest",
        description="Pipeline ingesting foodcode data into Postgres",
        start_date=datetime(2024, 1, 1),
        schedule_interval=None,
        catchup=False,
        tags=["foodcode", "ingest"],
    ) as dag:
        fetch_raw = PythonOperator(
            task_id="fetch_raw",
            python_callable=_fetch_raw,
        )

        parse_docs = PythonOperator(
            task_id="parse_docs",
            python_callable=_parse_docs,
        )

        load_postgres = PythonOperator(
            task_id="load_postgres",
            python_callable=_load_postgres,
        )

        fetch_raw >> parse_docs >> load_postgres

    return dag


dag = _create_dag()
