"""
Federal Regulatory Service

FastAPI microservice providing access to federal food safety compliance data,
including FDA-recognized accreditation bodies, certification bodies, and scopes.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "federal" / "prep_federal_layer.sqlite"

# FastAPI app
app = FastAPI(
    title="Prep Federal Regulatory Service",
    description="Federal compliance backbone for the Prep Regulatory Engine",
    version="1.0.0",
)


# ============================================================================
# Database Connection Management
# ============================================================================


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ============================================================================
# Pydantic Models
# ============================================================================


class AccreditationBody(BaseModel):
    """Accreditation body entity."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str | None = None
    email: str | None = None
    contact: str | None = None


class CertificationBody(BaseModel):
    """Certification body entity."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str | None = None
    email: str | None = None


class Scope(BaseModel):
    """Food safety scope entity."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    cfr_title_part_section: str | None = None
    program_reference: str | None = None
    notes: str | None = None


class ScopeLink(BaseModel):
    """Accreditation scope link entity."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    accreditation_body_id: int
    certification_body_id: int
    scope_id: int
    recognition_initial_date: date | None = None
    recognition_expiration_date: date | None = None
    scope_status: str | None = None
    source: str | None = None


class CertifierDetail(BaseModel):
    """Detailed certifier information with scopes and accreditation."""

    certifier_id: int
    certifier_name: str
    certifier_url: str | None = None
    certifier_email: str | None = None
    accreditor_name: str
    scope_name: str
    cfr_citation: str | None = None
    recognition_expiration_date: date | None = None
    scope_status: str
    days_until_expiry: int | None = None


class CertifierSummary(BaseModel):
    """Summary of a certification body with all its scopes."""

    id: int
    name: str
    url: str | None = None
    email: str | None = None
    scopes: list[str]
    scope_count: int


class ExpirationAlert(BaseModel):
    """Expiration alert for monitoring."""

    accreditor: str
    certifier: str
    scope: str
    expiration_date: date
    days_until_expiry: int
    priority: str


class AuthorityChain(BaseModel):
    """Complete authority chain for certification validation."""

    federal_authority: str = "FDA"
    accreditation_body: str
    accreditation_body_url: str | None = None
    certification_body: str
    certification_body_url: str | None = None
    scope: str
    cfr_citation: str | None = None
    recognition_initial_date: date | None = None
    recognition_expiration_date: date | None = None
    scope_status: str
    chain_validity: str


class MatchRequest(BaseModel):
    """Request for matching certifiers based on activity and jurisdiction."""

    activity: str = Field(
        ...,
        description="Food safety activity type (e.g., 'seafood_haccp', 'preventive_controls_human_food')",
    )
    jurisdiction: str | None = Field(None, description="Jurisdiction code (e.g., 'CA-Los Angeles')")


class MatchResponse(BaseModel):
    """Response with matched certifiers and regulatory context."""

    activity: str
    jurisdiction: str | None
    matched_scopes: list[Scope]
    certifiers: list[CertifierDetail]
    cfr_references: list[str]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    database_path: str
    database_exists: bool
    record_counts: dict[str, int]


# ============================================================================
# Helper Functions
# ============================================================================


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert SQLite row to dictionary."""
    return dict(row)


