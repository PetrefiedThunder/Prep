"""
ETL Module for Federal Regulatory Data

Handles extraction, transformation, and loading of federal compliance data
from upstream sources (ANAB, IAS, FDA listings).
"""

import csv
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ETLRun:
    """ETL run metadata."""

    started_at: datetime
    completed_at: Optional[datetime] = None
    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_deleted: int = 0
    errors: list[str] = None
    success: bool = False

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class FederalDataETL:
    """ETL pipeline for federal regulatory data."""

    def __init__(self, db_path: Path, data_dir: Path):
        self.db_path = db_path
        self.data_dir = data_dir
        self.run = ETLRun(started_at=datetime.now(UTC))

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def extract_from_csv(self) -> dict[str, list[dict[str, Any]]]:
        """
        Extract data from CSV files.

        Returns:
            Dictionary with table names as keys and list of records as values
        """
        data = {}

        csv_files = {
            "accreditation_bodies": "ab_table.csv",
            "certification_bodies": "certification_bodies.csv",
            "scopes": "scopes.csv",
            "ab_cb_scope_links": "accreditor_certifier_scope_links.csv",
        }

        for table_name, filename in csv_files.items():
            filepath = self.data_dir / filename

            if not filepath.exists():
                logger.warning(f"CSV file not found: {filepath}")
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    records = list(reader)
                    data[table_name] = records
                    logger.info(f"Extracted {len(records)} records from {filename}")
            except Exception as e:
                logger.error(f"Error reading {filename}: {e}")
                self.run.errors.append(f"Failed to read {filename}: {str(e)}")

        return data

    def load_to_database(self, data: dict[str, list[dict[str, Any]]]) -> None:
        """
        Load data into SQLite database.

        Args:
            data: Dictionary with table names and records
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Clear existing data - use hardcoded table names to prevent SQL injection
            cursor.execute("DELETE FROM ab_cb_scope_links")
            logger.info("Cleared table: ab_cb_scope_links")
            cursor.execute("DELETE FROM scopes")
            logger.info("Cleared table: scopes")
            cursor.execute("DELETE FROM certification_bodies")
            logger.info("Cleared table: certification_bodies")
            cursor.execute("DELETE FROM accreditation_bodies")
            logger.info("Cleared table: accreditation_bodies")

            # Load accreditation_bodies
            if "accreditation_bodies" in data:
                for record in data["accreditation_bodies"]:
                    cursor.execute(
                        """INSERT INTO accreditation_bodies (id, name, url, email, contact)
                           VALUES (?, ?, ?, ?, ?)""",
                        (record["id"], record["name"], record["url"], record["email"], record["contact"])
                    )
                    self.run.records_inserted += 1

            # Load certification_bodies
            if "certification_bodies" in data:
                for record in data["certification_bodies"]:
                    cursor.execute(
                        """INSERT INTO certification_bodies (id, name, url, email)
                           VALUES (?, ?, ?, ?)""",
                        (record["id"], record["name"], record["url"], record["email"])
                    )
                    self.run.records_inserted += 1

            # Load scopes
            if "scopes" in data:
                for record in data["scopes"]:
                    cursor.execute(
                        """INSERT INTO scopes (id, name, cfr_title_part_section, program_reference, notes)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            record["id"],
                            record["name"],
                            record["cfr_title_part_section"],
                            record["program_reference"],
                            record["notes"]
                        )
                    )
                    self.run.records_inserted += 1

            # Load ab_cb_scope_links
            if "ab_cb_scope_links" in data:
                for record in data["ab_cb_scope_links"]:
                    cursor.execute(
                        """INSERT INTO ab_cb_scope_links
                           (id, accreditation_body_id, certification_body_id, scope_id,
                            recognition_initial_date, recognition_expiration_date, scope_status, source)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            record["id"],
                            record["accreditation_body_id"],
                            record["certification_body_id"],
                            record["scope_id"],
                            record["recognition_initial_date"],
                            record["recognition_expiration_date"],
                            record["scope_status"],
                            record["source"]
                        )
                    )
                    self.run.records_inserted += 1

            conn.commit()
            logger.info(f"Successfully loaded {self.run.records_inserted} records")

        except Exception as e:
            conn.rollback()
            logger.error(f"Error loading data: {e}")
            self.run.errors.append(f"Failed to load data: {str(e)}")
            raise

        finally:
            conn.close()

    def fetch_from_anab(self) -> list[dict[str, Any]]:
        """
        Fetch certification body data from ANAB.

        Note: This is a placeholder. In production, this would:
        1. Scrape ANAB directory or call their API
        2. Parse HTML/JSON responses
        3. Normalize data into standard format

        Returns:
            List of certification body records from ANAB
        """
        logger.info("Fetching data from ANAB (placeholder)")

        # In production, implement actual ANAB scraping/API calls
        # Example:
        # async with httpx.AsyncClient() as client:
        #     response = await client.get("https://anab.ansi.org/...")
        #     data = parse_anab_response(response.text)
        #     return data

        return []

    def fetch_from_ias(self) -> list[dict[str, Any]]:
        """
        Fetch certification body data from IAS.

        Note: This is a placeholder. In production, this would:
        1. Scrape IAS directory or call their API
        2. Parse HTML/JSON responses
        3. Normalize data into standard format

        Returns:
            List of certification body records from IAS
        """
        logger.info("Fetching data from IAS (placeholder)")

        # In production, implement actual IAS scraping/API calls
        return []

    def validate_expiration_dates(self) -> None:
        """Validate and update expiration statuses."""

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Update expired certifications
            cursor.execute("""
                UPDATE ab_cb_scope_links
                SET scope_status = 'expired'
                WHERE recognition_expiration_date < DATE('now')
                  AND scope_status = 'active'
            """)

            expired_count = cursor.rowcount
            conn.commit()

            if expired_count > 0:
                logger.info(f"Marked {expired_count} certifications as expired")
                self.run.records_updated += expired_count

        except Exception as e:
            logger.error(f"Error validating expiration dates: {e}")
            self.run.errors.append(f"Failed to validate expirations: {str(e)}")

        finally:
            conn.close()

    def run_etl(self) -> ETLRun:
        """
        Execute the full ETL pipeline.

        Returns:
            ETLRun metadata with results
        """
        try:
            logger.info("Starting federal data ETL pipeline")

            # Extract from CSV files
            data = self.extract_from_csv()
            self.run.records_processed = sum(len(records) for records in data.values())

            # Load to database
            self.load_to_database(data)

            # Validate expiration dates
            self.validate_expiration_dates()

            # Future: Fetch from upstream sources
            # anab_data = self.fetch_from_anab()
            # ias_data = self.fetch_from_ias()

            self.run.success = True
            self.run.completed_at = datetime.now(UTC)

            logger.info(
                f"ETL completed successfully: "
                f"{self.run.records_inserted} inserted, "
                f"{self.run.records_updated} updated"
            )

        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}")
            self.run.errors.append(f"Pipeline failed: {str(e)}")
            self.run.success = False
            self.run.completed_at = datetime.now(UTC)

        return self.run

    def save_run_metadata(self) -> None:
        """Save ETL run metadata to JSON file."""

        metadata_path = self.data_dir / "etl_last_run.json"

        metadata = {
            "started_at": self.run.started_at.isoformat(),
            "completed_at": self.run.completed_at.isoformat() if self.run.completed_at else None,
            "records_processed": self.run.records_processed,
            "records_inserted": self.run.records_inserted,
            "records_updated": self.run.records_updated,
            "records_deleted": self.run.records_deleted,
            "errors": self.run.errors,
            "success": self.run.success,
        }

        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved ETL metadata to {metadata_path}")
        except Exception as e:
            logger.error(f"Failed to save ETL metadata: {e}")


def run_federal_etl(db_path: Path, data_dir: Path) -> ETLRun:
    """
    Run the federal regulatory data ETL pipeline.

    Args:
        db_path: Path to SQLite database
        data_dir: Path to data directory with CSV files

    Returns:
        ETL run metadata
    """
    etl = FederalDataETL(db_path, data_dir)
    run = etl.run_etl()
    etl.save_run_metadata()
    return run


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    db_path = Path(__file__).parent.parent.parent / "data" / "federal" / "prep_federal_layer.sqlite"
    data_dir = Path(__file__).parent.parent.parent / "data" / "federal"

    run = run_federal_etl(db_path, data_dir)

    print(f"\nETL Run Summary:")
    print(f"  Status: {'SUCCESS' if run.success else 'FAILED'}")
    print(f"  Records Processed: {run.records_processed}")
    print(f"  Records Inserted: {run.records_inserted}")
    print(f"  Records Updated: {run.records_updated}")
    print(f"  Duration: {(run.completed_at - run.started_at).total_seconds():.2f}s")

    if run.errors:
        print(f"\nErrors:")
        for error in run.errors:
            print(f"  - {error}")
