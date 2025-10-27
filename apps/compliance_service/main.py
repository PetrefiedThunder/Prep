from __future__ import annotations

import html
import os
from dataclasses import asdict
from datetime import date, datetime, time, timezone
from enum import Enum
import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID
import hashlib
import os
from collections.abc import Generator
from dataclasses import asdict
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import boto3

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from prep.compliance.coi_validation import COIValidationResult, validate_coi
from prep.compliance.data_validator import DataValidator
from prep.compliance.food_safety_compliance_engine import (
    DataIntelligenceAPIClient,
    FoodSafetyComplianceEngine,
)
from prep.compliance import COIExtractionError, validate_coi
from prep.models.db import SessionLocal
from prep.models.orm import (
    Booking,
    COIDocument,
    ComplianceDocument,
    ComplianceDocumentStatus,
    User,
)

try:  # pragma: no cover - import guarded for environments without WeasyPrint
    from weasyprint import HTML as WeasyPrintHTML
except Exception:  # pragma: no cover - defer failure until endpoint invocation
    WeasyPrintHTML = None  # type: ignore[assignment]


HTMLRenderer = WeasyPrintHTML
from prep.models.orm import COIDocument
from prep.regulatory.ingest_state import fetch_status


class KitchenPayload(BaseModel):
    """Typed payload used to validate kitchen requests."""

    model_config = ConfigDict(extra="allow")

    license_info: dict[str, Any]
    inspection_history: list[Any] = Field(default_factory=list)


ENGINE_VERSION = FoodSafetyComplianceEngine.ENGINE_VERSION


def _build_engine() -> FoodSafetyComplianceEngine:
    """Instantiate the compliance engine with optional external client."""

    api_client: DataIntelligenceAPIClient | None = None
    base_url = os.getenv("DATA_INTELLIGENCE_API_URL")
    if base_url:
        api_client = DataIntelligenceAPIClient(
            api_base_url=base_url,
            api_key=os.getenv("DATA_INTELLIGENCE_API_KEY", ""),
        )

    return FoodSafetyComplianceEngine(data_api_client=api_client)


engine = _build_engine()
app = FastAPI(title="Prep Compliance Service", version=ENGINE_VERSION)


def _get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_storage_client() -> Any:
    """Return an S3 client for storing generated packets."""

    return boto3.client("s3")


class Role(str, Enum):
    """Lightweight representation of the supported user roles."""

    ADMIN = "admin"
    HOST = "host"
    RENTER = "renter"
    GOVERNMENT = "government"


class RegulatoryStatus(BaseModel):
    """High level status summary for the regulatory dashboard."""

    overall_status: str
    score: float
    last_updated: datetime
    alerts_count: int
    pending_documents: int


class ComplianceCheckRequest(BaseModel):
    """Request payload for initiating a compliance check."""

    kitchen_payload: dict[str, Any] | None = None
    scope: str = "full"


class ComplianceCheckResult(BaseModel):
    """Response returned after a compliance check run."""

    status: str
    report: dict[str, Any] | None = None
    executed_at: datetime


class RegulatoryDocument(BaseModel):
    """Metadata describing a regulatory document requirement."""

    id: str
    name: str
    status: str
    owner: Role
    due_date: datetime
    submitted_at: datetime | None = None


class DocumentSubmissionRequest(BaseModel):
    """Payload for submitting or updating a regulatory document."""

    document_id: str
    url: str


class MonitoringStatus(BaseModel):
    """Health snapshot of the monitoring subsystem."""

    last_run: datetime
    healthy: bool
    active_alerts: int


class MonitoringAlert(BaseModel):
    """Representation of a monitoring alert for the regulatory engine."""

    id: str
    created_at: datetime
    severity: str
    message: str
    acknowledged: bool = False


class CreateMonitoringAlert(BaseModel):
    """Payload required to create a new monitoring alert."""

    severity: str = Field(pattern="^(info|warning|critical)$")
    message: str


