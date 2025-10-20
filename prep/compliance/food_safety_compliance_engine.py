from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

try:
    import requests
except ImportError:  # pragma: no cover - requests is optional at runtime
    requests = None  # type: ignore

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


class FoodSafetyComplianceEngine(ComplianceEngine):
    """Food safety compliance engine for PrepChef kitchens."""

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
        super().__init__("Food_Safety_Compliance_Engine")
        self.data_api_client = data_api_client
        self.load_rules()
        self.logger = logging.getLogger("compliance.food_safety")
        if not self.logger.handlers:
            self.logger.addHandler(logging.NullHandler())

    def load_rules(self) -> None:  # type: ignore[override]
        now = datetime.now()
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

    def validate(self, data: Dict[str, Any]) -> List[ComplianceViolation]:  # type: ignore[override]
        validation_errors = DataValidator.validate_kitchen_data(data)
        if validation_errors:
            return [
                ComplianceViolation(
                    rule_id="data_validation",
                    rule_name="Data Validation",
                    message=error,
                    severity="critical",
                    context={"validation_errors": validation_errors},
                    timestamp=datetime.now(),
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
                ComplianceViolation(
                    rule_id="fs_license_1",
                    rule_name="Valid Food Service License",
                    message="No food service license provided",
                    severity="critical",
                    context={"license_info": license_info},
                    timestamp=datetime.now(),
                )
            )
            return violations

        expiration = license_info.get("expiration_date")
        if expiration:
            try:
                exp_date = (
                    datetime.fromisoformat(expiration.replace("Z", "+00:00"))
                    if isinstance(expiration, str)
                    else expiration
                )
                now = datetime.now(exp_date.tzinfo) if exp_date.tzinfo else datetime.now()
                if exp_date < now:
                    violations.append(
                        ComplianceViolation(
                            rule_id="fs_license_1",
                            rule_name="Valid Food Service License",
                            message=f"Food service license expired on {exp_date.date()}",
                            severity="critical",
                            context={
                                "license_number": license_number,
                                "expiration_date": exp_date.isoformat(),
                            },
                            timestamp=datetime.now(),
                        )
                    )
            except (TypeError, ValueError) as exc:
                violations.append(
                    ComplianceViolation(
                        rule_id="fs_license_1",
                        rule_name="Valid Food Service License",
                        message=f"Invalid expiration date format: {expiration}",
                        severity="critical",
                        context={
                            "license_number": license_number,
                            "expiration_date": expiration,
                            "error": str(exc),
                        },
                        timestamp=datetime.now(),
                    )
                )

        status = (license_info.get("status") or "").lower()
        if status in {"suspended", "revoked"}:
            violations.append(
                ComplianceViolation(
                    rule_id="fs_license_2",
                    rule_name="License Not Suspended or Revoked",
                    message=f"Food service license is {status}",
                    severity="critical",
                    context={"license_number": license_number, "status": status},
                    timestamp=datetime.now(),
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
                ComplianceViolation(
                    rule_id="fs_inspect_1",
                    rule_name="Recent Health Inspection",
                    message="No inspection records found",
                    severity="high",
                    context={},
                    timestamp=datetime.now(),
                )
            )
            return violations

        latest_inspection = inspection_history[0]
        inspection_date = latest_inspection.get("inspection_date")
        if inspection_date:
            try:
                insp_date = (
                    datetime.fromisoformat(inspection_date.replace("Z", "+00:00"))
                    if isinstance(inspection_date, str)
                    else inspection_date
                )
                now = datetime.now(insp_date.tzinfo) if insp_date.tzinfo else datetime.now()
                days_since = (now - insp_date).days
                if days_since > 365:
                    violations.append(
                        ComplianceViolation(
                            rule_id="fs_inspect_1",
                            rule_name="Recent Health Inspection",
                            message=f"Last inspection was {days_since} days ago (>365 days)",
                            severity="high",
                            context={
                                "last_inspection_date": insp_date.isoformat(),
                                "days_since_inspection": days_since,
                            },
                            timestamp=datetime.now(),
                        )
                    )
            except (TypeError, ValueError) as exc:
                violations.append(
                    ComplianceViolation(
                        rule_id="fs_inspect_1",
                        rule_name="Recent Health Inspection",
                        message=f"Invalid inspection date format: {inspection_date}",
                        severity="high",
                        context={"inspection_date": inspection_date, "error": str(exc)},
                        timestamp=datetime.now(),
                    )
                )

        score = latest_inspection.get("overall_score")
        if score is not None:
            try:
                score_int = int(score)
                if score_int < 70:
                    violations.append(
                        ComplianceViolation(
                            rule_id="fs_inspect_2",
                            rule_name="Passing Inspection Score",
                            message=(
                                f"Latest inspection score ({score_int}/100) is below passing threshold (70)"
                            ),
                            severity="critical",
                            context={
                                "inspection_score": score_int,
                                "inspection_date": latest_inspection.get("inspection_date"),
                            },
                            timestamp=datetime.now(),
                        )
                    )
            except (TypeError, ValueError):
                violations.append(
                    ComplianceViolation(
                        rule_id="fs_inspect_2",
                        rule_name="Passing Inspection Score",
                        message=f"Invalid inspection score format: {score}",
                        severity="critical",
                        context={
                            "inspection_score": score,
                            "inspection_date": latest_inspection.get("inspection_date"),
                        },
                        timestamp=datetime.now(),
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
                ComplianceViolation(
                    rule_id="fs_inspect_3",
                    rule_name="No Unresolved Critical Violations",
                    message=(
                        f"{len(critical_violations)} unresolved critical violations from last inspection"
                    ),
                    severity="critical",
                    context={
                        "critical_violations": critical_violations,
                        "inspection_date": latest_inspection.get("inspection_date"),
                    },
                    timestamp=datetime.now(),
                )
            )

        if latest_inspection.get("establishment_closed", False):
            violations.append(
                ComplianceViolation(
                    rule_id="fs_inspect_4",
                    rule_name="Not Under Closure Order",
                    message="Kitchen is under health department closure order",
                    severity="critical",
                    context={"closure_date": latest_inspection.get("inspection_date")},
                    timestamp=datetime.now(),
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
                ComplianceViolation(
                    rule_id="fs_cert_1",
                    rule_name="Food Safety Manager Certification",
                    message="No active food safety manager certification found",
                    severity="high",
                    context={"certifications": certifications},
                    timestamp=datetime.now(),
                )
            )

        has_allergen_training = any(
            "allergen" in str(cert.get("type", "")).lower() for cert in certifications
        )
        if not has_allergen_training:
            violations.append(
                ComplianceViolation(
                    rule_id="fs_cert_2",
                    rule_name="Allergen Awareness Training",
                    message="No allergen awareness training documentation provided",
                    severity="medium",
                    context={},
                    timestamp=datetime.now(),
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
                    ComplianceViolation(
                        rule_id=rule_id,
                        rule_name="Required Equipment",
                        message=f"No {equipment_key.replace('_', ' ')} documented",
                        severity=severity,
                        context={"missing_equipment": equipment_key},
                        timestamp=datetime.now(),
                    )
                )

        non_commercial = [
            item
            for item in equipment
            if not item.get("commercial_grade", False) and not item.get("nsf_certified", False)
        ]
        if non_commercial:
            violations.append(
                ComplianceViolation(
                    rule_id="fs_equip_1",
                    rule_name="Commercial-Grade Equipment",
                    message=(
                        f"{len(non_commercial)} equipment items not marked as commercial-grade or NSF-certified"
                    ),
                    severity="high",
                    context={"non_commercial_equipment": non_commercial},
                    timestamp=datetime.now(),
                )
            )

        return violations

    def _validate_marketplace_requirements(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        insurance = data.get("insurance", {}) or {}

        if not insurance.get("policy_number"):
            violations.append(
                ComplianceViolation(
                    rule_id="fs_prep_1",
                    rule_name="PrepChef Liability Insurance",
                    message="No liability insurance policy documented",
                    severity="critical",
                    context={},
                    timestamp=datetime.now(),
                )
            )
        elif insurance.get("expiration_date"):
            try:
                exp_date = (
                    datetime.fromisoformat(insurance["expiration_date"].replace("Z", "+00:00"))
                    if isinstance(insurance["expiration_date"], str)
                    else insurance["expiration_date"]
                )
                now = datetime.now(exp_date.tzinfo) if exp_date.tzinfo else datetime.now()
                if exp_date < now:
                    violations.append(
                        ComplianceViolation(
                            rule_id="fs_prep_1",
                            rule_name="PrepChef Liability Insurance",
                            message=f"Liability insurance expired on {exp_date.date()}",
                            severity="critical",
                            context={"expiration_date": exp_date.isoformat()},
                            timestamp=datetime.now(),
                        )
                    )
            except (TypeError, ValueError) as exc:
                violations.append(
                    ComplianceViolation(
                        rule_id="fs_prep_1",
                        rule_name="PrepChef Liability Insurance",
                        message=(
                            "Invalid insurance expiration date format: "
                            f"{insurance['expiration_date']}"
                        ),
                        severity="critical",
                        context={
                            "expiration_date": insurance.get("expiration_date"),
                            "error": str(exc),
                        },
                        timestamp=datetime.now(),
                    )
                )

        photos = data.get("photos", []) or []
        if len(photos) < 3:
            violations.append(
                ComplianceViolation(
                    rule_id="fs_prep_2",
                    rule_name="Kitchen Condition Documentation",
                    message=f"Only {len(photos)} photos uploaded (minimum 3 required)",
                    severity="medium",
                    context={"photo_count": len(photos)},
                    timestamp=datetime.now(),
                )
            )

        equipment = data.get("equipment", []) or []
        equipment_with_photos = [item for item in equipment if item.get("photo_url")]
        if equipment and len(equipment_with_photos) < int(len(equipment) * 0.7):
            violations.append(
                ComplianceViolation(
                    rule_id="fs_prep_3",
                    rule_name="Verified Equipment List",
                    message=(
                        f"Only {len(equipment_with_photos)}/{len(equipment)} equipment items have photos"
                    ),
                    severity="low",
                    context={
                        "equipment_count": len(equipment),
                        "with_photos": len(equipment_with_photos),
                    },
                    timestamp=datetime.now(),
                )
            )

        return violations

    def _validate_operations(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        pest_control = data.get("pest_control_records", []) or []

        if not pest_control:
            violations.append(
                ComplianceViolation(
                    rule_id="fs_ops_1",
                    rule_name="Pest Control Documentation",
                    message="No pest control service records provided",
                    severity="high",
                    context={},
                    timestamp=datetime.now(),
                )
            )
        else:
            latest_service = pest_control[0]
            service_date = latest_service.get("service_date")
            if service_date:
                try:
                    svc_date = (
                        datetime.fromisoformat(service_date.replace("Z", "+00:00"))
                        if isinstance(service_date, str)
                        else service_date
                    )
                    now = datetime.now(svc_date.tzinfo) if svc_date.tzinfo else datetime.now()
                    if (now - svc_date).days > 90:
                        violations.append(
                            ComplianceViolation(
                                rule_id="fs_ops_1",
                                rule_name="Pest Control Documentation",
                        message=(
                            "Last pest control service was "
                            f"{(now - svc_date).days} days ago (>90 days)"
                        ),
                                severity="high",
                                context={"last_service_date": svc_date.isoformat()},
                                timestamp=datetime.now(),
                            )
                        )
                except (TypeError, ValueError) as exc:
                    violations.append(
                        ComplianceViolation(
                            rule_id="fs_ops_1",
                            rule_name="Pest Control Documentation",
                            message=(
                                "Invalid pest control service date format: "
                                f"{latest_service['service_date']}"
                            ),
                            severity="high",
                            context={
                                "service_date": latest_service.get("service_date"),
                                "error": str(exc),
                            },
                            timestamp=datetime.now(),
                        )
                    )

        cleaning_logs = data.get("cleaning_logs", []) or []
        if not cleaning_logs:
            violations.append(
                ComplianceViolation(
                    rule_id="fs_ops_2",
                    rule_name="Cleaning and Sanitation Logs",
                    message="No cleaning and sanitation logs provided",
                    severity="medium",
                    context={},
                    timestamp=datetime.now(),
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
            "last_verified": datetime.now().isoformat(),
            "highlights": highlights,
            "concerns": concerns,
        }
