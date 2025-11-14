"""
City Compliance Engine

This engine validates kitchen/facility compliance against city-level regulations
including health permits, business licenses, insurance requirements, and
operational certifications.
"""

import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any

# Add parent directory to path to import from prep package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from prep.compliance.base_engine import (
    ComplianceEngine,
    ComplianceRule,
    ComplianceViolation,
)


class CityComplianceEngine(ComplianceEngine):
    """
    Compliance engine for city-level regulations.

    This engine checks:
    - Health permits and certifications
    - Business licenses
    - Insurance coverage requirements
    - Fire safety compliance
    - Food handler certifications
    - Zoning and operational permits
    """

    def __init__(
        self,
        city_name: str,
        state: str,
        facility_type: str,
        engine_version: str = "1.0.0",
    ):
        """
        Initialize the city compliance engine.

        Args:
            city_name: Name of the city
            state: State code (e.g., 'CA')
            facility_type: Type of facility (e.g., 'commercial_kitchen')
            engine_version: Version of the engine
        """
        super().__init__(
            name=f"CityComplianceEngine[{city_name},{state}]",
            engine_version=engine_version,
        )
        self.city_name = city_name
        self.state = state
        self.facility_type = facility_type
        self.logger = logging.getLogger(f"compliance.city.{city_name}.{state}")

    def load_rules(self) -> None:
        """
        Load city-specific compliance rules.

        In production, these would be loaded from the city regulatory database.
        This implementation provides a template that will be populated with
        actual city data.
        """
        self.rules = []

        # Rule 1: Health Permit
        self.add_rule(
            ComplianceRule(
                id="CITY-HEALTH-001",
                name="Valid Health Permit",
                description=f"Facility must have a valid health permit from {self.city_name} Health Department",
                category="health_safety",
                severity="critical",
                applicable_regulations=[
                    f"{self.city_name} Health Code",
                    "Food Service Establishment Regulations",
                ],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        self.rule_versions["CITY-HEALTH-001"] = "1.0.0"

        # Rule 2: Business License
        self.add_rule(
            ComplianceRule(
                id="CITY-BIZ-001",
                name="Valid Business License",
                description=f"Facility must have a valid business operating license from {self.city_name}",
                category="business_operations",
                severity="critical",
                applicable_regulations=[
                    f"{self.city_name} Business Code",
                    "Commercial Operations License",
                ],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        self.rule_versions["CITY-BIZ-001"] = "1.0.0"

        # Rule 3: General Liability Insurance
        self.add_rule(
            ComplianceRule(
                id="CITY-INS-001",
                name="General Liability Insurance",
                description="Facility must maintain general liability insurance with minimum required coverage",
                category="insurance",
                severity="critical",
                applicable_regulations=[
                    f"{self.city_name} Insurance Requirements",
                    "Commercial General Liability Coverage",
                ],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        self.rule_versions["CITY-INS-001"] = "1.0.0"

        # Rule 4: Workers Compensation Insurance
        self.add_rule(
            ComplianceRule(
                id="CITY-INS-002",
                name="Workers Compensation Insurance",
                description="Facility with employees must have workers compensation insurance",
                category="insurance",
                severity="critical",
                applicable_regulations=[
                    f"{self.state} Workers Compensation Law",
                    f"{self.city_name} Employment Requirements",
                ],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        self.rule_versions["CITY-INS-002"] = "1.0.0"

        # Rule 5: Food Handler Certification
        self.add_rule(
            ComplianceRule(
                id="CITY-CERT-001",
                name="Food Handler Certification",
                description="All food handling staff must have valid food handler certifications",
                category="certifications",
                severity="high",
                applicable_regulations=[
                    f"{self.city_name} Food Safety Code",
                    "Food Handler Training Requirements",
                ],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        self.rule_versions["CITY-CERT-001"] = "1.0.0"

        # Rule 6: Fire Safety Inspection
        self.add_rule(
            ComplianceRule(
                id="CITY-FIRE-001",
                name="Fire Safety Inspection",
                description=f"Facility must pass annual fire safety inspection from {self.city_name} Fire Department",
                category="fire_safety",
                severity="critical",
                applicable_regulations=[
                    f"{self.city_name} Fire Code",
                    "Commercial Kitchen Fire Safety",
                ],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        self.rule_versions["CITY-FIRE-001"] = "1.0.0"

        # Rule 7: Food Safety Manager Certification
        self.add_rule(
            ComplianceRule(
                id="CITY-CERT-002",
                name="Food Safety Manager Certification",
                description="At least one certified food safety manager must be on staff",
                category="certifications",
                severity="high",
                applicable_regulations=[
                    f"{self.city_name} Health Code",
                    "Food Safety Manager Requirements",
                ],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        self.rule_versions["CITY-CERT-002"] = "1.0.0"

        # Rule 8: Grease Trap Maintenance
        self.add_rule(
            ComplianceRule(
                id="CITY-ENV-001",
                name="Grease Trap Maintenance",
                description="Commercial kitchen must have properly maintained grease trap with regular cleaning logs",
                category="environmental",
                severity="medium",
                applicable_regulations=[
                    f"{self.city_name} Environmental Code",
                    "Grease Trap Regulations",
                ],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        self.rule_versions["CITY-ENV-001"] = "1.0.0"

        # Rule 9: Waste Disposal Compliance
        self.add_rule(
            ComplianceRule(
                id="CITY-ENV-002",
                name="Waste Disposal Compliance",
                description="Facility must comply with city waste disposal and recycling requirements",
                category="environmental",
                severity="medium",
                applicable_regulations=[
                    f"{self.city_name} Waste Management Code",
                    "Commercial Waste Disposal",
                ],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        self.rule_versions["CITY-ENV-002"] = "1.0.0"

        # Rule 10: Permit Renewal Timeliness
        self.add_rule(
            ComplianceRule(
                id="CITY-ADMIN-001",
                name="Timely Permit Renewals",
                description="All permits and licenses must be renewed before expiration",
                category="administrative",
                severity="high",
                applicable_regulations=[
                    f"{self.city_name} Administrative Code",
                    "Permit Renewal Requirements",
                ],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        self.rule_versions["CITY-ADMIN-001"] = "1.0.0"

        self.logger.info(
            f"Loaded {len(self.rules)} city compliance rules for {self.city_name}, {self.state}"
        )

    def validate(self, data: dict[str, Any]) -> list[ComplianceViolation]:
        """
        Validate facility data against city compliance rules.

        Args:
            data: Facility data including permits, licenses, insurance, etc.

        Expected data structure:
        {
            "facility_id": str,
            "facility_type": str,
            "city": str,
            "state": str,
            "health_permit": {
                "number": str,
                "issue_date": str (ISO format),
                "expiration_date": str (ISO format),
                "status": str,
            },
            "business_license": {
                "number": str,
                "issue_date": str (ISO format),
                "expiration_date": str (ISO format),
                "status": str,
            },
            "insurance": [
                {
                    "type": str,  # "general_liability", "workers_comp", etc.
                    "provider": str,
                    "policy_number": str,
                    "coverage_amount": float,
                    "effective_date": str (ISO format),
                    "expiration_date": str (ISO format),
                }
            ],
            "certifications": [
                {
                    "type": str,  # "food_handler", "food_safety_manager"
                    "holder_name": str,
                    "number": str,
                    "issue_date": str (ISO format),
                    "expiration_date": str (ISO format),
                }
            ],
            "fire_safety": {
                "last_inspection_date": str (ISO format),
                "inspection_status": str,  # "passed", "failed", "pending"
                "next_inspection_due": str (ISO format),
            },
            "employee_count": int,
            "grease_trap": {
                "installed": bool,
                "last_cleaning_date": str (ISO format),
                "maintenance_logs": bool,
            },
            "waste_management": {
                "disposal_contract": bool,
                "recycling_program": bool,
            }
        }

        Returns:
            List of compliance violations
        """
        violations = []
        now = datetime.now(UTC)

        # Check CITY-HEALTH-001: Valid Health Permit
        violations.extend(self._check_health_permit(data, now))

        # Check CITY-BIZ-001: Valid Business License
        violations.extend(self._check_business_license(data, now))

        # Check CITY-INS-001: General Liability Insurance
        violations.extend(self._check_general_liability(data, now))

        # Check CITY-INS-002: Workers Compensation
        violations.extend(self._check_workers_comp(data, now))

        # Check CITY-CERT-001: Food Handler Certifications
        violations.extend(self._check_food_handler_certs(data, now))

        # Check CITY-FIRE-001: Fire Safety Inspection
        violations.extend(self._check_fire_safety(data, now))

        # Check CITY-CERT-002: Food Safety Manager
        violations.extend(self._check_food_safety_manager(data, now))

        # Check CITY-ENV-001: Grease Trap
        violations.extend(self._check_grease_trap(data, now))

        # Check CITY-ENV-002: Waste Disposal
        violations.extend(self._check_waste_disposal(data, now))

        # Check CITY-ADMIN-001: Permit Renewals
        violations.extend(self._check_permit_renewals(data, now))

        self.logger.info(f"Validation complete: {len(violations)} violations found")
        return violations

    def _check_health_permit(
        self, data: dict[str, Any], now: datetime
    ) -> list[ComplianceViolation]:
        """Check health permit compliance"""
        violations = []
        health_permit = data.get("health_permit")

        if not health_permit:
            violations.append(
                ComplianceViolation(
                    rule_id="CITY-HEALTH-001",
                    rule_name="Valid Health Permit",
                    message="No health permit on file",
                    severity="critical",
                    context={"facility_id": data.get("facility_id")},
                    timestamp=now,
                    rule_version="1.0.0",
                )
            )
        else:
            # Check expiration
            exp_date_str = health_permit.get("expiration_date")
            if exp_date_str:
                exp_date = datetime.fromisoformat(exp_date_str.replace("Z", "+00:00"))
                if exp_date < now:
                    violations.append(
                        ComplianceViolation(
                            rule_id="CITY-HEALTH-001",
                            rule_name="Valid Health Permit",
                            message="Health permit has expired",
                            severity="critical",
                            context={
                                "facility_id": data.get("facility_id"),
                                "expiration_date": exp_date_str,
                                "days_expired": (now - exp_date).days,
                            },
                            timestamp=now,
                            rule_version="1.0.0",
                            observed_value=exp_date_str,
                        )
                    )

            # Check status
            status = health_permit.get("status", "").lower()
            if status not in ["active", "valid", "current"]:
                violations.append(
                    ComplianceViolation(
                        rule_id="CITY-HEALTH-001",
                        rule_name="Valid Health Permit",
                        message=f"Health permit status is '{status}' (not active)",
                        severity="critical",
                        context={"facility_id": data.get("facility_id")},
                        timestamp=now,
                        rule_version="1.0.0",
                        observed_value=status,
                    )
                )

        return violations

    def _check_business_license(
        self, data: dict[str, Any], now: datetime
    ) -> list[ComplianceViolation]:
        """Check business license compliance"""
        violations = []
        business_license = data.get("business_license")

        if not business_license:
            violations.append(
                ComplianceViolation(
                    rule_id="CITY-BIZ-001",
                    rule_name="Valid Business License",
                    message="No business license on file",
                    severity="critical",
                    context={"facility_id": data.get("facility_id")},
                    timestamp=now,
                    rule_version="1.0.0",
                )
            )
        else:
            # Check expiration
            exp_date_str = business_license.get("expiration_date")
            if exp_date_str:
                exp_date = datetime.fromisoformat(exp_date_str.replace("Z", "+00:00"))
                if exp_date < now:
                    violations.append(
                        ComplianceViolation(
                            rule_id="CITY-BIZ-001",
                            rule_name="Valid Business License",
                            message="Business license has expired",
                            severity="critical",
                            context={
                                "facility_id": data.get("facility_id"),
                                "expiration_date": exp_date_str,
                            },
                            timestamp=now,
                            rule_version="1.0.0",
                            observed_value=exp_date_str,
                        )
                    )

        return violations

    def _check_general_liability(
        self, data: dict[str, Any], now: datetime
    ) -> list[ComplianceViolation]:
        """Check general liability insurance"""
        violations = []
        insurance_list = data.get("insurance", [])

        # Find general liability policy
        gl_policy = None
        for policy in insurance_list:
            if policy.get("type") == "general_liability":
                gl_policy = policy
                break

        if not gl_policy:
            violations.append(
                ComplianceViolation(
                    rule_id="CITY-INS-001",
                    rule_name="General Liability Insurance",
                    message="No general liability insurance policy on file",
                    severity="critical",
                    context={"facility_id": data.get("facility_id")},
                    timestamp=now,
                    rule_version="1.0.0",
                )
            )
        else:
            # Check coverage amount (minimum $1M typically)
            coverage = gl_policy.get("coverage_amount", 0)
            if coverage < 1000000:
                violations.append(
                    ComplianceViolation(
                        rule_id="CITY-INS-001",
                        rule_name="General Liability Insurance",
                        message=f"General liability coverage (${coverage:,.0f}) below minimum required ($1,000,000)",
                        severity="critical",
                        context={"facility_id": data.get("facility_id")},
                        timestamp=now,
                        rule_version="1.0.0",
                        observed_value=coverage,
                    )
                )

            # Check expiration
            exp_date_str = gl_policy.get("expiration_date")
            if exp_date_str:
                exp_date = datetime.fromisoformat(exp_date_str.replace("Z", "+00:00"))
                if exp_date < now:
                    violations.append(
                        ComplianceViolation(
                            rule_id="CITY-INS-001",
                            rule_name="General Liability Insurance",
                            message="General liability insurance has expired",
                            severity="critical",
                            context={
                                "facility_id": data.get("facility_id"),
                                "expiration_date": exp_date_str,
                            },
                            timestamp=now,
                            rule_version="1.0.0",
                        )
                    )

        return violations

    def _check_workers_comp(self, data: dict[str, Any], now: datetime) -> list[ComplianceViolation]:
        """Check workers compensation insurance"""
        violations = []
        employee_count = data.get("employee_count", 0)

        # Only required if facility has employees
        if employee_count > 0:
            insurance_list = data.get("insurance", [])
            wc_policy = None

            for policy in insurance_list:
                if policy.get("type") == "workers_compensation":
                    wc_policy = policy
                    break

            if not wc_policy:
                violations.append(
                    ComplianceViolation(
                        rule_id="CITY-INS-002",
                        rule_name="Workers Compensation Insurance",
                        message=f"No workers compensation insurance (facility has {employee_count} employees)",
                        severity="critical",
                        context={
                            "facility_id": data.get("facility_id"),
                            "employee_count": employee_count,
                        },
                        timestamp=now,
                        rule_version="1.0.0",
                    )
                )

        return violations

    def _check_food_handler_certs(
        self, data: dict[str, Any], now: datetime
    ) -> list[ComplianceViolation]:
        """Check food handler certifications"""
        violations = []
        certifications = data.get("certifications", [])

        # Find food handler certs
        food_handler_certs = [c for c in certifications if c.get("type") == "food_handler"]

        if not food_handler_certs:
            violations.append(
                ComplianceViolation(
                    rule_id="CITY-CERT-001",
                    rule_name="Food Handler Certification",
                    message="No food handler certifications on file",
                    severity="high",
                    context={"facility_id": data.get("facility_id")},
                    timestamp=now,
                    rule_version="1.0.0",
                )
            )
        else:
            # Check for expired certs
            expired_certs = []
            for cert in food_handler_certs:
                exp_date_str = cert.get("expiration_date")
                if exp_date_str:
                    exp_date = datetime.fromisoformat(exp_date_str.replace("Z", "+00:00"))
                    if exp_date < now:
                        expired_certs.append(cert.get("holder_name", "Unknown"))

            if expired_certs:
                violations.append(
                    ComplianceViolation(
                        rule_id="CITY-CERT-001",
                        rule_name="Food Handler Certification",
                        message=f"Expired food handler certifications: {', '.join(expired_certs)}",
                        severity="high",
                        context={
                            "facility_id": data.get("facility_id"),
                            "expired_count": len(expired_certs),
                        },
                        timestamp=now,
                        rule_version="1.0.0",
                    )
                )

        return violations

    def _check_fire_safety(self, data: dict[str, Any], now: datetime) -> list[ComplianceViolation]:
        """Check fire safety inspection"""
        violations = []
        fire_safety = data.get("fire_safety")

        if not fire_safety:
            violations.append(
                ComplianceViolation(
                    rule_id="CITY-FIRE-001",
                    rule_name="Fire Safety Inspection",
                    message="No fire safety inspection records on file",
                    severity="critical",
                    context={"facility_id": data.get("facility_id")},
                    timestamp=now,
                    rule_version="1.0.0",
                )
            )
        else:
            status = fire_safety.get("inspection_status", "").lower()
            if status == "failed":
                violations.append(
                    ComplianceViolation(
                        rule_id="CITY-FIRE-001",
                        rule_name="Fire Safety Inspection",
                        message="Failed most recent fire safety inspection",
                        severity="critical",
                        context={"facility_id": data.get("facility_id")},
                        timestamp=now,
                        rule_version="1.0.0",
                    )
                )

            # Check if inspection is overdue
            next_due_str = fire_safety.get("next_inspection_due")
            if next_due_str:
                next_due = datetime.fromisoformat(next_due_str.replace("Z", "+00:00"))
                if next_due < now:
                    violations.append(
                        ComplianceViolation(
                            rule_id="CITY-FIRE-001",
                            rule_name="Fire Safety Inspection",
                            message="Fire safety inspection is overdue",
                            severity="critical",
                            context={
                                "facility_id": data.get("facility_id"),
                                "next_inspection_due": next_due_str,
                                "days_overdue": (now - next_due).days,
                            },
                            timestamp=now,
                            rule_version="1.0.0",
                        )
                    )

        return violations

    def _check_food_safety_manager(
        self, data: dict[str, Any], now: datetime
    ) -> list[ComplianceViolation]:
        """Check for certified food safety manager"""
        violations = []
        certifications = data.get("certifications", [])

        # Find food safety manager cert
        manager_certs = [c for c in certifications if c.get("type") == "food_safety_manager"]

        if not manager_certs:
            violations.append(
                ComplianceViolation(
                    rule_id="CITY-CERT-002",
                    rule_name="Food Safety Manager Certification",
                    message="No certified food safety manager on staff",
                    severity="high",
                    context={"facility_id": data.get("facility_id")},
                    timestamp=now,
                    rule_version="1.0.0",
                )
            )
        else:
            # Check if cert is current
            cert = manager_certs[0]
            exp_date_str = cert.get("expiration_date")
            if exp_date_str:
                exp_date = datetime.fromisoformat(exp_date_str.replace("Z", "+00:00"))
                if exp_date < now:
                    violations.append(
                        ComplianceViolation(
                            rule_id="CITY-CERT-002",
                            rule_name="Food Safety Manager Certification",
                            message="Food safety manager certification has expired",
                            severity="high",
                            context={
                                "facility_id": data.get("facility_id"),
                                "manager": cert.get("holder_name"),
                            },
                            timestamp=now,
                            rule_version="1.0.0",
                        )
                    )

        return violations

    def _check_grease_trap(self, data: dict[str, Any], now: datetime) -> list[ComplianceViolation]:
        """Check grease trap compliance"""
        violations = []
        grease_trap = data.get("grease_trap")

        if not grease_trap or not grease_trap.get("installed"):
            violations.append(
                ComplianceViolation(
                    rule_id="CITY-ENV-001",
                    rule_name="Grease Trap Maintenance",
                    message="No grease trap installed",
                    severity="medium",
                    context={"facility_id": data.get("facility_id")},
                    timestamp=now,
                    rule_version="1.0.0",
                )
            )
        else:
            if not grease_trap.get("maintenance_logs"):
                violations.append(
                    ComplianceViolation(
                        rule_id="CITY-ENV-001",
                        rule_name="Grease Trap Maintenance",
                        message="No grease trap maintenance logs on file",
                        severity="medium",
                        context={"facility_id": data.get("facility_id")},
                        timestamp=now,
                        rule_version="1.0.0",
                    )
                )

            # Check if cleaning is overdue (typically quarterly)
            last_cleaning_str = grease_trap.get("last_cleaning_date")
            if last_cleaning_str:
                last_cleaning = datetime.fromisoformat(last_cleaning_str.replace("Z", "+00:00"))
                days_since_cleaning = (now - last_cleaning).days
                if days_since_cleaning > 90:  # 90 days = quarterly
                    violations.append(
                        ComplianceViolation(
                            rule_id="CITY-ENV-001",
                            rule_name="Grease Trap Maintenance",
                            message=f"Grease trap cleaning overdue ({days_since_cleaning} days since last cleaning)",
                            severity="medium",
                            context={
                                "facility_id": data.get("facility_id"),
                                "last_cleaning_date": last_cleaning_str,
                            },
                            timestamp=now,
                            rule_version="1.0.0",
                        )
                    )

        return violations

    def _check_waste_disposal(
        self, data: dict[str, Any], now: datetime
    ) -> list[ComplianceViolation]:
        """Check waste disposal compliance"""
        violations = []
        waste_mgmt = data.get("waste_management")

        if not waste_mgmt:
            violations.append(
                ComplianceViolation(
                    rule_id="CITY-ENV-002",
                    rule_name="Waste Disposal Compliance",
                    message="No waste management information on file",
                    severity="medium",
                    context={"facility_id": data.get("facility_id")},
                    timestamp=now,
                    rule_version="1.0.0",
                )
            )
        else:
            if not waste_mgmt.get("disposal_contract"):
                violations.append(
                    ComplianceViolation(
                        rule_id="CITY-ENV-002",
                        rule_name="Waste Disposal Compliance",
                        message="No commercial waste disposal contract on file",
                        severity="medium",
                        context={"facility_id": data.get("facility_id")},
                        timestamp=now,
                        rule_version="1.0.0",
                    )
                )

        return violations

    def _check_permit_renewals(
        self, data: dict[str, Any], now: datetime
    ) -> list[ComplianceViolation]:
        """Check for permits nearing expiration"""
        violations = []
        expiring_soon = []

        # Check health permit
        health_permit = data.get("health_permit")
        if health_permit:
            exp_date_str = health_permit.get("expiration_date")
            if exp_date_str:
                exp_date = datetime.fromisoformat(exp_date_str.replace("Z", "+00:00"))
                days_until_exp = (exp_date - now).days
                if 0 < days_until_exp <= 30:
                    expiring_soon.append(f"Health Permit ({days_until_exp} days)")

        # Check business license
        business_license = data.get("business_license")
        if business_license:
            exp_date_str = business_license.get("expiration_date")
            if exp_date_str:
                exp_date = datetime.fromisoformat(exp_date_str.replace("Z", "+00:00"))
                days_until_exp = (exp_date - now).days
                if 0 < days_until_exp <= 30:
                    expiring_soon.append(f"Business License ({days_until_exp} days)")

        # Check insurance policies
        for policy in data.get("insurance", []):
            exp_date_str = policy.get("expiration_date")
            if exp_date_str:
                exp_date = datetime.fromisoformat(exp_date_str.replace("Z", "+00:00"))
                days_until_exp = (exp_date - now).days
                if 0 < days_until_exp <= 30:
                    policy_type = policy.get("type", "Unknown").replace("_", " ").title()
                    expiring_soon.append(f"{policy_type} Insurance ({days_until_exp} days)")

        if expiring_soon:
            violations.append(
                ComplianceViolation(
                    rule_id="CITY-ADMIN-001",
                    rule_name="Timely Permit Renewals",
                    message=f"Permits/licenses expiring within 30 days: {', '.join(expiring_soon)}",
                    severity="high",
                    context={
                        "facility_id": data.get("facility_id"),
                        "expiring_count": len(expiring_soon),
                    },
                    timestamp=now,
                    rule_version="1.0.0",
                )
            )

        return violations
