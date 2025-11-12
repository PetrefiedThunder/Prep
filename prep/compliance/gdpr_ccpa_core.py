from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .base_engine import ComplianceEngine, ComplianceRule, ComplianceViolation


class GDPRCCPACore(ComplianceEngine):
    """GDPR and CCPA privacy compliance engine."""

    def __init__(self) -> None:
        super().__init__("GDPR_CCPA_Compliance_Engine")
        self.load_rules()

    def load_rules(self) -> None:  # type: ignore[override]
        now = datetime.now(UTC)
        self.rules = [
            ComplianceRule(
                id="privacy_consent_1",
                name="Explicit Consent Required",
                description="Personal data processing requires explicit user consent",
                category="consent",
                severity="critical",
                applicable_regulations=["GDPR", "CCPA"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="privacy_data_minimization_1",
                name="Data Minimization",
                description="Collect only data that is necessary for specified purposes",
                category="data_collection",
                severity="high",
                applicable_regulations=["GDPR"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="privacy_right_to_delete_1",
                name="Right to Deletion",
                description="Users have the right to request deletion of their personal data",
                category="user_rights",
                severity="critical",
                applicable_regulations=["GDPR", "CCPA"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="privacy_data_breach_1",
                name="Data Breach Notification",
                description=(
                    "Data breaches must be reported within 72 hours (GDPR) or as required (CCPA)"
                ),
                category="incident_response",
                severity="critical",
                applicable_regulations=["GDPR", "CCPA"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="privacy_third_party_1",
                name="Third-Party Data Sharing",
                description="Third-party data sharing requires user consent and proper contracts",
                category="data_sharing",
                severity="high",
                applicable_regulations=["GDPR", "CCPA"],
                created_at=now,
                updated_at=now,
            ),
        ]

    def validate(self, data: dict[str, Any]) -> list[ComplianceViolation]:  # type: ignore[override]
        violations: list[ComplianceViolation] = []

        violations.extend(self._validate_consent(data))
        violations.extend(self._validate_data_minimization(data))
        violations.extend(self._validate_right_to_delete(data))
        violations.extend(self._validate_data_breach_procedures(data))
        violations.extend(self._validate_third_party_sharing(data))

        return violations

    def _validate_consent(self, data: dict[str, Any]) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []

        for user in data.get("users", []):
            consent_given = bool(user.get("consent_given", False))
            consent_timestamp = user.get("consent_timestamp")

            if not consent_given:
                violations.append(
                    ComplianceViolation(
                        rule_id="privacy_consent_1",
                        rule_name="Explicit Consent Required",
                        message=(
                            f"User {user.get('id')} has not provided explicit consent for "
                            "data processing"
                        ),
                        severity="critical",
                        context={
                            "user_id": user.get("id"),
                            "consent_given": consent_given,
                        },
                        timestamp=datetime.now(UTC),
                    )
                )
            elif not consent_timestamp:
                violations.append(
                    ComplianceViolation(
                        rule_id="privacy_consent_1",
                        rule_name="Explicit Consent Required",
                        message=(f"User {user.get('id')} consent is missing a recorded timestamp"),
                        severity="high",
                        context={
                            "user_id": user.get("id"),
                            "consent_timestamp": consent_timestamp,
                        },
                        timestamp=datetime.now(UTC),
                    )
                )

        return violations

    def _validate_data_minimization(self, data: dict[str, Any]) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []

        collected_data = data.get("collected_data", {})
        purpose = data.get("data_purpose", "")

        if "sensitive_data" in collected_data and not purpose:
            violations.append(
                ComplianceViolation(
                    rule_id="privacy_data_minimization_1",
                    rule_name="Data Minimization",
                    message="Sensitive data collected without specified purpose",
                    severity="high",
                    context={
                        "data_fields": list(collected_data.keys()),
                        "purpose_specified": bool(purpose),
                    },
                    timestamp=datetime.now(UTC),
                )
            )

        return violations

    def _validate_right_to_delete(self, data: dict[str, Any]) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []

        for request in data.get("deletion_requests", []):
            status = request.get("status", "pending")
            processed_at = request.get("processed_at")

            if status == "pending" and processed_at:
                violations.append(
                    ComplianceViolation(
                        rule_id="privacy_right_to_delete_1",
                        rule_name="Right to Deletion",
                        message=(
                            f"Deletion request {request.get('id')} marked as pending but has "
                            "a processed timestamp"
                        ),
                        severity="medium",
                        context={
                            "request_id": request.get("id"),
                            "status": status,
                            "processed_at": processed_at,
                        },
                        timestamp=datetime.now(UTC),
                    )
                )

        return violations

    def _validate_data_breach_procedures(self, data: dict[str, Any]) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []

        for breach in data.get("data_breaches", []):
            detected_at = breach.get("detected_at")
            notified_at = breach.get("notified_at")

            if isinstance(detected_at, datetime) and isinstance(notified_at, datetime):
                time_diff = (notified_at - detected_at).total_seconds()
                if time_diff > 72 * 3600:
                    violations.append(
                        ComplianceViolation(
                            rule_id="privacy_data_breach_1",
                            rule_name="Data Breach Notification",
                            message="Data breach notification delayed beyond 72 hours",
                            severity="critical",
                            context={
                                "breach_id": breach.get("id"),
                                "detection_time": detected_at,
                                "notification_time": notified_at,
                                "delay_seconds": time_diff,
                            },
                            timestamp=datetime.now(UTC),
                        )
                    )

        return violations

    def _validate_third_party_sharing(self, data: dict[str, Any]) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []

        for party in data.get("third_party_sharing", []):
            consent_obtained = bool(party.get("user_consent_obtained", False))
            contract_in_place = bool(party.get("data_processing_agreement", False))

            if not consent_obtained:
                violations.append(
                    ComplianceViolation(
                        rule_id="privacy_third_party_1",
                        rule_name="Third-Party Data Sharing",
                        message=(f"Data shared with {party.get('name')} without user consent"),
                        severity="high",
                        context={
                            "third_party": party.get("name"),
                            "consent_obtained": consent_obtained,
                        },
                        timestamp=datetime.now(UTC),
                    )
                )

            if not contract_in_place:
                violations.append(
                    ComplianceViolation(
                        rule_id="privacy_third_party_1",
                        rule_name="Third-Party Data Sharing",
                        message=(
                            f"Data sharing with {party.get('name')} lacks a data processing agreement"
                        ),
                        severity="high",
                        context={
                            "third_party": party.get("name"),
                            "contract_in_place": contract_in_place,
                        },
                        timestamp=datetime.now(UTC),
                    )
                )

        return violations
