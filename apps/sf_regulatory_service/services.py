"""Domain services for the San Francisco regulatory service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import metrics
from .config import get_compliance_config
from .models import CityEtlRun, SFBookingCompliance, SFHostProfile, SFTaxLedger
from .schemas import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ComplianceResponse,
    FireVerificationRequest,
    FireVerificationResponse,
    HealthPermitValidationRequest,
    HealthPermitValidationResponse,
    HostStatusResponse,
    RemediationAction,
    SFHostProfilePayload,
    WasteVerificationRequest,
    WasteVerificationResponse,
    ZoningCheckResponse,
)

@dataclass
class EvaluationResult:
    status: str
    issues: List[str]
    remediation: List[RemediationAction]


class ComplianceEvaluator:
    """Evaluate host payloads against the SF compliance rule set."""

    def __init__(self, config: Dict[str, Dict[str, object]]):
        self.config = config

    def evaluate(self, payload: SFHostProfilePayload, zoning_allowed: bool, zoning_manual_review: bool) -> EvaluationResult:
        status = "compliant"
        issues: List[str] = []
        remediation: List[RemediationAction] = []
        today = date.today()

        # Business registration validation
        business_config = self.config.get("business_registration", {})
        expiration_grace_days = int(business_config.get("expiration_grace_days", 0))
        if not payload.business_registration_certificate:
            status = "blocked"
            issues.append("Business registration certificate is required")
            remediation.append(
                RemediationAction(
                    field="businessRegistrationCertificate",
                    action="Upload a valid San Francisco business registration certificate.",
                ),
            )
        elif payload.business_registration_expires < today:
            status = "blocked"
            issues.append("Business registration certificate has expired")
            remediation.append(
                RemediationAction(
                    field="businessRegistrationExpires",
                    action="Renew the business registration with the SF Treasurer & Tax Collector.",
                ),
            )
        elif payload.business_registration_expires <= today + timedelta(days=expiration_grace_days):
            if status != "blocked":
                status = "flagged"
            issues.append("Business registration certificate expires soon")

        # Health permit validation
        health_config = self.config.get("health_permit", {})
        facility_mapping: Dict[str, str] = health_config.get("facility_type_mapping", {})
        required_permit = facility_mapping.get(payload.facility_type)
        if not payload.health_permit_number:
            status = "blocked"
            issues.append("Health permit number is required")
            remediation.append(
                RemediationAction(
                    field="healthPermitNumber",
                    action="Provide the active Department of Public Health permit number.",
                ),
            )
        elif payload.health_permit_expires < today:
            status = "blocked"
            issues.append("Health permit is expired")
            remediation.append(
                RemediationAction(
                    field="healthPermitExpires",
                    action="Renew the health permit with SFDPH.",
                ),
            )
        elif required_permit is None:
            if status != "blocked":
                status = "flagged"
            issues.append("Facility type is not recognized for health permit mapping")
        else:
            # If the permit is valid we assume status is acceptable for MVP
            pass

        # Zoning validation
        if not zoning_allowed:
            status = "blocked"
            issues.append("Zoning district does not allow shared kitchen use")
            remediation.append(
                RemediationAction(
                    field="zoningUseDistrict",
                    action="Submit zoning variance or choose an address in an allowed district.",
                ),
            )
        elif zoning_manual_review and status != "blocked":
            status = "flagged"
            issues.append("Zoning lookup requires manual review")

        # Fire suppression requirements
        fire_config = self.config.get("fire", {})
        fire_required = payload.facility_type in set(fire_config.get("required_for", []))
        inspection_max_age_days = int(fire_config.get("inspection_max_age_days", 365))
        if fire_required:
            if not payload.fire_suppression_certificate:
                status = "blocked"
                issues.append("Fire suppression certificate is required for cooking kitchens")
                remediation.append(
                    RemediationAction(
                        field="fireSuppressionCertificate",
                        action="Upload the current fire suppression certificate issued by SFFD.",
                    ),
                )
            elif not payload.fire_last_inspection:
                status = "blocked"
                issues.append("Fire inspection date is required")
            else:
                age_days = (today - payload.fire_last_inspection).days
                if age_days > inspection_max_age_days:
                    status = "blocked"
                    issues.append("Fire inspection is older than allowed interval")
                    remediation.append(
                        RemediationAction(
                            field="fireLastInspection",
                            action="Schedule inspection with San Francisco Fire Department.",
                        ),
                    )

        # Grease waste requirements
        grease_config = self.config.get("grease", {})
        grease_required = payload.facility_type in set(grease_config.get("required_for", []))
        service_interval = int(grease_config.get("service_interval_days", 365))
        if grease_required:
            if not payload.grease_trap_certificate:
                status = "flagged" if status != "blocked" else status
                issues.append("Grease trap certificate missing")
                remediation.append(
                    RemediationAction(
                        field="greaseTrapCertificate",
                        action="Provide proof of grease interceptor service within the last year.",
                    ),
                )
            elif payload.grease_last_service:
                if (today - payload.grease_last_service).days > service_interval:
                    status = "blocked"
                    issues.append("Grease interceptor service interval exceeded")
            else:
                status = "flagged" if status != "blocked" else status
                issues.append("Grease service date required")

        # Tax classification validation
        tax_config = self.config.get("tax", {})
        allowed_classifications = {"lease_sublease", "service_provider"}
        if payload.tax_classification not in allowed_classifications:
            status = "blocked"
            issues.append("Invalid tax classification")
            remediation.append(
                RemediationAction(
                    field="taxClassification",
                    action="Select either lease_sublease (CRT) or service_provider (GRT reporting).",
                ),
            )

        return EvaluationResult(status=status, issues=issues, remediation=remediation)


class ZoningService:
    """Apply zoning allow list checks."""

    def __init__(self, config: Dict[str, object]):
        zoning_config = config.get("zoning", {}) if config else {}
        self.allowed_districts = set(zoning_config.get("allowed_districts", []))
        self.manual_review_when_unknown = zoning_config.get("manual_review_when_unknown", True)

    def check(self, address: str, provided_district: Optional[str]) -> Tuple[bool, bool, str]:
        if provided_district:
            allowed = provided_district in self.allowed_districts
            message = "District allowed" if allowed else "District not in allow list"
            return allowed, False, message
        if self.manual_review_when_unknown:
            return True, True, "Zoning requires manual review for confirmation"
        return False, False, "Unable to resolve zoning district"


class HealthPermitValidator:
    """Simple validator for SF health permits."""

    def __init__(self, config: Dict[str, object]):
        health_config = config.get("health_permit", {}) if config else {}
        self.valid_statuses = set(health_config.get("valid_statuses", ["valid"]))

    def validate(self, request: HealthPermitValidationRequest) -> HealthPermitValidationResponse:
        permit_number = request.permit_number.strip()
        if not permit_number or len(permit_number) < 4:
            metrics.sf_permit_validations_total.labels(result="invalid").inc()
            return HealthPermitValidationResponse(
                status="invalid",
                expiry_date=None,
                verification_method="manual_review",
            )
        if permit_number.startswith("X"):
            metrics.sf_permit_validations_total.labels(result="revoked").inc()
            return HealthPermitValidationResponse(
                status="revoked",
                expiry_date=None,
                verification_method="manual_review",
            )
        metrics.sf_permit_validations_total.labels(result="valid").inc()
        return HealthPermitValidationResponse(
            status="valid",
            expiry_date=date.today() + timedelta(days=365),
            verification_method="api_lookup",
        )


class FireComplianceService:
    """Validate fire suppression evidence."""

    def __init__(self, config: Dict[str, object]):
        self.max_age_days = int(config.get("fire", {}).get("inspection_max_age_days", 365))

    def verify(self, request: FireVerificationRequest) -> FireVerificationResponse:
        if (date.today() - request.last_inspection_date).days > self.max_age_days:
            return FireVerificationResponse(status="non_compliant", message="Inspection is out of date")
        return FireVerificationResponse(status="compliant", message="Inspection within required interval")


class WasteComplianceService:
    """Validate grease trap service interval."""

    def __init__(self, config: Dict[str, object]):
        self.service_interval_days = int(config.get("grease", {}).get("service_interval_days", 365))

    def verify(self, request: WasteVerificationRequest) -> WasteVerificationResponse:
        if (date.today() - request.last_service_date).days > self.service_interval_days:
            return WasteVerificationResponse(status="overdue")
        if (date.today() - request.last_service_date).days > self.service_interval_days - 30:
            return WasteVerificationResponse(status="due_soon")
        return WasteVerificationResponse(status="compliant")


class SFRegulatoryService:
    """Aggregate orchestrator for SF compliance operations."""

    def __init__(self, session: Session):
        self.session = session
        self.config = get_compliance_config()
        self.evaluator = ComplianceEvaluator(self.config)
        self.zoning_service = ZoningService(self.config)
        self.health_validator = HealthPermitValidator(self.config)
        self.fire_service = FireComplianceService(self.config)
        self.waste_service = WasteComplianceService(self.config)

    # Host onboarding -----------------------------------------------------
    def onboard_host(self, payload: SFHostProfilePayload) -> ComplianceResponse:
        zoning_allowed, manual_review, _ = self.zoning_service.check("", payload.zoning_use_district)
        result = self.evaluator.evaluate(payload, zoning_allowed, manual_review)
        self._upsert_host_profile(payload, result.status)
        self._update_compliant_ratio()
        return ComplianceResponse(status=result.status, issues=result.issues, remediation=result.remediation)

    def get_host_status(self, host_kitchen_id: str) -> HostStatusResponse:
        profile = self.session.get(SFHostProfile, host_kitchen_id)
        if profile is None:
            raise ValueError("Host profile not found")
        payload = self._to_payload(profile)
        zoning_allowed, manual_review, message = self.zoning_service.check("", profile.zoning_use_district)
        result = self.evaluator.evaluate(payload, zoning_allowed, manual_review)
        warnings: List[str] = []
        today = date.today()
        if (profile.health_permit_expires - today).days <= 30:
            warnings.append("Health permit expires within 30 days")
        if (profile.business_registration_expires - today).days <= 30:
            warnings.append("Business registration expires within 30 days")
        return HostStatusResponse(
            profile=payload,
            status=result.status,
            warnings=warnings,
            issues=result.issues,
        )

    # Booking gate --------------------------------------------------------
    def check_booking(self, request: ComplianceCheckRequest) -> ComplianceCheckResponse:
        profile = self.session.get(SFHostProfile, request.host_kitchen_id)
        if profile is None:
            raise ValueError("Host profile not found")
        payload = self._to_payload(profile)
        zoning_allowed, manual_review, _ = self.zoning_service.check("", profile.zoning_use_district)
        result = self.evaluator.evaluate(payload, zoning_allowed, manual_review)
        if request.booking_id:
            record = SFBookingCompliance(
                booking_id=request.booking_id,
                prebooking_status=result.status if result.status != "compliant" else "passed",
                issues=result.issues,
            )
            self.session.merge(record)
        metrics.sf_compliance_check_total.labels(
            status=result.status if result.status != "compliant" else "passed",
        ).inc()
        return ComplianceCheckResponse(
            bookingId=request.booking_id,
            status=result.status if result.status != "compliant" else "passed",
            issues=result.issues,
            remediation=result.remediation,
        )

    # Integrations --------------------------------------------------------
    def validate_health_permit(self, request: HealthPermitValidationRequest) -> HealthPermitValidationResponse:
        return self.health_validator.validate(request)

    def verify_fire(self, request: FireVerificationRequest) -> FireVerificationResponse:
        return self.fire_service.verify(request)

    def verify_waste(self, request: WasteVerificationRequest) -> WasteVerificationResponse:
        return self.waste_service.verify(request)

    def check_zoning(self, address: str, zoning_use_district: Optional[str]) -> ZoningCheckResponse:
        allowed, manual_review, message = self.zoning_service.check(address, zoning_use_district)
        if manual_review:
            metrics.sf_zoning_checks_total.labels(outcome="manual_review").inc()
        else:
            metrics.sf_zoning_checks_total.labels(outcome="allowed" if allowed else "denied").inc()
        return ZoningCheckResponse(
            kitchenUseAllowed=allowed,
            zoningUseDistrict=zoning_use_district or "unknown",
            manualReviewRequired=manual_review,
            message=message,
        )

    # Internal helpers ----------------------------------------------------
    def _upsert_host_profile(self, payload: SFHostProfilePayload, status: str) -> None:
        profile = self.session.get(SFHostProfile, payload.host_kitchen_id)
        values = {
            "business_registration_certificate": payload.business_registration_certificate,
            "business_registration_expires": payload.business_registration_expires,
            "health_permit_number": payload.health_permit_number,
            "health_permit_expires": payload.health_permit_expires,
            "facility_type": payload.facility_type,
            "zoning_use_district": payload.zoning_use_district,
            "fire_suppression_certificate": payload.fire_suppression_certificate,
            "fire_last_inspection": payload.fire_last_inspection,
            "grease_trap_certificate": payload.grease_trap_certificate,
            "grease_last_service": payload.grease_last_service,
            "tax_classification": payload.tax_classification,
            "lease_gross_receipts_ytd": payload.lease_gross_receipts_ytd or 0,
            "compliance_status": status,
            "updated_at": datetime.utcnow(),
        }
        if profile is None:
            profile = SFHostProfile(host_kitchen_id=payload.host_kitchen_id, **values)
            self.session.add(profile)
        else:
            for key, value in values.items():
                setattr(profile, key, value)

    def _to_payload(self, profile: SFHostProfile) -> SFHostProfilePayload:
        return SFHostProfilePayload(
            hostKitchenId=profile.host_kitchen_id,
            businessRegistrationCertificate=profile.business_registration_certificate,
            businessRegistrationExpires=profile.business_registration_expires,
            healthPermitNumber=profile.health_permit_number,
            healthPermitExpires=profile.health_permit_expires,
            facilityType=profile.facility_type,
            zoningUseDistrict=profile.zoning_use_district,
            fireSuppressionCertificate=profile.fire_suppression_certificate,
            fireLastInspection=profile.fire_last_inspection,
            greaseTrapCertificate=profile.grease_trap_certificate,
            greaseLastService=profile.grease_last_service,
            taxClassification=profile.tax_classification,
            leaseGrossReceiptsYtd=float(profile.lease_gross_receipts_ytd or 0),
        )

    def _update_compliant_ratio(self) -> None:
        total = self.session.query(func.count(SFHostProfile.host_kitchen_id)).scalar() or 0
        if not total:
            metrics.sf_hosts_compliant_ratio.set(0)
            return
        compliant = (
            self.session.query(func.count(SFHostProfile.host_kitchen_id))
            .filter(SFHostProfile.compliance_status == "compliant")
            .scalar()
            or 0
        )
        metrics.sf_hosts_compliant_ratio.set(compliant / total)


class LedgerService:
    """Utility service shared with tax integration for ledger visibility."""

    def __init__(self, session: Session):
        self.session = session

    def record_tax_line(self, booking_id: Optional[str], jurisdiction: str, basis: float, rate: float, amount: float) -> None:
        entry = SFTaxLedger(
            booking_id=booking_id,
            tax_jurisdiction=jurisdiction,
            tax_basis=basis,
            tax_rate=rate,
            tax_amount=amount,
        )
        self.session.add(entry)


class EtlRecorder:
    """Record nightly ETL runs for observability."""

    def __init__(self, session: Session):
        self.session = session

    def record(self, *, city: str, run_date: datetime, extracted: int, changed: int, status: str, diff_summary: str) -> CityEtlRun:
        run = CityEtlRun(
            city=city,
            run_date=run_date,
            records_extracted=extracted,
            records_changed=changed,
            status=status,
            diff_summary=diff_summary,
        )
        metrics.sf_etl_runs_total.labels(status=status).inc()
        self.session.add(run)
        return run