class ManualMonitoringRun(BaseModel):
    """Request payload when manually triggering monitoring."""

    reason: str


class PacketParticipant(BaseModel):
    """Participant metadata captured in the compliance packet."""

    id: str
    name: str
    email: str
    role: str


class PacketBookingInfo(BaseModel):
    """Details describing the associated booking."""

    id: str
    status: str
    start_time: datetime
    end_time: datetime
    total_amount: str
    host_payout_amount: str


class PacketKitchenInfo(BaseModel):
    """Metadata about the kitchen for the compliance packet."""

    id: str
    name: str
    compliance_status: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    health_permit_number: Optional[str] = None
    last_inspection_date: Optional[datetime] = None
    zoning_type: Optional[str] = None
    insurance_policy_number: Optional[str] = None


class PacketDocumentInfo(BaseModel):
    """Metadata about a compliance document included in the packet."""

    id: str
    document_type: str
    status: str
    url: str
    submitted_at: datetime
    notes: Optional[str] = None


class CompliancePacket(BaseModel):
    """Aggregated compliance packet metadata."""

    generated_at: datetime
    booking: PacketBookingInfo
    kitchen: PacketKitchenInfo
    host: PacketParticipant
    customer: PacketParticipant
    documents: List[PacketDocumentInfo]


class CompliancePacketResponse(BaseModel):
    """Response payload for generated compliance packets."""

    packet_url: str
    expires_in: int
    metadata: CompliancePacket
class EtlRunStatus(BaseModel):
    """Latest ETL run metadata exposed to observability dashboards."""

    last_run: datetime | None = None
    states_processed: list[str] = Field(default_factory=list)
    documents_processed: int = 0
    documents_inserted: int = 0
    documents_updated: int = 0
    documents_changed: int = 0
    failures: list[str] = Field(default_factory=list)


class ComplianceHistoryEntry(BaseModel):
    """Audit trail entry for compliance events."""

    id: str
    occurred_at: datetime
    actor: Role
    description: str


_documents: list[RegulatoryDocument] = [
    RegulatoryDocument(
        id="occupancy-license",
        name="Commercial Occupancy License",
        status="approved",
        owner=Role.HOST,
        due_date=datetime(2024, 9, 30, tzinfo=UTC),
        submitted_at=datetime(2024, 2, 15, tzinfo=UTC),
    ),
    RegulatoryDocument(
        id="food-handler-cert",
        name="Food Handler Certificate",
        status="pending",
        owner=Role.RENTER,
        due_date=datetime(2024, 6, 1, tzinfo=UTC),
    ),
    RegulatoryDocument(
        id="safety-audit",
        name="Kitchen Safety Audit",
        status="in_review",
        owner=Role.ADMIN,
        due_date=datetime(2024, 5, 12, tzinfo=UTC),
        submitted_at=datetime(2024, 4, 25, tzinfo=UTC),
    ),
]

_alerts: list[MonitoringAlert] = [
    MonitoringAlert(
        id="alert-001",
        created_at=datetime(2024, 4, 20, 9, 30, tzinfo=UTC),
        severity="warning",
        message="Pending sanitation inspection exceeds SLA",
        acknowledged=False,
    )
]


class HistoryResponse(BaseModel):
    """Container for history entries with metadata."""

    items: list[ComplianceHistoryEntry]
    total: int

_history: list[ComplianceHistoryEntry] = [
    ComplianceHistoryEntry(
        id="hist-001",
        occurred_at=datetime(2024, 4, 21, 14, 15, tzinfo=UTC),
        actor=Role.ADMIN,
        description="Manual override approved for refrigeration maintenance window.",
    ),
    ComplianceHistoryEntry(
        id="hist-002",
        occurred_at=datetime(2024, 4, 18, 11, 0, tzinfo=UTC),
        actor=Role.HOST,
        description="Submitted occupancy license renewal documentation.",
    ),
]

