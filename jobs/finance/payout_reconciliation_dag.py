"""Airflow DAG orchestrating nightly finance payout reconciliation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from airflow import DAG
from airflow.operators.python import PythonOperator

from jobs.finance import NIGHTLY_CRON, ensure_nightly_schedule
from modules.observability import finance_missed_run_alert


def _load_ledger_exports() -> None:
    """Placeholder for loading ledger exports into the workspace."""

    print("Loading GAAP ledger exports for reconciliation")


def _aggregate_platform_payouts() -> None:
    """Placeholder for aggregating platform payout records."""

    print("Aggregating platform payout records for comparison")


def _reconcile_and_publish() -> None:
    """Placeholder for reconciling payouts and publishing results."""

    print("Reconciling payouts against ledger exports and publishing summary")


def _create_operator(task_id: str, python_callable: Callable[[], None]) -> PythonOperator:
    return PythonOperator(
        task_id=task_id,
        python_callable=python_callable,
    )


def _create_dag() -> DAG:
    default_args = {
        "owner": "finance-ops",
        "depends_on_past": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=15),
        "sla_miss_callback": finance_missed_run_alert,
    }

    schedule = ensure_nightly_schedule(None, job_name="finance_payout_reconciliation")

    with DAG(
        dag_id="finance_payout_reconciliation",
        description="Nightly reconciliation of host payouts against ledger exports.",
        start_date=datetime(2024, 1, 1),
        schedule_interval=schedule or NIGHTLY_CRON,
        catchup=False,
        default_args=default_args,
        tags=["finance", "payouts", "ledger"],
    ) as dag:
        load_ledger_exports = _create_operator(
            "load_ledger_exports", _load_ledger_exports
        )
        aggregate_platform_payouts = _create_operator(
            "aggregate_platform_payouts", _aggregate_platform_payouts
        )
        reconcile_and_publish = _create_operator(
            "reconcile_and_publish", _reconcile_and_publish
        )

        load_ledger_exports >> aggregate_platform_payouts >> reconcile_and_publish

    return dag


dag = _create_dag()
