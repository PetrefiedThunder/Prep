"""
Municipal Compliance Kernel

Evaluates booking requests against city-specific rules for permits, zoning,
insurance, sound ordinances, rental limits, and seasonal restrictions.
"""

import os
from datetime import UTC, datetime, time
from enum import Enum
from typing import Any

import yaml


class ComplianceResult(str, Enum):
    """Compliance decision outcomes."""

    ALLOW = "ALLOW"
    CONDITIONS = "CONDITIONS"
    DENY = "DENY"


class ComplianceViolation:
    """A single compliance violation or warning."""

    def __init__(
        self,
        rule_id: str,
        severity: str,
        message: str,
        remedy: str | None = None,
        citation: str | None = None,
    ):
        self.rule_id = rule_id
        self.severity = severity  # critical, high, medium, low, warning
        self.message = message
        self.remedy = remedy
        self.citation = citation

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "remedy": self.remedy,
            "citation": self.citation,
        }


class ComplianceEvaluation:
    """Complete compliance evaluation result."""

    def __init__(self, jurisdiction_id: str):
        self.jurisdiction_id = jurisdiction_id
        self.result: ComplianceResult = ComplianceResult.ALLOW
        self.violations: list[ComplianceViolation] = []
        self.warnings: list[ComplianceViolation] = []
        self.conditions: list[str] = []
        self.evaluated_at: datetime = datetime.now(UTC)

    def add_violation(self, violation: ComplianceViolation):
        """Add a violation."""
        self.violations.append(violation)
        if violation.severity in ["critical", "high"]:
            self.result = ComplianceResult.DENY
        elif self.result != ComplianceResult.DENY:
            self.result = ComplianceResult.CONDITIONS

    def add_warning(self, warning: ComplianceViolation):
        """Add a warning (doesn't block booking)."""
        self.warnings.append(warning)

    def add_condition(self, condition: str):
        """Add a condition that must be met."""
        self.conditions.append(condition)
        if self.result == ComplianceResult.ALLOW:
            self.result = ComplianceResult.CONDITIONS

    def to_dict(self) -> dict[str, Any]:
        return {
            "jurisdiction_id": self.jurisdiction_id,
            "result": self.result.value,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [w.to_dict() for w in self.warnings],
            "conditions": self.conditions,
            "evaluated_at": self.evaluated_at.isoformat(),
            "blocking_violations_count": len(
                [v for v in self.violations if v.severity in ["critical", "high"]]
            ),
        }


