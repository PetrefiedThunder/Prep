"""Socrata -> Supabase ETL script for PrepChef pilot counties."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Iterable, List

import backoff
import httpx
import pandas as pd
from supabase import create_client, Client

try:  # Supabase >=2.0 exposes ClientOptions for configuring the default schema
    from supabase.client import ClientOptions
except ImportError:  # pragma: no cover - fallback for older client versions
    ClientOptions = None  # type: ignore[assignment]

LOGGER = logging.getLogger("prepchef.nightly_sync")
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "nightly_sync.log"

def configure_logging(verbose: bool = False) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handlers: List[logging.Handler] = [
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Socrata inspection data into Supabase")
    parser.add_argument("--supabase-url", required=True)
    parser.add_argument("--supabase-service-key", required=True)
    parser.add_argument("--socrata-app-token", required=True)
    parser.add_argument("--socrata-username", required=True)
    parser.add_argument("--socrata-password", required=True)
    parser.add_argument(
        "--pilot-county-ids",
        required=True,
        help="Comma-separated list of county UUIDs matching the order of the workflow configuration",
    )
    parser.add_argument("--limit", type=int, default=5000, help="Max rows per dataset fetch")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


@backoff.on_exception(backoff.expo, httpx.HTTPError, max_tries=5)
def fetch_socrata_dataset(
    domain: str,
    dataset_identifier: str,
    app_token: str,
    username: str,
    password: str,
    limit: int,
) -> pd.DataFrame:
    LOGGER.info("Fetching %s/%s", domain, dataset_identifier)
    client = httpx.Client(base_url=f"https://{domain}", timeout=30.0, auth=(username, password))
    headers = {"X-App-Token": app_token}
    response = client.get(f"/resource/{dataset_identifier}.json", params={"$limit": limit}, headers=headers)
    response.raise_for_status()
    data = response.json()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    LOGGER.debug("Fetched %s rows from %s/%s", len(df), domain, dataset_identifier)
    return df


def _configure_postgrest_schema(client: Client, schema: str) -> None:
    """Ensure PostgREST queries run against the expected schema."""

    postgrest = getattr(client, "postgrest", None)
    if postgrest and hasattr(postgrest, "schema"):
        client.postgrest = postgrest.schema(schema)  # type: ignore[assignment]


def get_supabase_client(url: str, key: str) -> Client:
    if ClientOptions is not None:
        client = create_client(url, key, options=ClientOptions(schema="prepchef"))
    else:
        client = create_client(url, key)

    # Explicitly scope PostgREST queries to the prepchef schema for all client versions.
    _configure_postgrest_schema(client, "prepchef")
    return client


def upsert_staging(
    supabase: Client,
    data_source_id: str,
    df: pd.DataFrame,
    county_id: str,
    ingestion_run_id: str,
) -> int:
    if df.empty:
        LOGGER.info("No rows to ingest for data_source_id=%s", data_source_id)
        return 0

    payload = []
    for _, row in df.iterrows():
        payload.append(
            {
                "data_source_id": data_source_id,
                "external_primary_key": row.get("inspection_serial_number") or row.get("id"),
                "raw_payload": json.loads(row.to_json()),
                "ingestion_run_id": ingestion_run_id,
            }
        )

    response = supabase.table("staging_inspections").upsert(payload).execute()
    inserted = len(response.data or [])
    LOGGER.info("Upserted %s staging rows for data_source_id=%s", inserted, data_source_id)
    return inserted


def normalize_and_upsert(
    supabase: Client,
    data_source_id: str,
    county_id: str,
    ingestion_run_id: str,
) -> int:
    # Example normalization using Postgres stored procedure placeholder
    response = supabase.rpc(
        "prepchef_normalize_inspections",
        {"p_data_source_id": data_source_id, "p_ingestion_run_id": ingestion_run_id},
    ).execute()
    count = response.data or 0
    LOGGER.info("Normalized %s inspection rows for data_source_id=%s", count, data_source_id)
    return count


def record_ingestion_run(
    supabase: Client,
    county_id: str,
    data_source_id: str,
    status: str,
    record_count: int,
    error_message: str | None,
    ingestion_run_id: str,
) -> None:
    supabase.table("ingestion_runs").upsert(
        {
            "id": ingestion_run_id,
            "county_id": county_id,
            "data_source_id": data_source_id,
            "status": status,
            "record_count": record_count,
            "error_count": 0 if not error_message else 1,
            "error_message": error_message,
        }
    ).execute()


@backoff.on_exception(backoff.expo, httpx.HTTPError, max_tries=3)
def fetch_data_sources(supabase: Client, county_id: str) -> Iterable[dict]:
    response = (
        supabase.table("data_sources")
        .select("id, dataset_identifier, metadata->>domain")
        .eq("county_id", county_id)
        .eq("is_enabled", True)
        .execute()
    )
    return response.data or []


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)

    supabase = get_supabase_client(args.supabase_url, args.supabase_service_key)
    pilot_county_ids = [cid.strip() for cid in args.pilot_county_ids.split(",") if cid.strip()]

    for county_index, county_id in enumerate(pilot_county_ids):
        LOGGER.info("Starting sync for county_id=%s", county_id)
        data_sources = fetch_data_sources(supabase, county_id)
        if not data_sources:
            LOGGER.warning("No enabled data sources for county_id=%s", county_id)
            continue

        for source in data_sources:
            dataset_id = source["dataset_identifier"]
            domain = source.get("metadata") or source.get("metadata->>domain") or ""
            if not domain:
                LOGGER.error("Data source %s missing domain metadata", dataset_id)
                continue

            ingestion_run_id = supabase.rpc("uuid_generate_v4", {}).execute().data
            inserted = 0
            normalized = 0
            status = "running"
            error_message = None
            try:
                df = fetch_socrata_dataset(
                    domain=domain,
                    dataset_identifier=dataset_id,
                    app_token=args.socrata_app_token,
                    username=args.socrata_username,
                    password=args.socrata_password,
                    limit=args.limit,
                )
                inserted = upsert_staging(supabase, source["id"], df, county_id, ingestion_run_id)
                normalized = normalize_and_upsert(supabase, source["id"], county_id, ingestion_run_id)
                status = "success"
            except Exception as exc:  # noqa: BLE001 - top-level ETL guard
                LOGGER.exception("Failed to sync %s: %s", dataset_id, exc)
                status = "failed"
                error_message = str(exc)
            finally:
                record_ingestion_run(
                    supabase,
                    county_id=county_id,
                    data_source_id=source["id"],
                    status=status,
                    record_count=normalized or inserted,
                    error_message=error_message,
                    ingestion_run_id=ingestion_run_id,
                )


if __name__ == "__main__":
    main()