_monitoring_status = MonitoringStatus(
    last_run=datetime(2024, 4, 22, 6, 45, tzinfo=UTC),
    healthy=True,
    active_alerts=len(_alerts),
)

_state_lock = asyncio.Lock()


def _get_role_or_401(role_value: str) -> Role:
    try:
        return Role(role_value.lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid role provided"},
        ) from exc


async def get_current_role(x_user_role: str = Header(..., alias="X-User-Role")) -> Role:
    """Resolve the caller's role from the request headers."""

    return _get_role_or_401(x_user_role)


def _require_role(role: Role, allowed: list[Role]) -> None:
    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Insufficient role permissions"},
        )


def _participant_from_user(user: User) -> PacketParticipant:
    role_value = getattr(user.role, "value", None)
    resolved_role = role_value if isinstance(role_value, str) else "unknown"
    return PacketParticipant(
        id=str(user.id),
        name=user.full_name,
        email=user.email,
        role=resolved_role,
    )


def _extract_policy_number(kitchen: Any) -> Optional[str]:
    insurance_info = getattr(kitchen, "insurance_info", None)
    if isinstance(insurance_info, dict):
        value = insurance_info.get("policy_number")
        if value is not None:
            return str(value)
    return None


def _build_compliance_packet_metadata(booking: Booking) -> CompliancePacket:
    kitchen = booking.kitchen
    host = booking.host
    customer = booking.customer

    if kitchen is None or host is None or customer is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Booking is missing related entities"},
        )

    documents = sorted(
        list(kitchen.compliance_documents),
        key=lambda document: document.submitted_at,
    )

    document_models = [
        PacketDocumentInfo(
            id=str(document.id),
            document_type=document.document_type,
            status=document.verification_status.value
            if isinstance(document.verification_status, ComplianceDocumentStatus)
            else str(document.verification_status),
            url=document.document_url,
            submitted_at=document.submitted_at,
            notes=document.notes,
        )
        for document in documents
    ]

    metadata = CompliancePacket(
        generated_at=datetime.now(timezone.utc),
        booking=PacketBookingInfo(
            id=str(booking.id),
            status=booking.status.value,
            start_time=booking.start_time,
            end_time=booking.end_time,
            total_amount=str(booking.total_amount),
            host_payout_amount=str(booking.host_payout_amount),
        ),
        kitchen=PacketKitchenInfo(
            id=str(kitchen.id),
            name=kitchen.name,
            compliance_status=kitchen.compliance_status,
            city=kitchen.city,
            state=kitchen.state,
            health_permit_number=kitchen.health_permit_number,
            last_inspection_date=kitchen.last_inspection_date,
            zoning_type=kitchen.zoning_type,
            insurance_policy_number=_extract_policy_number(kitchen),
        ),
        host=_participant_from_user(host),
        customer=_participant_from_user(customer),
        documents=document_models,
    )

    return metadata


def _format_datetime(value: Optional[datetime]) -> str:
    if value is None:
        return "Not provided"
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M %Z")


def _escape(value: Optional[str]) -> str:
    if value is None or value == "":
        return "—"
    return html.escape(value)