class MunicipalComplianceKernel:
    """
    City compliance kernel - evaluates bookings against city rules.

    Usage:
        kernel = MunicipalComplianceKernel("san_francisco")
        evaluation = kernel.evaluate_booking(
            kitchen_data={...},
            maker_data={...},
            booking_data={...}
        )
        if evaluation.result == ComplianceResult.DENY:
            # Show violations and remedies
    """

    def __init__(self, jurisdiction_id: str, config_path: str | None = None):
        self.jurisdiction_id = jurisdiction_id

        # Load city config
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), jurisdiction_id, "config.yaml")

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    def evaluate_booking(
        self, kitchen_data: dict[str, Any], maker_data: dict[str, Any], booking_data: dict[str, Any]
    ) -> ComplianceEvaluation:
        """
        Evaluate a booking request against all city rules.

        Args:
            kitchen_data: Facility info (permits, zoning, safety, etc.)
            maker_data: Maker info (insurance, certifications, etc.)
            booking_data: Booking details (start, end, hours, product_type, etc.)

        Returns:
            ComplianceEvaluation with result and violations/warnings
        """
        eval = ComplianceEvaluation(self.jurisdiction_id)

        # Run all checks
        self._check_permits(kitchen_data, eval)
        self._check_zoning(kitchen_data, eval)
        self._check_insurance(maker_data, eval)
        self._check_sound_ordinance(booking_data, eval)
        self._check_rental_limits(kitchen_data, booking_data, eval)
        self._check_seasonal_restrictions(booking_data, eval)
        self._check_ada_requirements(kitchen_data, maker_data, eval)
        self._check_grease_maintenance(kitchen_data, eval)

        return eval

    def _check_permits(self, kitchen_data: dict[str, Any], eval: ComplianceEvaluation):
        """Check facility has all required permits."""
        required_permits = self.config.get("permit_kinds", [])
        kitchen_permits = kitchen_data.get("permits", [])

        active_permit_types = {
            p["kind"]
            for p in kitchen_permits
            if p.get("status") == "active"
            and (
                not p.get("expires_at")
                or datetime.fromisoformat(p["expires_at"]) > datetime.now(UTC)
            )
        }

        for permit_type in required_permits:
            if permit_type not in active_permit_types:
                eval.add_violation(
                    ComplianceViolation(
                        rule_id=f"PERMIT_{permit_type.upper()}",
                        severity="critical",
                        message=f"Missing or expired {permit_type} permit",
                        remedy=f"Upload current {permit_type} permit for this facility",
                        citation=self.config.get("health_code"),
                    )
                )

    def _check_zoning(self, kitchen_data: dict[str, Any], eval: ComplianceEvaluation):
        """Check zoning compliance."""
        zoning_config = self.config.get("zoning", {})
        kitchen_zoning = kitchen_data.get("zoning", {})

        if zoning_config.get("require_neighborhood_notice"):
            if not kitchen_zoning.get("neighborhood_notice_doc_id"):
                eval.add_violation(
                    ComplianceViolation(
                        rule_id="ZONING_NOTICE",
                        severity="high",
                        message=f"Neighborhood notice required ({zoning_config.get('notice_period_days', 30)} days)",
                        remedy=f"Provide proof of {zoning_config.get('notice_radius_feet', 300)}-foot radius neighborhood notification",
                        citation=self.config.get("health_code"),
                    )
                )

    def _check_insurance(self, maker_data: dict[str, Any], eval: ComplianceEvaluation):
        """Check insurance meets city minimums."""
        ins_config = self.config["insurance"]
        maker_insurance = maker_data.get("insurance", {})

        # Check general liability
        liability_cents = maker_insurance.get("general_liability_cents", 0)
        min_liability = ins_config["liability_min_cents"]

        if liability_cents < min_liability:
            eval.add_violation(
                ComplianceViolation(
                    rule_id="INSURANCE_LIABILITY",
                    severity="critical",
                    message=f"General liability coverage below minimum (${min_liability / 100:.0f} required, ${liability_cents / 100:.0f} provided)",
                    remedy=f"Obtain general liability insurance of at least ${min_liability / 100:.0f}",
                    citation=self.config.get("health_code"),
                )
            )

        # Check aggregate
        aggregate_cents = maker_insurance.get("aggregate_cents", 0)
        min_aggregate = ins_config["aggregate_min_cents"]

        if aggregate_cents < min_aggregate:
            eval.add_violation(
                ComplianceViolation(
                    rule_id="INSURANCE_AGGREGATE",
                    severity="critical",
                    message=f"Aggregate coverage below minimum (${min_aggregate / 100:.0f} required)",
                    remedy=f"Obtain aggregate coverage of at least ${min_aggregate / 100:.0f}",
                )
            )

        # Check additional insured
        additional_insured_text = maker_insurance.get("additional_insured_text", "")
        required_text = ins_config["additional_insured_legal"]

        if required_text.lower() not in additional_insured_text.lower():
            eval.add_violation(
                ComplianceViolation(
                    rule_id="INSURANCE_ADDITIONAL_INSURED",
                    severity="critical",
                    message=f"COI must list '{required_text}' as additional insured",
                    remedy=f"Update your Certificate of Insurance to include '{required_text}' as additional insured",
                )
            )

    def _check_sound_ordinance(self, booking_data: dict[str, Any], eval: ComplianceEvaluation):
        """Check booking doesn't violate quiet hours."""
        sound_config = self.config.get("sound_ordinance", {})
        quiet_hours = sound_config.get("quiet_hours")

        if not quiet_hours:
            return

        booking_start = datetime.fromisoformat(booking_data["start"])
        booking_end = datetime.fromisoformat(booking_data["end"])

        quiet_start = datetime.strptime(quiet_hours["start"], "%H:%M").time()
        quiet_end = datetime.strptime(quiet_hours["end"], "%H:%M").time()

        # Check if booking overlaps quiet hours
        if self._overlaps_quiet_hours(booking_start, booking_end, quiet_start, quiet_end):
            citation = sound_config.get("citation", "")
            eval.add_violation(
                ComplianceViolation(
                    rule_id="SOUND_QUIET_HOURS",
                    severity="high",
                    message=f"Booking overlaps quiet hours ({quiet_hours['start']}-{quiet_hours['end']})",
                    remedy=f"Adjust booking to avoid quiet hours {quiet_hours['start']}-{quiet_hours['end']}",
                    citation=citation,
                )
            )

    def _overlaps_quiet_hours(
        self, start: datetime, end: datetime, quiet_start: time, quiet_end: time
    ) -> bool:
        """Check if datetime range overlaps quiet hours."""
        # Simplified - assumes quiet hours don't span midnight
        booking_start_time = start.time()
        booking_end_time = end.time()

        if quiet_start < quiet_end:
            # Normal case: quiet hours like 22:00-06:00
            return booking_start_time < quiet_end or booking_end_time > quiet_start
        else:
            # Spans midnight
            return booking_start_time >= quiet_start or booking_end_time <= quiet_end

    def _check_rental_limits(
        self, kitchen_data: dict[str, Any], booking_data: dict[str, Any], eval: ComplianceEvaluation
    ):
        """Check rental hour limits."""
        limits = self.config.get("rental_limits", {})
        max_hours_per_day = limits.get("max_hours_per_day_per_facility")

        if not max_hours_per_day:
            return

        booking_hours = booking_data.get("hours", 0)
        # Would need to query existing bookings for same day
        # Simplified for now
        daily_hours = booking_hours

        if daily_hours > max_hours_per_day:
            eval.add_violation(
                ComplianceViolation(
                    rule_id="RENTAL_LIMIT_DAILY",
                    severity="medium",
                    message=f"Exceeds daily rental limit ({max_hours_per_day} hours)",
                    remedy=f"Reduce booking to fit within {max_hours_per_day} hour daily limit",
                    citation=self.config.get("health_code"),
                )
            )

    def _check_seasonal_restrictions(
        self, booking_data: dict[str, Any], eval: ComplianceEvaluation
    ):
        """Check seasonal restrictions."""
        restrictions = self.config.get("seasonal_restrictions", [])

        booking_date = datetime.fromisoformat(booking_data["start"]).date()
        product_type = booking_data.get("product_type")

        for restriction in restrictions:
            if restriction.get("product_type") and restriction["product_type"] != product_type:
                continue

            # Check if booking falls in restricted period
            # Simplified - would need proper date range handling

            if restriction.get("restriction_type") == "prohibited":
                eval.add_violation(
                    ComplianceViolation(
                        rule_id="SEASONAL_PROHIBITED",
                        severity="high",
                        message=f"Prohibited: {restriction['reason']}",
                        remedy="Choose a different date outside restricted period",
                    )
                )

    def _check_ada_requirements(
        self, kitchen_data: dict[str, Any], maker_data: dict[str, Any], eval: ComplianceEvaluation
    ):
        """Check ADA accessibility if required."""
        maker_needs_ada = maker_data.get("requires_ada_access", False)
        kitchen_ada_accessible = kitchen_data.get("ada_accessible", False)

        if maker_needs_ada and not kitchen_ada_accessible:
            eval.add_violation(
                ComplianceViolation(
                    rule_id="ADA_ACCESSIBILITY",
                    severity="high",
                    message="Maker requires ADA-accessible facility",
                    remedy="Select an ADA-accessible facility or update accessibility features",
                )
            )

    def _check_grease_maintenance(self, kitchen_data: dict[str, Any], eval: ComplianceEvaluation):
        """Check grease trap maintenance is current."""
        grease_config = self.config.get("grease", {})
        if not grease_config.get("interceptor_required"):
            return

        kitchen_grease = kitchen_data.get("grease", {})
        last_service = kitchen_grease.get("last_service_at")
        max_interval_days = grease_config.get("max_service_interval_days", 90)

        if not last_service:
            eval.add_warning(
                ComplianceViolation(
                    rule_id="GREASE_MAINTENANCE",
                    severity="warning",
                    message="Grease trap service date not recorded",
                    remedy="Update grease trap maintenance records",
                )
            )
        else:
            last_service_date = datetime.fromisoformat(last_service)
            days_since = (datetime.now(UTC) - last_service_date).days

            if days_since > max_interval_days:
                eval.add_violation(
                    ComplianceViolation(
                        rule_id="GREASE_MAINTENANCE",
                        severity="medium",
                        message=f"Grease trap overdue for service ({days_since} days since last service)",
                        remedy=f"Schedule grease trap service (required every {max_interval_days} days)",
                    )
                )
            elif days_since >= max(max_interval_days - 30, 0):
                remaining_days = max_interval_days - days_since
                remedy_text = (
                    f"Plan grease trap service within {remaining_days} days"
                    if remaining_days > 0
                    else "Schedule grease trap service immediately"
                )
                eval.add_warning(
                    ComplianceViolation(
                        rule_id="GREASE_MAINTENANCE",
                        severity="warning",
                        message=f"Grease trap service due soon ({days_since} days since last service)",
                        remedy=remedy_text,
                    )
                )


