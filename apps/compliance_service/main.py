from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
import asyncio
from typing import Any, Dict, List, Optional
import hashlib
from collections.abc import Generator

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from prep.compliance.data_validator import DataValidator
from prep.compliance.food_safety_compliance_engine import (
    DataIntelligenceAPIClient,
    FoodSafetyComplianceEngine,
)
from prep.compliance.coi_validation import COIValidationResult, validate_coi
from prep.models.db import SessionLocal
from prep.models.orm import COIDocument


class KitchenPayload(BaseModel):
    """Typed payload used to validate kitchen requests."""

    model_config = ConfigDict(extra="allow")

    license_info: Dict[str, Any]
    inspection_history: list[Any] = Field(default_factory=list)


ENGINE_VERSION = FoodSafetyComplianceEngine.ENGINE_VERSION


def _build_engine() -> FoodSafetyComplianceEngine:
    """Instantiate the compliance engine with optional external client."""

    api_client: Optional[DataIntelligenceAPIClient] = None
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

    kitchen_payload: Optional[Dict[str, Any]] = None
    scope: str = "full"


class ComplianceCheckResult(BaseModel):
    """Response returned after a compliance check run."""

    status: str
    report: Optional[Dict[str, Any]] = None
    executed_at: datetime


class RegulatoryDocument(BaseModel):
    """Metadata describing a regulatory document requirement."""

    id: str
    name: str
    status: str
    owner: Role
    due_date: datetime
    submitted_at: Optional[datetime] = None


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


class ComplianceHistoryEntry(BaseModel):
    """Audit trail entry for compliance events."""

    id: str
    occurred_at: datetime
    actor: Role
    description: str


_documents: List[RegulatoryDocument] = [
    RegulatoryDocument(
        id="occupancy-license",
        name="Commercial Occupancy License",
        status="approved",
        owner=Role.HOST,
        due_date=datetime(2024, 9, 30, tzinfo=timezone.utc),
        submitted_at=datetime(2024, 2, 15, tzinfo=timezone.utc),
    ),
    RegulatoryDocument(
        id="food-handler-cert",
        name="Food Handler Certificate",
        status="pending",
        owner=Role.RENTER,
        due_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
    ),
    RegulatoryDocument(
        id="safety-audit",
        name="Kitchen Safety Audit",
        status="in_review",
        owner=Role.ADMIN,
        due_date=datetime(2024, 5, 12, tzinfo=timezone.utc),
        submitted_at=datetime(2024, 4, 25, tzinfo=timezone.utc),
    ),
]

_alerts: List[MonitoringAlert] = [
    MonitoringAlert(
        id="alert-001",
        created_at=datetime(2024, 4, 20, 9, 30, tzinfo=timezone.utc),
        severity="warning",
        message="Pending sanitation inspection exceeds SLA",
        acknowledged=False,
    )
]


class HistoryResponse(BaseModel):
    """Container for history entries with metadata."""

    items: List[ComplianceHistoryEntry]
    total: int

_history: List[ComplianceHistoryEntry] = [
    ComplianceHistoryEntry(
        id="hist-001",
        occurred_at=datetime(2024, 4, 21, 14, 15, tzinfo=timezone.utc),
        actor=Role.ADMIN,
        description="Manual override approved for refrigeration maintenance window.",
    ),
    ComplianceHistoryEntry(
        id="hist-002",
        occurred_at=datetime(2024, 4, 18, 11, 0, tzinfo=timezone.utc),
        actor=Role.HOST,
        description="Submitted occupancy license renewal documentation.",
    ),
]

_monitoring_status = MonitoringStatus(
    last_run=datetime(2024, 4, 22, 6, 45, tzinfo=timezone.utc),
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


def _require_role(role: Role, allowed: List[Role]) -> None:
    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Insufficient role permissions"},
        )


def _compute_status_snapshot() -> RegulatoryStatus:
    now = datetime.now(timezone.utc)
    pending_documents = len([doc for doc in _documents if doc.status != "approved"])
    return RegulatoryStatus(
        overall_status="on_track" if pending_documents == 0 else "action_required",
        score=max(0.0, 100.0 - pending_documents * 12.5),
        last_updated=now,
        alerts_count=len([alert for alert in _alerts if not alert.acknowledged]),
        pending_documents=pending_documents,
    )


@app.get("/healthz")
def health_check() -> Dict[str, Any]:
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
            validation: COIValidationResult = validate_coi(payload)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": str(exc) or "Invalid COI document."},
            ) from exc

        document = COIDocument(
            filename=file.filename or "coi.pdf",
            content_type=file.content_type or "application/pdf",
            file_size=len(payload),
            checksum=hashlib.sha256(payload).hexdigest(),
            valid=validation.valid,
            expiry_date=validation.expiry_date,
            validation_errors="; ".join(validation.errors) if validation.errors else None,
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
            "valid": validation.valid,
            "expiry_date": validation.expiry_date.isoformat(),
        }
    finally:
        await file.close()


@app.post("/v1/report")
async def generate_compliance_report(payload: KitchenPayload) -> Dict[str, Any]:
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
    executed_at = datetime.now(timezone.utc)
    report: Optional[Dict[str, Any]] = None
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


@app.get("/api/v1/regulatory/documents", response_model=List[RegulatoryDocument])
async def list_regulatory_documents(role: Role = Depends(get_current_role)) -> List[RegulatoryDocument]:
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
                        "submitted_at": datetime.now(timezone.utc),
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
        created_at=datetime.now(timezone.utc),
        severity=request.severity,
        message=request.message,
        acknowledged=False,
    )
    async with _state_lock:
        _alerts.append(new_alert)
        global _monitoring_status
        _monitoring_status = _monitoring_status.model_copy(
            update={
                "last_run": datetime.now(timezone.utc),
                "healthy": _monitoring_status.healthy and request.severity != "critical",
                "active_alerts": len([alert for alert in _alerts if not alert.acknowledged]),
            }
        )
    return new_alert


@app.get("/api/v1/regulatory/monitoring/alerts", response_model=List[MonitoringAlert])
async def list_monitoring_alerts(role: Role = Depends(get_current_role)) -> List[MonitoringAlert]:
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
    now = datetime.now(timezone.utc)
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