def _build_packet_html(metadata: CompliancePacket) -> str:
    documents_rows = "".join(
        """
        <tr>
            <td>{document_type}</td>
            <td>{status}</td>
            <td>{submitted}</td>
            <td>{url}</td>
            <td>{notes}</td>
        </tr>
        """.format(
            document_type=_escape(item.document_type),
            status=_escape(item.status),
            submitted=_escape(_format_datetime(item.submitted_at)),
            url=_escape(item.url),
            notes=_escape(item.notes),
        )
        for item in metadata.documents
    )

    if not documents_rows:
        documents_rows = """
        <tr>
            <td colspan="5">No compliance documents recorded for this kitchen.</td>
        </tr>
        """

    return f"""
    <html>
        <head>
            <meta charset="utf-8" />
            <title>Compliance Packet</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; }}
                h1 {{ font-size: 24px; margin-bottom: 8px; }}
                h2 {{ font-size: 18px; margin-top: 24px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
                th, td {{ border: 1px solid #d2d6dc; padding: 8px; text-align: left; }}
                th {{ background-color: #f4f5f7; }}
                .metadata {{ margin-top: 8px; }}
            </style>
        </head>
        <body>
            <h1>Compliance Packet for Booking {_escape(metadata.booking.id)}</h1>
            <p class="metadata">Generated at {_escape(_format_datetime(metadata.generated_at))}</p>

            <h2>Booking Overview</h2>
            <p>Status: {_escape(metadata.booking.status)}</p>
            <p>Start: {_escape(_format_datetime(metadata.booking.start_time))}</p>
            <p>End: {_escape(_format_datetime(metadata.booking.end_time))}</p>
            <p>Total Amount: {_escape(metadata.booking.total_amount)}</p>
            <p>Host Payout: {_escape(metadata.booking.host_payout_amount)}</p>

            <h2>Kitchen Details</h2>
            <p>Name: {_escape(metadata.kitchen.name)}</p>
            <p>Compliance Status: {_escape(metadata.kitchen.compliance_status)}</p>
            <p>Location: {_escape(metadata.kitchen.city)}, {_escape(metadata.kitchen.state)}</p>
            <p>Health Permit #: {_escape(metadata.kitchen.health_permit_number)}</p>
            <p>Last Inspection: {_escape(_format_datetime(metadata.kitchen.last_inspection_date))}</p>
            <p>Zoning: {_escape(metadata.kitchen.zoning_type)}</p>
            <p>Insurance Policy: {_escape(metadata.kitchen.insurance_policy_number)}</p>

            <h2>Participants</h2>
            <p>Host: {_escape(metadata.host.name)} ({_escape(metadata.host.email)})</p>
            <p>Customer: {_escape(metadata.customer.name)} ({_escape(metadata.customer.email)})</p>

            <h2>Compliance Documents</h2>
            <table>
                <thead>
                    <tr>
                        <th>Document</th>
                        <th>Status</th>
                        <th>Submitted At</th>
                        <th>Source URL</th>
                        <th>Notes</th>
                    </tr>
                </thead>
                <tbody>
                    {documents_rows}
                </tbody>
            </table>
        </body>
    </html>
    """


def _render_packet_pdf(metadata: CompliancePacket) -> bytes:
    if HTMLRenderer is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "WeasyPrint is not available in this environment"},
        )

    html_content = _build_packet_html(metadata)
    try:
        renderer = HTMLRenderer(string=html_content)
    except Exception as exc:  # pragma: no cover - renderer construction is deterministic
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to initialize PDF renderer"},
        ) from exc

    try:
        return renderer.write_pdf()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to render compliance packet"},
        ) from exc


def _build_packet_key(metadata: CompliancePacket) -> str:
    timestamp = metadata.generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"compliance/packets/{metadata.booking.id}/packet-{timestamp}.pdf"

def _compute_status_snapshot() -> RegulatoryStatus:
    now = datetime.now(UTC)
    pending_documents = len([doc for doc in _documents if doc.status != "approved"])
    return RegulatoryStatus(
        overall_status="on_track" if pending_documents == 0 else "action_required",
        score=max(0.0, 100.0 - pending_documents * 12.5),
        last_updated=now,
        alerts_count=len([alert for alert in _alerts if not alert.acknowledged]),
        pending_documents=pending_documents,
    )


