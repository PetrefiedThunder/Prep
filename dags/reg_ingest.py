"""Airflow DAG orchestrating the regulatory ingestion workflow."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, Callable

from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy.exc import SQLAlchemyError

from prep.models.db import SessionLocal
from prep.regulatory import RegulatoryScraper, load_regdoc
from prep.regulatory.ingest_state import record_document_changes, store_status
from prep.regulatory.models import RegDoc
from prep.regulatory.parser import extract_reg_sections
from data.ingestors.berkeley_dph import validate_fee_schedule_berkeley
from data.ingestors.joshua_tree_dph import validate_fee_schedule_joshua_tree
from data.ingestors.oakland_dph import validate_fee_schedule_oakland
from data.ingestors.palo_alto_dph import validate_fee_schedule_palo_alto
from data.ingestors.san_jose_dph import validate_fee_schedule_san_jose
from data.ingestors.sf_dph import validate_fee_schedule_sf

logger = logging.getLogger(__name__)

DEFAULT_STATES: Iterable[str] = ("CA", "NY", "TX", "FL")


def _fetch_raw(**context: Any) -> dict[str, Any]:
    dag_run = context.get("dag_run")
    requested_states = []
    if dag_run and getattr(dag_run, "conf", None):
        requested_states = dag_run.conf.get("states", []) or []
    states: list[str] = list(requested_states or DEFAULT_STATES)

    async def _run() -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        failures: list[str] = []
        async with RegulatoryScraper() as scraper:
            for state in states:
                try:
                    regulations = await scraper.scrape_health_department(state)
                except Exception as exc:  # pragma: no cover - network failures are non-deterministic
                    logger.exception("Failed to fetch regulations for state %s", state)
                    failures.append(f"{state}: {exc}")
                    regulations = []
                records.append({"state": state, "regulations": regulations})
        return {"states": states, "records": records, "failures": failures}

    result = asyncio.run(_run())
    logger.info("Fetched regulatory data for %s states", len(result["records"]))
    return result


def _parse_docs(**context: Any) -> dict[str, Any]:
    ti = context["ti"]
    raw_payload: dict[str, Any] = ti.xcom_pull(task_ids="fetch_raw") or {}
    failures: list[str] = list(raw_payload.get("failures", []))

    parsed_docs: list[dict[str, Any]] = []
    change_snapshot: list[dict[str, str]] = []

    for entry in raw_payload.get("records", []):
        state = entry.get("state") or "US"
        regulations: Iterable[dict[str, Any]] = entry.get("regulations") or []
        for regulation in regulations:
            description = str(regulation.get("description") or "")
            sections = extract_reg_sections(description)
            summary = sections[0]["body"] if sections else description[:280]
            title = regulation.get("title") or f"Regulation - {state}"
            doc_type = regulation.get("source_type") or regulation.get("regulation_type") or "regulation"
            jurisdiction = regulation.get("jurisdiction") or state
            city = None
            if isinstance(jurisdiction, str) and "," in jurisdiction:
                city_candidate, _, region = jurisdiction.partition(",")
                if region.strip().upper() == state.upper():
                    city = city_candidate.strip() or None
            reg_payload = dict(regulation)
            effective_date = reg_payload.get("effective_date")
            if isinstance(effective_date, datetime):
                reg_payload["effective_date"] = effective_date.isoformat()
            sha = hashlib.sha256()
            sha.update(state.encode("utf-8"))
            sha.update((title or "").encode("utf-8"))
            sha.update(description.encode("utf-8"))
            sha256_hash = sha.hexdigest()
            parsed_docs.append(
                {
                    "sha256_hash": sha256_hash,
                    "jurisdiction": jurisdiction,
                    "state": state,
                    "city": city,
                    "doc_type": doc_type,
                    "title": title,
                    "summary": summary,
                    "source_url": regulation.get("source_url"),
                    "raw_payload": {
                        "state": state,
                        "regulation": reg_payload,
                        "sections": sections,
                    },
                }
            )
            change_snapshot.append(
                {
                    "id": sha256_hash,
                    "text": description,
                    "jurisdiction": jurisdiction,
                }
            )

    change_count = asyncio.run(record_document_changes(change_snapshot)) if change_snapshot else 0

    logger.info(
        "Parsed %s regulatory documents with %s detected changes",
        len(parsed_docs),
        change_count,
    )

    return {
        "regdocs": parsed_docs,
        "change_count": change_count,
        "failures": failures,
    }


def _load_postgres(**context: Any) -> dict[str, Any]:
    ti = context["ti"]
    parsed: dict[str, Any] = ti.xcom_pull(task_ids="parse_docs") or {}
    regdocs: list[dict[str, Any]] = parsed.get("regdocs", [])
    failures: list[str] = list(parsed.get("failures", []))

    if not regdocs:
        logger.info("No regulatory documents to persist")
        return {"inserted": 0, "total": 0, "updated": 0, "failures": failures}

    session = SessionLocal()
    inserted = 0
    try:
        RegDoc.__table__.create(bind=session.get_bind(), checkfirst=True)
        inserted = load_regdoc(session, regdocs)
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        failure_message = f"load_postgres: {exc}"
        logger.exception("Failed to persist regulatory documents")
        failures.append(failure_message)
        ti.xcom_push(key="load_postgres_failures", value=failures)
        raise
    finally:
        session.close()

    total = len(regdocs)
    updated = max(total - inserted, 0)
    logger.info("Persisted %s documents (%s new, %s updated)", total, inserted, updated)
    return {"inserted": inserted, "total": total, "updated": updated, "failures": failures}


def _warm_cache(**context: Any) -> dict[str, Any]:
    ti = context["ti"]
    raw_payload: dict[str, Any] = ti.xcom_pull(task_ids="fetch_raw") or {}
    parsed: dict[str, Any] = ti.xcom_pull(task_ids="parse_docs") or {}
    loaded: dict[str, Any] = ti.xcom_pull(task_ids="load_postgres") or {}

    states_processed = raw_payload.get("states") or []
    documents_processed = loaded.get("total") or len(parsed.get("regdocs", []))
    inserted = loaded.get("inserted") or 0
    updated = loaded.get("updated") or max(documents_processed - inserted, 0)
    change_count = parsed.get("change_count") or 0

    failures: list[str] = []
    for payload in (raw_payload, parsed, loaded):
        failures.extend(str(item) for item in payload.get("failures", []))

    load_failures = ti.xcom_pull(task_ids="load_postgres", key="load_postgres_failures") or []
    failures.extend(str(item) for item in load_failures)

    documents_by_state = {
        record.get("state", "US"): len(record.get("regulations", []) or [])
        for record in raw_payload.get("records", [])
    }

    status_payload = {
        "last_run": datetime.now(UTC),
        "states_processed": states_processed,
        "documents_processed": documents_processed,
        "documents_inserted": inserted,
        "documents_updated": updated,
        "documents_changed": change_count,
        "documents_by_state": documents_by_state,
        "failures": failures,
        "status": "success" if not failures else "degraded",
        "fee_schedules": _collect_fee_schedule_metadata(),
    }

    asyncio.run(store_status(status_payload))
    logger.info("Cached regulatory ingestion status with %s failures", len(failures))
    return status_payload


def _create_dag() -> DAG:
    with DAG(
        dag_id="reg_ingest",
        description="Pipeline ingesting regulatory data into Postgres and warming caches",
        start_date=datetime(2024, 1, 1),
        schedule_interval="@daily",
        catchup=False,
        tags=["regulatory", "ingest"],
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

        warm_cache = PythonOperator(
            task_id="warm_cache",
            python_callable=_warm_cache,
            trigger_rule="all_done",
        )

        fetch_raw >> parse_docs >> load_postgres >> warm_cache

    return dag


dag = _create_dag()
FEE_SCHEDULE_VALIDATORS: tuple[Callable[[], Any], ...] = (
    validate_fee_schedule_sf,
    validate_fee_schedule_oakland,
    validate_fee_schedule_joshua_tree,
    validate_fee_schedule_berkeley,
    validate_fee_schedule_san_jose,
    validate_fee_schedule_palo_alto,
)


def _collect_fee_schedule_metadata() -> list[dict[str, Any]]:
    """Materialize fee schedule metadata to surface ingestion coverage."""

    schedules: list[dict[str, Any]] = []
    for validator in FEE_SCHEDULE_VALIDATORS:
        schedule = validator()
        schedules.append(
            {
                "jurisdiction": schedule.jurisdiction,
                "program": schedule.program,
                "agency": schedule.agency,
                "renewal_frequency": schedule.renewal_frequency,
                "component_count": schedule.component_count(),
            }
        )
    return schedules