def map_activity_to_scope(activity: str) -> list[str]:
    """Map activity type to scope names."""
    activity_lower = activity.lower().replace("_", " ").replace("-", " ")

    mappings = {
        "preventive controls human food": ["Preventive Controls for Human Food"],
        "pchf": ["Preventive Controls for Human Food"],
        "preventive controls animal food": ["Preventive Controls for Animal Food"],
        "pcaf": ["Preventive Controls for Animal Food"],
        "produce safety": ["Produce Safety"],
        "produce": ["Produce Safety"],
        "seafood haccp": ["Seafood HACCP"],
        "seafood": ["Seafood HACCP"],
        "juice haccp": ["Juice HACCP"],
        "juice": ["Juice HACCP"],
        "low acid canned": ["Low-Acid Canned Foods (LACF)"],
        "lacf": ["Low-Acid Canned Foods (LACF)"],
        "acidified foods": ["Acidified Foods"],
        "infant formula": ["Infant Formula"],
    }

    for key, scopes in mappings.items():
        if key in activity_lower:
            return scopes

    return []


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/healthz", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""

    db_exists = DB_PATH.exists()
    record_counts = {}

    if db_exists:
        with get_db() as conn:
            cursor = conn.cursor()

            # SECURITY: Use whitelist validation and parameterized queries to prevent SQL injection
            ALLOWED_TABLES = frozenset(
                ["accreditation_bodies", "certification_bodies", "scopes", "ab_cb_scope_links"]
            )
            tables = ["accreditation_bodies", "certification_bodies", "scopes", "ab_cb_scope_links"]
            for table in tables:
                if table not in ALLOWED_TABLES:
                    logger.warning(f"Skipping invalid table name: {table}")
                    continue
                try:
                    # Safe to use string formatting since table is validated against whitelist
                    count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
                    record_counts[table] = count
                except Exception as e:
                    logger.error(f"Error counting {table}: {e}")
                    record_counts[table] = -1

    return HealthResponse(
        status="ok" if db_exists else "degraded",
        version="1.0.0",
        database_path=str(DB_PATH),
        database_exists=db_exists,
        record_counts=record_counts,
    )


@app.get("/federal/scopes", response_model=list[Scope])
async def list_scopes() -> list[Scope]:
    """
    List all available food safety scopes with CFR anchors.

    Returns all scopes recognized by FDA under FSMA and related regulations.
    """

    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT id, name, cfr_title_part_section, program_reference, notes
            FROM scopes
            ORDER BY id
        """).fetchall()

        return [Scope(**row_to_dict(row)) for row in rows]


@app.get("/federal/accreditation-bodies", response_model=list[AccreditationBody])
async def list_accreditation_bodies() -> list[AccreditationBody]:
    """
    List all FDA-recognized accreditation bodies.

    Returns accreditation bodies with metadata and contact information.
    """

    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT id, name, url, email, contact
            FROM accreditation_bodies
            ORDER BY name
        """).fetchall()

        return [AccreditationBody(**row_to_dict(row)) for row in rows]


@app.get("/federal/certification-bodies", response_model=list[CertificationBody])
async def list_certification_bodies(
    scope: str | None = Query(None, description="Filter by scope name"),
) -> list[CertificationBody]:
    """
    List all certification bodies, optionally filtered by scope.

    Returns certification bodies accredited to conduct food safety audits.
    """

    with get_db() as conn:
        cursor = conn.cursor()

        if scope:
            rows = cursor.execute(
                """
                SELECT DISTINCT cb.id, cb.name, cb.url, cb.email
                FROM certification_bodies cb
                JOIN ab_cb_scope_links l ON l.certification_body_id = cb.id
                JOIN scopes s ON s.id = l.scope_id
                WHERE s.name LIKE ? AND l.scope_status = 'active'
                ORDER BY cb.name
            """,
                (f"%{scope}%",),
            ).fetchall()
        else:
            rows = cursor.execute("""
                SELECT id, name, url, email
                FROM certification_bodies
                ORDER BY name
            """).fetchall()

        return [CertificationBody(**row_to_dict(row)) for row in rows]