@app.post("/packet/{booking_id}", response_model=CompliancePacketResponse)
async def generate_compliance_packet(
    booking_id: str,
    role: Role = Depends(get_current_role),
    session: Session = Depends(_get_session),
    storage_client: Any = Depends(get_storage_client),
) -> CompliancePacketResponse:
    """Aggregate booking metadata and create a downloadable compliance packet."""

    _require_role(role, [Role.ADMIN, Role.GOVERNMENT])

    try:
        booking_uuid = UUID(booking_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid booking identifier"},
        ) from exc

    booking = session.get(Booking, booking_uuid)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Booking not found"},
        )

    metadata = _build_compliance_packet_metadata(booking)
    pdf_bytes = _render_packet_pdf(metadata)

    bucket_name = os.getenv("COMPLIANCE_PACKET_BUCKET", "prep-compliance-packets")
    key = _build_packet_key(metadata)

    try:
        storage_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "Failed to store compliance packet"},
        ) from exc

    try:
        expires_in = int(os.getenv("COMPLIANCE_PACKET_URL_TTL", "900"))
    except ValueError:
        expires_in = 900

    try:
        signed_url = storage_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "Failed to generate packet URL"},
        ) from exc

    return CompliancePacketResponse(
        packet_url=signed_url,
        expires_in=expires_in,
        metadata=metadata,
    )


@app.get("/healthz")
def health_check() -> dict[str, Any]:
    """Simple readiness and liveness endpoint."""

    return {
        "status": "ok",
        "version": ENGINE_VERSION,
        "engine": engine.name,
    }


@app.post("/coi", status_code=status.HTTP_201_CREATED)
async def upload_coi(
    file: UploadFile = File(...),
    session: Session = Depends(_get_session),
) -> Dict[str, Any]:
    """Accept a COI PDF upload, run OCR extraction, and persist metadata."""
) -> dict[str, Any]:
    """Accept a COI PDF upload, validate it, and persist metadata."""

    if file.content_type and not file.content_type.lower().endswith("pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Only PDF uploads are supported."},
        )

    try:
        payload = await file.read()
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Uploaded document is empty."},
            )

        try:
            metadata = validate_coi(payload)
        except COIExtractionError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": str(exc) or "Invalid COI document."},
            ) from exc

        try:
            expiry_value = metadata["expiry_date"]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Expiry date missing from COI document."},
            ) from exc

        try:
            expiry_date_obj = date.fromisoformat(expiry_value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid expiry date format extracted from COI."},
            ) from exc

        expiry_datetime = datetime.combine(
            expiry_date_obj,
            time.min,
            tzinfo=timezone.utc,
        )
        is_valid = expiry_date_obj >= datetime.now(timezone.utc).date()
        validation_errors = None if is_valid else "COI document has expired."

        document = COIDocument(
            filename=file.filename or "coi.pdf",
            content_type=file.content_type or "application/pdf",
            file_size=len(payload),
            checksum=hashlib.sha256(payload).hexdigest(),
            valid=is_valid,
            expiry_date=expiry_datetime,
            policy_number=metadata.get("policy_number"),
            insured_name=metadata.get("insured_name"),
            validation_errors=validation_errors,
        )

        try:
            session.add(document)
            session.commit()
        except SQLAlchemyError as exc:  # pragma: no cover - defensive guard
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Failed to persist COI metadata.",
                    "details": str(exc),
                },
            ) from exc

        return {
            "valid": is_valid,
            "expiry_date": expiry_datetime.isoformat(),
        }
    finally:
        await file.close()


@app.post("/v1/report")
async def generate_compliance_report(payload: KitchenPayload) -> dict[str, Any]:
    """Validate input payload and return a serialized compliance report."""

    kitchen_data = payload.model_dump()
    validation_errors = DataValidator.validate_kitchen_data(kitchen_data)
    if validation_errors:
        raise HTTPException(status_code=422, detail={"errors": validation_errors})

    try:
        report = engine.generate_report(kitchen_data)
    except Exception as exc:  # pragma: no cover - defensive logging
        raise HTTPException(
            status_code=500,
            detail={"error": "Engine execution failed", "details": str(exc)},
        ) from exc

    report_dict = asdict(report)
    report_dict["engine_version"] = engine.engine_version
    report_dict["rule_versions"] = engine.rule_versions
    return report_dict


