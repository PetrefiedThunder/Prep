from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .base_engine import ComplianceEngine, ComplianceRule, ComplianceViolation


class DOLRegComplianceEngine(ComplianceEngine):
    """Department of Labor regulation compliance engine."""

    def __init__(self) -> None:
        super().__init__("DOL_Reg_Compliance_Engine")
        self.load_rules()

    def load_rules(self) -> None:  # type: ignore[override]
        self.rules = [
            ComplianceRule(
                id="dol_overtime_1",
                name="Overtime Pay Requirement",
                description=(
                    "Non-exempt employees must receive overtime pay for hours"
                    " worked over 40 in a workweek"
                ),
                category="wage_and_hour",
                severity="critical",
                applicable_regulations=["FLSA"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            ComplianceRule(
                id="dol_minimum_wage_1",
                name="Federal Minimum Wage",
                description="Employees must be paid at least $7.25 per hour",
                category="wage_and_hour",
                severity="critical",
                applicable_regulations=["FLSA"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            ComplianceRule(
                id="dol_child_labor_1",
                name="Child Labor Restrictions",
                description=(
                    "Prohibits employment of children under 14, limits hours for 14-15 year olds"
                ),
                category="child_labor",
                severity="critical",
                applicable_regulations=["FLSA"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            ComplianceRule(
                id="dol_record_keeping_1",
                name="Payroll Record Keeping",
                description="Employers must maintain accurate payroll records for 3 years",
                category="record_keeping",
                severity="high",
                applicable_regulations=["FLSA"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            ComplianceRule(
                id="dol_break_1",
                name="Meal and Rest Breaks",
                description="Certain states require meal and rest breaks",
                category="working_conditions",
                severity="medium",
                applicable_regulations=["State_Laws"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        ]

    def validate(self, data: dict[str, Any]) -> list[ComplianceViolation]:  # type: ignore[override]
        violations: list[ComplianceViolation] = []

        violations.extend(self._validate_overtime(data))
        violations.extend(self._validate_minimum_wage(data))
        violations.extend(self._validate_child_labor(data))
        violations.extend(self._validate_record_keeping(data))
        violations.extend(self._validate_breaks(data))

        return violations

    def _validate_overtime(self, data: dict[str, Any]) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []

        for employee in data.get("employees", []):
            hours_worked = float(employee.get("hours_worked", 0))
            hourly_rate = float(employee.get("hourly_rate", 0))
            overtime_paid = float(employee.get("overtime_paid", 0))

            if hours_worked > 40:
                required_overtime = (hours_worked - 40) * (hourly_rate * 1.5)
                if overtime_paid + 1e-6 < required_overtime:
                    violations.append(
                        ComplianceViolation(
                            rule_id="dol_overtime_1",
                            rule_name="Overtime Pay Requirement",
                            message=(
                                f"Employee {employee.get('id')} worked {hours_worked} hours "
                                "but received insufficient overtime pay"
                            ),
                            severity="critical",
                            context={
                                "employee_id": employee.get("id"),
                                "hours_worked": hours_worked,
                                "required_overtime": required_overtime,
                                "actual_overtime": overtime_paid,
                            },
                            timestamp=datetime.now(UTC),
                        )
                    )

        return violations

    def _validate_minimum_wage(self, data: dict[str, Any]) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []
        federal_min_wage = 7.25

        for employee in data.get("employees", []):
            hourly_rate = float(employee.get("hourly_rate", 0))
            if hourly_rate < federal_min_wage:
                violations.append(
                    ComplianceViolation(
                        rule_id="dol_minimum_wage_1",
                        rule_name="Federal Minimum Wage",
                        message=(
                            f"Employee {employee.get('id')} paid below federal minimum wage: "
                            f"${hourly_rate:.2f}"
                        ),
                        severity="critical",
                        context={
                            "employee_id": employee.get("id"),
                            "paid_rate": hourly_rate,
                            "minimum_rate": federal_min_wage,
                        },
                        timestamp=datetime.now(UTC),
                    )
                )

        return violations

    def _validate_child_labor(self, data: dict[str, Any]) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []

        for employee in data.get("employees", []):
            age = employee.get("age")
            hours_worked = float(employee.get("hours_worked", 0))

            if age is None:
                continue
            if int(age) < 14:
                violations.append(
                    ComplianceViolation(
                        rule_id="dol_child_labor_1",
                        rule_name="Child Labor Restrictions",
                        message=f"Employee {employee.get('id')} is under 14 years old",
                        severity="critical",
                        context={
                            "employee_id": employee.get("id"),
                            "age": age,
                        },
                        timestamp=datetime.now(UTC),
                    )
                )
            elif int(age) in {14, 15} and hours_worked > 18:
                violations.append(
                    ComplianceViolation(
                        rule_id="dol_child_labor_1",
                        rule_name="Child Labor Restrictions",
                        message=(
                            f"Employee {employee.get('id')} (age {age}) worked more than "
                            "allowed hours"
                        ),
                        severity="critical",
                        context={
                            "employee_id": employee.get("id"),
                            "age": age,
                            "hours_worked": hours_worked,
                        },
                        timestamp=datetime.now(UTC),
                    )
                )

        return violations

    def _validate_record_keeping(self, data: dict[str, Any]) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []

        for record in data.get("payroll_records", []):
            created_date = record.get("created_date")
            if isinstance(created_date, datetime):
                continue
            if isinstance(created_date, str):
                try:
                    datetime.fromisoformat(created_date)
                except ValueError:
                    violations.append(
                        ComplianceViolation(
                            rule_id="dol_record_keeping_1",
                            rule_name="Payroll Record Keeping",
                            message="Invalid date format in payroll record",
                            severity="high",
                            context={
                                "record_id": record.get("id"),
                                "date_field": created_date,
                            },
                            timestamp=datetime.now(UTC),
                        )
                    )
            else:
                violations.append(
                    ComplianceViolation(
                        rule_id="dol_record_keeping_1",
                        rule_name="Payroll Record Keeping",
                        message="Missing created_date in payroll record",
                        severity="high",
                        context={"record_id": record.get("id")},
                        timestamp=datetime.now(UTC),
                    )
                )

        return violations

    def _validate_breaks(self, data: dict[str, Any]) -> list[ComplianceViolation]:
        violations: list[ComplianceViolation] = []

        for employee in data.get("employees", []):
            hours_worked = float(employee.get("hours_worked", 0))
            breaks_taken = int(employee.get("breaks_taken", 0))

            if hours_worked >= 8 and breaks_taken < 1:
                violations.append(
                    ComplianceViolation(
                        rule_id="dol_break_1",
                        rule_name="Meal and Rest Breaks",
                        message=(
                            f"Employee {employee.get('id')} worked {hours_worked} hours "
                            "without required break"
                        ),
                        severity="medium",
                        context={
                            "employee_id": employee.get("id"),
                            "hours_worked": hours_worked,
                            "breaks_taken": breaks_taken,
                        },
                        timestamp=datetime.now(UTC),
                    )
                )

        return violations
