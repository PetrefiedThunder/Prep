from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

try:
    import requests
except ImportError:  # pragma: no cover - requests is optional at runtime
    requests = None  # type: ignore

from dateutil.parser import isoparse

from .base_engine import (
    ComplianceEngine,
    ComplianceReport,
    ComplianceRule,
    ComplianceViolation,
)
from .data_validator import DataValidator


@dataclass
class HealthInspectionRecord:
    """Represents a health inspection record."""

    inspection_id: str
    inspection_date: datetime
    overall_score: int
    violations: List[Dict[str, Any]]
    inspector_id: str
    reinspection_required: bool
    establishment_closed: bool


@dataclass
class KitchenCertification:
    """Represents a kitchen certification or license."""

    license_number: str
    license_type: str
    issue_date: datetime
    expiration_date: datetime
    county_fips: str
    status: str


class DataIntelligenceAPIClient:
    """Minimal HTTP client for the PrepChef Data Intelligence API."""

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        *,
        timeout: int = 10,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not requests:  # pragma: no cover - defensive guard
            raise RuntimeError("requests is required for DataIntelligenceAPIClient")

        self.api_base_url = api_base_url.rstrip("/") + "/"
        self.api_key = api_key
        self.timeout = timeout
        self.session = session or requests.Session()

    def get(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url = urljoin(self.api_base_url, path.lstrip("/"))
        headers = {"Authorization": f"Bearer {self.api_key}"}
        return self.session.get(url, params=params, headers=headers, timeout=self.timeout)


STALENESS_WINDOW_DAYS = 180
PEST_CONTROL_WINDOW_DAYS = 90


def normalize_to_utc(date_input: Any) -> Optional[datetime]:
    """Return a timezone-aware UTC datetime for the provided input."""

    if not date_input:
        return None

    if isinstance(date_input, datetime):
        if date_input.tzinfo:
            return date_input.astimezone(timezone.utc)
        return date_input.replace(tzinfo=timezone.utc)

    try:
        parsed = isoparse(str(date_input))
    except (TypeError, ValueError):
        return None

    if parsed.tzinfo:
        return parsed.astimezone(timezone.utc)
    return parsed.replace(tzinfo=timezone.utc)


def is_stale(utc_dt: Optional[datetime], days: int) -> bool:
    """Determine if the provided datetime is older than the staleness threshold."""

    if utc_dt is None:
        return True
    return (datetime.now(timezone.utc) - utc_dt) > timedelta(days=days)


class FoodSafetyComplianceEngine(ComplianceEngine):
    """Food safety compliance engine for PrepChef kitchens."""

    ENGINE_VERSION = "1.3.0"

    CRITICAL_VIOLATIONS = [
        "foodborne_illness",
        "improper_cooling",
        "cross_contamination",
        "food_temperature_abuse",
        "sick_employee_handling_food",
        "bare_hand_contact",
        "sewage_backup",
        "rodent_infestation",
    ]

    MAJOR_VIOLATIONS = [
        "inadequate_handwashing",
        "improper_food_storage",
        "equipment_not_sanitized",
        "pest_infestation",
        "inadequate_ventilation",
        "no_hot_water",
    ]

    def __init__(self, data_api_client: Optional[DataIntelligenceAPIClient] = None) -> None:
        super().__init__(
            "Food_Safety_Compliance_Engine", engine_version=self.ENGINE_VERSION
        )
        self.data_api_client = data_api_client
        self.load_rules()
        self.logger = logging.getLogger("compliance.food_safety")
        if not self.logger.handlers:
            self.logger.addHandler(logging.NullHandler())

    def load_rules(self) -> None:  # type: ignore[override]
        now = datetime.now(timezone.utc)
        self.rules = [
            ComplianceRule(
                id="fs_license_1",
                name="Valid Food Service License",
                description="Kitchen must have current, non-expired food service license",
                category="licensing",
                severity="critical",
                applicable_regulations=["FDA_Food_Code", "State_Health_Dept"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_license_2",
                name="License Not Suspended or Revoked",
                description="Kitchen license must not be suspended or revoked",
                category="licensing",
                severity="critical",
                applicable_regulations=["State_Health_Dept"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_inspect_1",
                name="Recent Health Inspection",
                description="Kitchen must have been inspected within the last 12 months",
                category="inspections",
                severity="high",
                applicable_regulations=["FDA_Food_Code", "Local_Health_Dept"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_inspect_stale",
                name="Inspection Data Freshness",
                description="Inspection data older than six months must be refreshed",
                category="inspections",
                severity="medium",
                applicable_regulations=["PrepChef_Policy"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_inspect_2",
                name="Passing Inspection Score",
                description="Most recent inspection must have passing score (≥70/100)",
                category="inspections",
                severity="critical",
                applicable_regulations=["Local_Health_Dept"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_inspect_3",
                name="No Unresolved Critical Violations",
                description="No critical health violations from last inspection remain unresolved",
                category="inspections",
                severity="critical",
                applicable_regulations=["FDA_Food_Code"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_inspect_4",
                name="Not Under Closure Order",
                description="Kitchen must not be under health department closure order",
                category="inspections",
                severity="critical",
                applicable_regulations=["Local_Health_Dept"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_cert_1",
                name="Food Safety Manager Certification",
                description="At least one certified food safety manager on staff",
                category="certifications",
                severity="high",
                applicable_regulations=["FDA_Food_Code", "State_Law"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_cert_2",
                name="Allergen Awareness Training",
                description="Staff trained on allergen safety and cross-contact prevention",
                category="certifications",
                severity="medium",
                applicable_regulations=["FDA_FSMA"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_equip_1",
                name="Commercial-Grade Equipment",
                description="All equipment must be NSF-certified or commercial-grade",
                category="equipment",
                severity="high",
                applicable_regulations=["FDA_Food_Code", "NSF_Standards"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_equip_2",
                name="Temperature Monitoring",
                description="Proper refrigeration and temperature monitoring systems in place",
                category="equipment",
                severity="critical",
                applicable_regulations=["FDA_Food_Code"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_equip_3",
                name="Handwashing Stations",
                description="Adequate handwashing stations with hot water and soap",
                category="equipment",
                severity="critical",
                applicable_regulations=["FDA_Food_Code"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_prep_1",
                name="PrepChef Liability Insurance",
                description="Host must maintain required liability insurance coverage",
                category="marketplace",
                severity="critical",
                applicable_regulations=["PrepChef_Terms"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_prep_2",
                name="Kitchen Condition Documentation",
                description="Current photos of kitchen facilities uploaded and verified",
                category="marketplace",
                severity="medium",
                applicable_regulations=["PrepChef_Standards"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_prep_3",
                name="Verified Equipment List",
                description="Accurate list of available equipment with photos",
                category="marketplace",
                severity="low",
                applicable_regulations=["PrepChef_Standards"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_ops_1",
                name="Pest Control Documentation",
                description="Regular pest control service records available",
                category="operations",
                severity="high",
                applicable_regulations=["FDA_Food_Code"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="fs_ops_2",
                name="Cleaning and Sanitation Logs",
                description="Documented cleaning and sanitation procedures",
                category="operations",
                severity="medium",
                applicable_regulations=["FDA_Food_Code"],
                created_at=now,
                updated_at=now,
            ),
        ]
        default_versions = {rule.id: "1.0.0" for rule in self.rules}
        default_versions.update(
            {
                "fs_license_1": "2.1.0",
                "fs_license_2": "1.4.0",
                "fs_inspect_1": "2.0.0",
                "fs_inspect_stale": "1.0.0",
                "fs_inspect_2": "2.3.0",
                "fs_inspect_3": "1.6.0",
                "fs_inspect_4": "1.2.0",
                "fs_cert_1": "1.1.0",
                "fs_cert_2": "1.1.0",
                "fs_equip_1": "1.0.2",
                "fs_equip_2": "1.0.2",
                "fs_equip_3": "1.0.2",
                "fs_prep_1": "1.3.0",
                "fs_prep_2": "1.2.0",
                "fs_prep_3": "1.1.0",
                "fs_ops_1": "1.4.0",
                "fs_ops_2": "1.2.0",
            }
        )
        default_versions["data_validation"] = "1.0.0"
        self.rule_versions = default_versions

    def _build_violation(
        self,
        rule_id: str,
        *,
        message: str,
        severity: str,
        context: Optional[Dict[str, Any]] = None,
        evidence_path: Optional[str] = None,
        observed_value: Any = None,
    ) -> ComplianceViolation:
        """Create a violation enriched with traceability metadata."""

        rule_name = next((rule.name for rule in self.rules if rule.id == rule_id), rule_id)
        timestamp = datetime.now(timezone.utc)
        return ComplianceViolation(
            rule_id=rule_id,
            rule_name=rule_name,
            message=message,
            severity=severity,
            context=context or {},
            timestamp=timestamp,
            rule_version=self.rule_versions.get(rule_id),
            evidence_path=evidence_path,
            observed_value=observed_value,
        )

    def validate(self, data: Dict[str, Any]) -> List[ComplianceViolation]:  # type: ignore[override]
        validation_errors = DataValidator.validate_kitchen_data(data)
        if validation_errors:
            return [
                self._build_violation(
                    "data_validation",
                    message=error,
                    severity="critical",
                    context={"validation_errors": validation_errors},
                    evidence_path=None,
                    observed_value=None,
                )
                for error in validation_errors
            ]

        sanitized_data = DataValidator.sanitize_kitchen_data(data)
        violations: List[ComplianceViolation] = []

        if (
            self.data_api_client
            and sanitized_data.get("license_number")
            and sanitized_data.get("county_fips")
        ):
            try:
                county_data = self._fetch_county_compliance_data(
                    sanitized_data["license_number"], sanitized_data["county_fips"]
                )
                sanitized_data["real_time_inspection"] = county_data.get("latest_inspection")
                sanitized_data["license_status"] = county_data.get("license_status")
            except Exception as exc:  # pragma: no cover - network dependent
                self.logger.warning("Could not fetch county data: %s", exc)

        violations.extend(self._validate_licensing(sanitized_data))
        violations.extend(self._validate_inspections(sanitized_data))
        violations.extend(self._validate_certifications(sanitized_data))
        violations.extend(self._validate_equipment(sanitized_data))
        violations.extend(self._validate_marketplace_requirements(sanitized_data))
        violations.extend(self._validate_operations(sanitized_data))

        return violations

    def _fetch_county_compliance_data(self, license_number: str, county_fips: str) -> Dict[str, Any]:
        if not self.data_api_client:
            return {}

        try:
            response = self.data_api_client.get(
                "/v1/inspections/verify",
                params={"license_number": license_number, "county_fips": county_fips},
            )
            if response.status_code == 200:
                return response.json()
            self.logger.warning("County API returned status %s", response.status_code)
        except Exception as exc:  # pragma: no cover - network dependent
            self.logger.error("Error fetching county compliance data: %s", exc)
        return {}

    def _validate_licensing(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        license_info = data.get("license_info", {}) or {}

        license_number = license_info.get("license_number")
        if not license_number:
            violations.append(
                self._build_violation(
                    "fs_license_1",
                    message="No food service license provided",
                    severity="critical",
                    context={"license_info": license_info},
                    evidence_path="license_info.license_number",
                    observed_value=license_number,
                )
            )
            return violations

        expiration_raw = license_info.get("expiration_date")
        expiration_utc = normalize_to_utc(expiration_raw)
        if expiration_raw and not expiration_utc:
            violations.append(
                self._build_violation(
                    "fs_license_1",
                    message=f"Invalid expiration date format: {expiration_raw}",
                    severity="critical",
                    context={
                        "license_number": license_number,
                        "expiration_date": expiration_raw,
                    },
                    evidence_path="license_info.expiration_date",
                    observed_value=expiration_raw,
                )
            )
        elif expiration_utc and expiration_utc < datetime.now(timezone.utc):
            violations.append(
                self._build_violation(
                    "fs_license_1",
                    message=f"Food service license expired on {expiration_utc.date()}",
                    severity="critical",
                    context={
                        "license_number": license_number,
                        "expiration_date": expiration_utc.isoformat(),
                    },
                    evidence_path="license_info.expiration_date",
                    observed_value=expiration_raw,
                )
            )

        status = (license_info.get("status") or "").lower()
        if status in {"suspended", "revoked"}:
            violations.append(
                self._build_violation(
                    "fs_license_2",
                    message=f"Food service license is {status}",
                    severity="critical",
                    context={"license_number": license_number, "status": status},
                    evidence_path="license_info.status",
                    observed_value=status,
                )
            )

        return violations

    def _validate_inspections(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        inspection_history: List[Dict[str, Any]] = data.get("inspection_history", []) or []

        if data.get("real_time_inspection"):
            inspection_history = [data["real_time_inspection"]] + inspection_history

        if not inspection_history:
            violations.append(
                self._build_violation(
                    "fs_inspect_1",
                    message="No inspection records found",
                    severity="high",
                    context={},
                    evidence_path="inspection_history",
                    observed_value=inspection_history,
                )
            )
            return violations

        latest_inspection = inspection_history[0]
        inspection_date_raw = latest_inspection.get("inspection_date")
        inspection_date_utc = normalize_to_utc(inspection_date_raw)

        if inspection_date_raw and not inspection_date_utc:
            violations.append(
                self._build_violation(
                    "fs_inspect_1",
                    message=f"Invalid inspection date format: {inspection_date_raw}",
                    severity="high",
                    context={"inspection_date": inspection_date_raw},
                    evidence_path="inspection_history[0].inspection_date",
                    observed_value=inspection_date_raw,
                )
            )
        elif inspection_date_utc:
            days_since = (datetime.now(timezone.utc) - inspection_date_utc).days
            if days_since > 365:
                violations.append(
                    self._build_violation(
                        "fs_inspect_1",
                        message=f"Last inspection was {days_since} days ago (>365 days)",
                        severity="high",
                        context={
                            "last_inspection_date": inspection_date_utc.isoformat(),
                            "days_since_inspection": days_since,
                        },
                        evidence_path="inspection_history[0].inspection_date",
                        observed_value=inspection_date_raw,
                    )
                )
            if is_stale(inspection_date_utc, STALENESS_WINDOW_DAYS):
                violations.append(
                    self._build_violation(
                        "fs_inspect_stale",
                        message=(
                            "Last inspection data is older than "
                            f"{STALENESS_WINDOW_DAYS} days"
                        ),
                        severity="medium",
                        context={
                            "last_inspection_date": inspection_date_utc.isoformat(),
                            "days_since_inspection": days_since,
                        },
                        evidence_path="inspection_history[0].inspection_date",
                        observed_value=inspection_date_raw,
                    )
                )

        score = latest_inspection.get("overall_score")
        if score is not None:
            try:
                score_int = int(score)
            except (TypeError, ValueError):
                violations.append(
                    self._build_violation(
                        "fs_inspect_2",
                        message=f"Invalid inspection score format: {score}",
                        severity="critical",
                        context={
                            "inspection_score": score,
                            "inspection_date": inspection_date_raw,
                        },
                        evidence_path="inspection_history[0].overall_score",
                        observed_value=score,
                    )
                )
            else:
                if score_int < 70:
                    violations.append(
                        self._build_violation(
                            "fs_inspect_2",
                            message=(
                                "Latest inspection score "
                                f"({score_int}/100) is below passing threshold (70)"
                            ),
                            severity="critical",
                            context={
                                "inspection_score": score_int,
                                "inspection_date": inspection_date_raw,
                            },
                            evidence_path="inspection_history[0].overall_score",
                            observed_value=score_int,
                        )
                    )

        violations_list = latest_inspection.get("violations", []) or []
        critical_violations = [
            violation
            for violation in violations_list
            if self._is_critical_violation(violation)
            and not violation.get("corrected_on_site", False)
        ]
        if critical_violations:
            violations.append(
                self._build_violation(
                    "fs_inspect_3",
                    message=(
                        f"{len(critical_violations)} unresolved critical violations from last inspection"
                    ),
                    severity="critical",
                    context={
                        "critical_violations": critical_violations,
                        "inspection_date": inspection_date_raw,
                    },
                    evidence_path="inspection_history[0].violations",
                    observed_value=critical_violations,
                )
            )

        if latest_inspection.get("establishment_closed", False):
            violations.append(
                self._build_violation(
                    "fs_inspect_4",
                    message="Kitchen is under health department closure order",
                    severity="critical",
                    context={"closure_date": inspection_date_raw},
                    evidence_path="inspection_history[0].establishment_closed",
                    observed_value=True,
                )
            )

        return violations

    def _is_critical_violation(self, violation: Dict[str, Any]) -> bool:
        violation_code = str(violation.get("violation_code", "")).lower()
        description = str(violation.get("violation_description", "")).lower()

        for keyword in self.CRITICAL_VIOLATIONS:
            if keyword in violation_code or keyword in description:
                return True

        severity = str(violation.get("severity", "")).lower()
        if severity == "critical":
            return True
        return False

    def _validate_certifications(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        certifications = data.get("certifications", []) or []

        has_manager_cert = any(
            (
                "servsafe" in str(cert.get("type", "")).lower()
                or "food_safety_manager" in str(cert.get("type", "")).lower()
                or "certified_food_manager" in str(cert.get("type", "")).lower()
            )
            and str(cert.get("status", "")).lower() == "active"
            for cert in certifications
        )

        if not has_manager_cert:
            violations.append(
                self._build_violation(
                    "fs_cert_1",
                    message="No active food safety manager certification found",
                    severity="high",
                    context={"certifications": certifications},
                    evidence_path="certifications",
                    observed_value=certifications,
                )
            )

        has_allergen_training = any(
            "allergen" in str(cert.get("type", "")).lower() for cert in certifications
        )
        if not has_allergen_training:
            violations.append(
                self._build_violation(
                    "fs_cert_2",
                    message="No allergen awareness training documentation provided",
                    severity="medium",
                    context={},
                    evidence_path="certifications",
                    observed_value=certifications,
                )
            )

        return violations

    def _validate_equipment(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        equipment = data.get("equipment", []) or []

        required_equipment = {
            "refrigeration": ("fs_equip_2", "critical"),
            "handwashing_station": ("fs_equip_3", "critical"),
        }

        for equipment_key, (rule_id, severity) in required_equipment.items():
            has_equipment = any(
                equipment_key in str(item.get("type", "")).lower() for item in equipment
            )
            if not has_equipment:
                violations.append(
                    self._build_violation(
                        rule_id,
                        message=f"No {equipment_key.replace('_', ' ')} documented",
                        severity=severity,
                        context={"missing_equipment": equipment_key},
                        evidence_path="equipment",
                        observed_value=equipment,
                    )
                )

        non_commercial = [
            item
            for item in equipment
            if not item.get("commercial_grade", False) and not item.get("nsf_certified", False)
        ]
        if non_commercial:
            violations.append(
                self._build_violation(
                    "fs_equip_1",
                    message=(
                        f"{len(non_commercial)} equipment items not marked as commercial-grade or NSF-certified"
                    ),
                    severity="high",
                    context={"non_commercial_equipment": non_commercial},
                    evidence_path="equipment",
                    observed_value=non_commercial,
                )
            )

        return violations

    def _validate_marketplace_requirements(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        insurance = data.get("insurance", {}) or {}

        if not insurance.get("policy_number"):
            violations.append(
                self._build_violation(
                    "fs_prep_1",
                    message="No liability insurance policy documented",
                    severity="critical",
                    context={},
                    evidence_path="insurance.policy_number",
                    observed_value=insurance.get("policy_number"),
                )
            )
        else:
            expiration_raw = insurance.get("expiration_date")
            expiration_utc = normalize_to_utc(expiration_raw)
            if expiration_raw and not expiration_utc:
                violations.append(
                    self._build_violation(
                        "fs_prep_1",
                        message=(
                            "Invalid insurance expiration date format: "
                            f"{expiration_raw}"
                        ),
                        severity="critical",
                        context={"expiration_date": expiration_raw},
                        evidence_path="insurance.expiration_date",
                        observed_value=expiration_raw,
                    )
                )
            elif expiration_utc and expiration_utc < datetime.now(timezone.utc):
                violations.append(
                    self._build_violation(
                        "fs_prep_1",
                        message=f"Liability insurance expired on {expiration_utc.date()}",
                        severity="critical",
                        context={"expiration_date": expiration_utc.isoformat()},
                        evidence_path="insurance.expiration_date",
                        observed_value=expiration_raw,
                    )
                )

        photos = data.get("photos", []) or []
        if len(photos) < 3:
            violations.append(
                self._build_violation(
                    "fs_prep_2",
                    message=f"Only {len(photos)} photos uploaded (minimum 3 required)",
                    severity="medium",
                    context={"photo_count": len(photos)},
                    evidence_path="photos",
                    observed_value=photos,
                )
            )

        equipment = data.get("equipment", []) or []
        equipment_with_photos = [item for item in equipment if item.get("photo_url")]
        if equipment and len(equipment_with_photos) < int(len(equipment) * 0.7):
            violations.append(
                self._build_violation(
                    "fs_prep_3",
                    message=(
                        f"Only {len(equipment_with_photos)}/{len(equipment)} equipment items have photos"
                    ),
                    severity="low",
                    context={
                        "equipment_count": len(equipment),
                        "with_photos": len(equipment_with_photos),
                    },
                    evidence_path="equipment",
                    observed_value=equipment,
                )
            )

        return violations

    def _validate_operations(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        pest_control = data.get("pest_control_records", []) or []

        if not pest_control:
            violations.append(
                self._build_violation(
                    "fs_ops_1",
                    message="No pest control service records provided",
                    severity="high",
                    context={},
                    evidence_path="pest_control_records",
                    observed_value=pest_control,
                )
            )
        else:
            latest_service = pest_control[0]
            service_date = latest_service.get("service_date")
            if service_date:
                service_date_utc = normalize_to_utc(service_date)
                if service_date and not service_date_utc:
                    violations.append(
                        self._build_violation(
                            "fs_ops_1",
                            message=(
                                "Invalid pest control service date format: "
                                f"{service_date}"
                            ),
                            severity="high",
                            context={"service_date": service_date},
                            evidence_path="pest_control_records[0].service_date",
                            observed_value=service_date,
                        )
                    )
                elif service_date_utc and is_stale(service_date_utc, PEST_CONTROL_WINDOW_DAYS):
                    days_since = (datetime.now(timezone.utc) - service_date_utc).days
                    violations.append(
                        self._build_violation(
                            "fs_ops_1",
                            message=(
                                "Last pest control service was "
                                f"{days_since} days ago (> {PEST_CONTROL_WINDOW_DAYS} days)"
                            ),
                            severity="high",
                            context={"last_service_date": service_date_utc.isoformat()},
                            evidence_path="pest_control_records[0].service_date",
                            observed_value=service_date,
                        )
                    )

        cleaning_logs = data.get("cleaning_logs", []) or []
        if not cleaning_logs:
            violations.append(
                self._build_violation(
                    "fs_ops_2",
                    message="No cleaning and sanitation logs provided",
                    severity="medium",
                    context={},
                    evidence_path="cleaning_logs",
                    observed_value=cleaning_logs,
                )
            )

        return violations

    def validate_for_booking(
        self, kitchen_data: Dict[str, Any]
    ) -> Tuple[bool, List[ComplianceViolation]]:
        violations = self.validate(kitchen_data)
        critical_violations = [violation for violation in violations if violation.severity == "critical"]
        return len(critical_violations) == 0, critical_violations

    def generate_kitchen_safety_badge(self, kitchen_data: Dict[str, Any]) -> Dict[str, Any]:
        report = self.generate_report(kitchen_data)
        score = report.overall_compliance_score * 100

        if score >= 95:
            badge_level = "gold"
        elif score >= 85:
            badge_level = "silver"
        elif score >= 70:
            badge_level = "bronze"
        else:
            badge_level = "needs_improvement"

        highlights: List[str] = []
        inspection_history = kitchen_data.get("inspection_history", []) or []
        if inspection_history:
            latest = inspection_history[0]
            if latest.get("overall_score", 0) >= 90:
                highlights.append(f"Excellent health score: {latest['overall_score']}/100")

        certifications = kitchen_data.get("certifications", []) or []
        if any("servsafe" in str(cert.get("type", "")).lower() for cert in certifications):
            highlights.append("ServSafe certified staff")

        if report.overall_compliance_score >= 0.95 and not any(
            violation.severity == "critical" for violation in report.violations_found
        ):
            highlights.append("No critical violations")

        concerns = [
            violation.message
            for violation in report.violations_found
            if violation.severity in {"critical", "high"}
        ]

        return {
            "badge_level": badge_level,
            "score": round(score, 1),
            "last_verified": datetime.now(timezone.utc).isoformat(),
            "engine_version": self.engine_version,
            "highlights": highlights,
            "concerns": concerns,
        }