@app.get("/api/v1/regulatory/status", response_model=RegulatoryStatus)
async def get_regulatory_status(role: Role = Depends(get_current_role)) -> RegulatoryStatus:
    """Return a snapshot of the overall regulatory status for the caller."""

    _require_role(role, [Role.ADMIN, Role.HOST, Role.RENTER, Role.GOVERNMENT])
    return _compute_status_snapshot()


@app.post("/api/v1/regulatory/check", response_model=ComplianceCheckResult)
async def run_compliance_check(
    request: ComplianceCheckRequest,
    role: Role = Depends(get_current_role),
) -> ComplianceCheckResult:
    """Trigger a compliance check leveraging the existing engine."""

    _require_role(role, [Role.ADMIN, Role.HOST])
    executed_at = datetime.now(UTC)
    report: dict[str, Any] | None = None
    if request.kitchen_payload:
        validation_errors = DataValidator.validate_kitchen_data(request.kitchen_payload)
        if validation_errors:
            raise HTTPException(status_code=422, detail={"errors": validation_errors})
        report = asdict(engine.generate_report(request.kitchen_payload))
        report["engine_version"] = engine.engine_version
        report["rule_versions"] = engine.rule_versions
    async with _state_lock:
        _history.append(
            ComplianceHistoryEntry(
                id=f"hist-{len(_history)+1:03d}",
                occurred_at=executed_at,
                actor=role,
                description=f"{role.value.title()} initiated a {request.scope} compliance check.",
            )
        )
    return ComplianceCheckResult(status="completed", report=report, executed_at=executed_at)


@app.get("/api/v1/regulatory/documents", response_model=list[RegulatoryDocument])
async def list_regulatory_documents(role: Role = Depends(get_current_role)) -> list[RegulatoryDocument]:
    """List regulatory documents filtered based on the caller's role."""

    _require_role(role, [Role.ADMIN, Role.HOST, Role.RENTER, Role.GOVERNMENT])
    if role in {Role.ADMIN, Role.GOVERNMENT}:
        return _documents
    return [doc for doc in _documents if doc.owner == role]


@app.post("/api/v1/regulatory/documents/submit", response_model=RegulatoryDocument)
async def submit_regulatory_document(
    request: DocumentSubmissionRequest,
    role: Role = Depends(get_current_role),
) -> RegulatoryDocument:
    """Submit a regulatory document and update its metadata."""

    _require_role(role, [Role.ADMIN, Role.HOST, Role.RENTER])
    async with _state_lock:
        for index, doc in enumerate(_documents):
            if doc.id == request.document_id:
                if role not in {doc.owner, Role.ADMIN}:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={"error": "Cannot submit documents owned by another role"},
                    )
                updated_doc = doc.model_copy(
                    update={
                        "status": "submitted",
                        "submitted_at": datetime.now(UTC),
                    }
                )
                _documents[index] = updated_doc
                _history.append(
                    ComplianceHistoryEntry(
                        id=f"hist-{len(_history)+1:03d}",
                        occurred_at=updated_doc.submitted_at,
                        actor=role,
                        description=(
                            f"Document {doc.name} submitted via dashboard ({request.url})."
                        ),
                    )
                )
                return updated_doc
    raise HTTPException(status_code=404, detail={"error": "Document not found"})


@app.get(
    "/api/v1/regulatory/history",
    response_model=HistoryResponse,
)
async def get_compliance_history(role: Role = Depends(get_current_role)) -> HistoryResponse:
    """Return the audit log entries for compliance events."""

    _require_role(role, [Role.ADMIN, Role.HOST, Role.RENTER, Role.GOVERNMENT])
    return HistoryResponse(items=_history, total=len(_history))


