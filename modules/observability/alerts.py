"""Alert helpers built on top of the observability stack."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, MutableMapping

from prep.monitoring.observability import EnterpriseObservability

__all__ = ["emit_missed_run_alert", "finance_missed_run_alert"]

_observability = EnterpriseObservability()


def _serialize_execution_date(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return None
    return str(value)


def emit_missed_run_alert(
    *,
    job_name: str,
    dag_id: str | None = None,
    execution_date: datetime | None = None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    """Emit an alert that a scheduled job was missed."""

    payload: MutableMapping[str, Any] = {
        "job_name": job_name,
        "dag_id": dag_id,
        "execution_date": _serialize_execution_date(execution_date),
    }
    if extra:
        payload.update(extra)

    _observability.metrics.increment("jobs.finance.missed_runs")
    _observability.logging.info(
        "Finance job missed scheduled run",
        **payload,
    )


def finance_missed_run_alert(context: Mapping[str, Any]) -> None:
    """Airflow-compatible callback for finance job SLA misses."""

    dag = context.get("dag")
    dag_id = getattr(dag, "dag_id", None)
    task = context.get("task")
    task_id = getattr(task, "task_id", None)
    dag_run = context.get("dag_run")
    execution_date = context.get("execution_date")

    job_name_parts = [part for part in (dag_id, task_id) if part]
    job_name = ".".join(job_name_parts) if job_name_parts else dag_id or "finance_job"

    extra = {
        "task_id": task_id,
        "run_id": getattr(dag_run, "run_id", None) if dag_run else None,
    }

    emit_missed_run_alert(
        job_name=job_name,
        dag_id=dag_id,
        execution_date=execution_date,
        extra=extra,
    )