# Example usage
if __name__ == "__main__":
    kernel = MunicipalComplianceKernel("san_francisco")

    # Example compliant booking
    evaluation = kernel.evaluate_booking(
        kitchen_data={
            "permits": [
                {
                    "kind": "shared_kitchen",
                    "status": "active",
                    "expires_at": "2025-12-31T00:00:00Z",
                },
                {"kind": "fire", "status": "active", "expires_at": "2025-12-31T00:00:00Z"},
                {"kind": "ventilation", "status": "active", "expires_at": "2025-12-31T00:00:00Z"},
                {"kind": "health_permit", "status": "active", "expires_at": "2025-12-31T00:00:00Z"},
            ],
            "zoning": {"neighborhood_notice_doc_id": "abc123"},
            "ada_accessible": True,
            "grease": {"last_service_at": "2025-10-01T00:00:00Z"},
        },
        maker_data={
            "insurance": {
                "general_liability_cents": 100000000,
                "aggregate_cents": 200000000,
                "additional_insured_text": "City and County of San Francisco",
            },
            "requires_ada_access": False,
        },
        booking_data={"start": "2025-11-15T10:00:00Z", "end": "2025-11-15T18:00:00Z", "hours": 8},
    )

    print(f"Result: {evaluation.result.value}")
    print(f"Violations: {len(evaluation.violations)}")
    print(f"Warnings: {len(evaluation.warnings)}")

    for violation in evaluation.violations:
        print(f"\n[{violation.severity}] {violation.message}")
        if violation.remedy:
            print(f"  Remedy: {violation.remedy}")