@app.get(
    "/api/v1/regulatory/monitoring/status",
    response_model=MonitoringStatus,
)
async def get_monitoring_status(role: Role = Depends(get_current_role)) -> MonitoringStatus:
    """Return operational state of the monitoring system."""

    _require_role(role, [Role.ADMIN, Role.GOVERNMENT])
    return _monitoring_status


@app.get("/etl/status", response_model=EtlRunStatus)
async def get_etl_status(role: Role = Depends(get_current_role)) -> EtlRunStatus:
    """Return the cached metadata for the regulatory ingestion workflow."""

    _require_role(role, [Role.ADMIN, Role.GOVERNMENT])
    status_payload = await fetch_status()
    if not status_payload:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "No ingestion runs have been recorded."},
        )

    last_run_value = status_payload.get("last_run")
    last_run: datetime | None = None
    if isinstance(last_run_value, str):
        try:
            last_run = datetime.fromisoformat(last_run_value)
        except ValueError:
            last_run = None
    elif isinstance(last_run_value, datetime):
        last_run = last_run_value

    return EtlRunStatus(
        last_run=last_run,
        states_processed=list(status_payload.get("states_processed", [])),
        documents_processed=int(status_payload.get("documents_processed", 0) or 0),
        documents_inserted=int(status_payload.get("documents_inserted", 0) or 0),
        documents_updated=int(status_payload.get("documents_updated", 0) or 0),
        documents_changed=int(status_payload.get("documents_changed", 0) or 0),
        failures=[str(item) for item in status_payload.get("failures", [])],
    )


@app.post(
    "/api/v1/regulatory/monitoring/alerts",
    response_model=MonitoringAlert,
    status_code=status.HTTP_201_CREATED,
)
async def create_monitoring_alert(
    request: CreateMonitoringAlert,
    role: Role = Depends(get_current_role),
) -> MonitoringAlert:
    """Create a new monitoring alert for regulatory stakeholders."""

    _require_role(role, [Role.ADMIN])
    new_alert = MonitoringAlert(
        id=f"alert-{len(_alerts)+1:03d}",
        created_at=datetime.now(UTC),
        severity=request.severity,
        message=request.message,
        acknowledged=False,
    )
    async with _state_lock:
        _alerts.append(new_alert)
        global _monitoring_status
        _monitoring_status = _monitoring_status.model_copy(
            update={
                "last_run": datetime.now(UTC),
                "healthy": _monitoring_status.healthy and request.severity != "critical",
                "active_alerts": len([alert for alert in _alerts if not alert.acknowledged]),
            }
        )
    return new_alert


@app.get("/api/v1/regulatory/monitoring/alerts", response_model=list[MonitoringAlert])
async def list_monitoring_alerts(role: Role = Depends(get_current_role)) -> list[MonitoringAlert]:
    """Return active monitoring alerts."""

    _require_role(role, [Role.ADMIN, Role.GOVERNMENT])
    return _alerts


@app.post(
    "/api/v1/regulatory/monitoring/run",
    response_model=MonitoringStatus,
)
async def trigger_monitoring_run(
    request: ManualMonitoringRun,
    role: Role = Depends(get_current_role),
) -> MonitoringStatus:
    """Trigger a manual monitoring execution."""

    _require_role(role, [Role.ADMIN, Role.GOVERNMENT])
    now = datetime.now(UTC)
    async with _state_lock:
        global _monitoring_status
        _monitoring_status = _monitoring_status.model_copy(
            update={
                "last_run": now,
                "healthy": True,
                "active_alerts": len([alert for alert in _alerts if not alert.acknowledged]),
            }
        )
        _history.append(
            ComplianceHistoryEntry(
                id=f"hist-{len(_history)+1:03d}",
                occurred_at=now,
                actor=role,
                description=f"Manual monitoring run triggered: {request.reason}",
            )
        )
        return _monitoring_status