@app.get("/federal/certifiers", response_model=list[CertifierDetail])
async def list_certifiers(
    scope: str | None = Query(None, description="Filter by scope name"),
    active_only: bool = Query(True, description="Only return active certifications"),
    expiring_within_days: int | None = Query(
        None, description="Filter to certifications expiring within N days"
    ),
) -> list[CertifierDetail]:
    """
    List certifiers with full details including accreditation lineage.

    Returns active certification bodies authorized for specified scope
    with accreditation body, status, and expiry date.
    """

    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT
                cb.id AS certifier_id,
                cb.name AS certifier_name,
                cb.url AS certifier_url,
                cb.email AS certifier_email,
                ab.name AS accreditor_name,
                s.name AS scope_name,
                s.cfr_title_part_section AS cfr_citation,
                l.recognition_expiration_date,
                l.scope_status,
                CAST((julianday(l.recognition_expiration_date) - julianday('now')) AS INTEGER) AS days_until_expiry
            FROM ab_cb_scope_links l
            JOIN certification_bodies cb ON cb.id = l.certification_body_id
            JOIN accreditation_bodies ab ON ab.id = l.accreditation_body_id
            JOIN scopes s ON s.id = l.scope_id
            WHERE 1=1
        """

        params = []

        if scope:
            query += " AND s.name LIKE ?"
            params.append(f"%{scope}%")

        if active_only:
            query += " AND l.scope_status = 'active'"

        if expiring_within_days is not None:
            query += " AND l.recognition_expiration_date BETWEEN DATE('now') AND DATE('now', '+' || ? || ' days')"
            params.append(str(expiring_within_days))

        query += " ORDER BY cb.name, s.name"

        rows = cursor.execute(query, params).fetchall()

        return [CertifierDetail(**row_to_dict(row)) for row in rows]


@app.get("/federal/certifiers/{certifier_id}", response_model=CertifierSummary)
async def get_certifier(certifier_id: int) -> CertifierSummary:
    """
    Get detailed information about a specific certification body.

    Returns certification body with all authorized scopes.
    """

    with get_db() as conn:
        cursor = conn.cursor()

        # Get certifier info
        certifier_row = cursor.execute(
            """
            SELECT id, name, url, email
            FROM certification_bodies
            WHERE id = ?
        """,
            (certifier_id,),
        ).fetchone()

        if not certifier_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certification body {certifier_id} not found",
            )

        # Get scopes
        scope_rows = cursor.execute(
            """
            SELECT DISTINCT s.name
            FROM scopes s
            JOIN ab_cb_scope_links l ON l.scope_id = s.id
            WHERE l.certification_body_id = ? AND l.scope_status = 'active'
            ORDER BY s.name
        """,
            (certifier_id,),
        ).fetchall()

        scopes = [row["name"] for row in scope_rows]

        return CertifierSummary(
            id=certifier_row["id"],
            name=certifier_row["name"],
            url=certifier_row["url"],
            email=certifier_row["email"],
            scopes=scopes,
            scope_count=len(scopes),
        )


@app.get("/federal/expiring", response_model=list[ExpirationAlert])
async def get_expiring_certifications(
    days: int = Query(180, description="Number of days to look ahead", ge=1, le=730),
) -> list[ExpirationAlert]:
    """
    Get certifications expiring within specified days.

    Returns upcoming expirations with priority levels for monitoring.
    """

    with get_db() as conn:
        cursor = conn.cursor()

        rows = cursor.execute(
            """
            SELECT
                ab.name AS accreditor,
                cb.name AS certifier,
                s.name AS scope,
                l.recognition_expiration_date AS expiration_date,
                CAST((julianday(l.recognition_expiration_date) - julianday('now')) AS INTEGER) AS days_until_expiry,
                CASE
                    WHEN julianday(l.recognition_expiration_date) - julianday('now') <= 90 THEN 'CRITICAL'
                    WHEN julianday(l.recognition_expiration_date) - julianday('now') <= 180 THEN 'HIGH'
                    WHEN julianday(l.recognition_expiration_date) - julianday('now') <= 365 THEN 'MEDIUM'
                    ELSE 'LOW'
                END AS priority
            FROM ab_cb_scope_links l
            JOIN accreditation_bodies ab ON ab.id = l.accreditation_body_id
            JOIN certification_bodies cb ON cb.id = l.certification_body_id
            JOIN scopes s ON s.id = l.scope_id
            WHERE l.recognition_expiration_date BETWEEN DATE('now') AND DATE('now', '+' || ? || ' days')
              AND l.scope_status = 'active'
            ORDER BY l.recognition_expiration_date ASC
        """,
            (str(days),),
        ).fetchall()

        return [ExpirationAlert(**row_to_dict(row)) for row in rows]


@app.get("/federal/authority-chain", response_model=AuthorityChain)
async def get_authority_chain(
    certifier_name: str = Query(..., description="Certification body name"),
    scope_name: str = Query(..., description="Scope name"),
) -> AuthorityChain:
    """
    Get complete authority chain for certification validation.

    Traces certification legitimacy from FDA through accreditation body
    to certification body for a specific scope.
    """

    with get_db() as conn:
        cursor = conn.cursor()

        row = cursor.execute(
            """
            SELECT
                ab.name AS accreditation_body,
                ab.url AS ab_url,
                cb.name AS certification_body,
                cb.url AS cb_url,
                s.name AS scope,
                s.cfr_title_part_section AS cfr_citation,
                l.recognition_initial_date,
                l.recognition_expiration_date,
                l.scope_status,
                CASE
                    WHEN l.recognition_expiration_date >= DATE('now') AND l.scope_status = 'active' THEN 'VALID'
                    ELSE 'INVALID'
                END AS chain_validity
            FROM ab_cb_scope_links l
            JOIN accreditation_bodies ab ON ab.id = l.accreditation_body_id
            JOIN certification_bodies cb ON cb.id = l.certification_body_id
            JOIN scopes s ON s.id = l.scope_id
            WHERE cb.name LIKE ? AND s.name LIKE ?
            ORDER BY l.recognition_expiration_date DESC
            LIMIT 1
        """,
            (f"%{certifier_name}%", f"%{scope_name}%"),
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No authority chain found for certifier '{certifier_name}' and scope '{scope_name}'",
            )

        return AuthorityChain(**row_to_dict(row))


@app.post("/federal/match", response_model=MatchResponse)
async def match_certifiers(request: MatchRequest) -> MatchResponse:
    """
    Match certifiers based on activity type and jurisdiction.

    Returns relevant certifiers, scopes, and CFR references for the activity.
    """

    # Map activity to scopes
    scope_names = map_activity_to_scope(request.activity)

    if not scope_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not map activity '{request.activity}' to any recognized scopes",
        )

    with get_db() as conn:
        cursor = conn.cursor()

        # Get matching scopes
        placeholders = ",".join("?" * len(scope_names))
        scope_rows = cursor.execute(
            f"""
            SELECT id, name, cfr_title_part_section, program_reference, notes
            FROM scopes
            WHERE name IN ({placeholders})
        """,
            scope_names,
        ).fetchall()

        matched_scopes = [Scope(**row_to_dict(row)) for row in scope_rows]

        if not matched_scopes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No scopes found matching activity '{request.activity}'",
            )

        scope_ids = [s.id for s in matched_scopes]

        # Get certifiers for these scopes
        certifier_rows = cursor.execute(
            f"""
            SELECT
                cb.id AS certifier_id,
                cb.name AS certifier_name,
                cb.url AS certifier_url,
                cb.email AS certifier_email,
                ab.name AS accreditor_name,
                s.name AS scope_name,
                s.cfr_title_part_section AS cfr_citation,
                l.recognition_expiration_date,
                l.scope_status,
                CAST((julianday(l.recognition_expiration_date) - julianday('now')) AS INTEGER) AS days_until_expiry
            FROM ab_cb_scope_links l
            JOIN certification_bodies cb ON cb.id = l.certification_body_id
            JOIN accreditation_bodies ab ON ab.id = l.accreditation_body_id
            JOIN scopes s ON s.id = l.scope_id
            WHERE s.id IN ({placeholders})
              AND l.scope_status = 'active'
              AND l.recognition_expiration_date > DATE('now')
            ORDER BY cb.name, s.name
        """,
            scope_ids,
        ).fetchall()

        certifiers = [CertifierDetail(**row_to_dict(row)) for row in certifier_rows]

        # Collect CFR references
        cfr_references = list(
            set(s.cfr_title_part_section for s in matched_scopes if s.cfr_title_part_section)
        )

        return MatchResponse(
            activity=request.activity,
            jurisdiction=request.jurisdiction,
            matched_scopes=matched_scopes,
            certifiers=certifiers,
            cfr_references=cfr_references,
        )


# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
