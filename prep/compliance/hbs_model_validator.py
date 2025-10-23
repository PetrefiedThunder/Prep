from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .base_engine import ComplianceEngine, ComplianceRule, ComplianceViolation


class HBSModelValidator(ComplianceEngine):
    """Harvard Business School model validation engine."""

    def __init__(self) -> None:
        super().__init__("HBS_Model_Validator")
        self.load_rules()

    def load_rules(self) -> None:  # type: ignore[override]
        now = datetime.now(timezone.utc)
        self.rules = [
            ComplianceRule(
                id="hbs_structure_1",
                name="Model Structure Validation",
                description="Validate model structure against HBS standards",
                category="structure",
                severity="critical",
                applicable_regulations=["HBS_Standards"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="hbs_assumptions_1",
                name="Assumption Documentation",
                description="All model assumptions must be clearly documented",
                category="documentation",
                severity="high",
                applicable_regulations=["HBS_Standards"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="hbs_sensitivity_1",
                name="Sensitivity Analysis",
                description="Models must include sensitivity analysis for key variables",
                category="analysis",
                severity="medium",
                applicable_regulations=["HBS_Standards"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="hbs_data_quality_1",
                name="Data Quality Standards",
                description="Input data must meet quality and sourcing standards",
                category="data_quality",
                severity="high",
                applicable_regulations=["HBS_Standards"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="hbs_validation_1",
                name="Model Validation",
                description="Models must be validated against historical data",
                category="validation",
                severity="critical",
                applicable_regulations=["HBS_Standards"],
                created_at=now,
                updated_at=now,
            ),
        ]

    def validate(self, data: Dict[str, Any]) -> List[ComplianceViolation]:  # type: ignore[override]
        violations: List[ComplianceViolation] = []

        violations.extend(self._validate_structure(data))
        violations.extend(self._validate_assumptions(data))
        violations.extend(self._validate_sensitivity(data))
        violations.extend(self._validate_data_quality(data))
        violations.extend(self._validate_model_validation(data))

        return violations

    def _validate_structure(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        required_sections = ["inputs", "assumptions", "calculations", "outputs"]
        model_structure = data.get("model_structure", {})

        for section in required_sections:
            if section not in model_structure:
                violations.append(
                    ComplianceViolation(
                        rule_id="hbs_structure_1",
                        rule_name="Model Structure Validation",
                        message=f"Missing required model section: {section}",
                        severity="critical",
                        context={
                            "missing_section": section,
                            "available_sections": list(model_structure.keys()),
                        },
                        timestamp=datetime.now(timezone.utc),
                    )
                )

        return violations

    def _validate_assumptions(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        assumptions = data.get("assumptions", [])

        if not assumptions:
            violations.append(
                ComplianceViolation(
                    rule_id="hbs_assumptions_1",
                    rule_name="Assumption Documentation",
                    message="No assumptions documented in model",
                    severity="high",
                    context={"assumptions_count": 0},
                    timestamp=datetime.now(timezone.utc),
                )
            )

        for index, assumption in enumerate(assumptions):
            if not assumption.get("description"):
                violations.append(
                    ComplianceViolation(
                        rule_id="hbs_assumptions_1",
                        rule_name="Assumption Documentation",
                        message=f"Assumption {index + 1} lacks description",
                        severity="medium",
                        context={"assumption_index": index},
                        timestamp=datetime.now(timezone.utc),
                    )
                )
            if not assumption.get("source"):
                violations.append(
                    ComplianceViolation(
                        rule_id="hbs_assumptions_1",
                        rule_name="Assumption Documentation",
                        message=f"Assumption {index + 1} lacks source documentation",
                        severity="medium",
                        context={"assumption_index": index},
                        timestamp=datetime.now(timezone.utc),
                    )
                )

        return violations

    def _validate_sensitivity(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        sensitivity_analysis = data.get("sensitivity_analysis", {})
        key_variables = data.get("key_variables", [])

        if not sensitivity_analysis:
            violations.append(
                ComplianceViolation(
                    rule_id="hbs_sensitivity_1",
                    rule_name="Sensitivity Analysis",
                    message="No sensitivity analysis provided",
                    severity="medium",
                    context={"sensitivity_analysis_present": False},
                    timestamp=datetime.now(timezone.utc),
                )
            )
        else:
            for variable in key_variables:
                if variable not in sensitivity_analysis:
                    violations.append(
                        ComplianceViolation(
                            rule_id="hbs_sensitivity_1",
                            rule_name="Sensitivity Analysis",
                            message=(
                                f"Key variable {variable} not included in sensitivity analysis"
                            ),
                            severity="medium",
                            context={
                                "missing_variable": variable,
                                "key_variables": key_variables,
                                "analyzed_variables": list(sensitivity_analysis.keys()),
                            },
                            timestamp=datetime.now(timezone.utc),
                        )
                    )

        return violations

    def _validate_data_quality(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        input_data = data.get("input_data", {})
        data_sources = data.get("data_sources", {})

        for data_key, values in input_data.items():
            if data_key not in data_sources:
                violations.append(
                    ComplianceViolation(
                        rule_id="hbs_data_quality_1",
                        rule_name="Data Quality Standards",
                        message=f"Input data {data_key} lacks source documentation",
                        severity="high",
                        context={
                            "data_key": data_key,
                            "sources_documented": list(data_sources.keys()),
                        },
                        timestamp=datetime.now(timezone.utc),
                    )
                )

            if not values:
                violations.append(
                    ComplianceViolation(
                        rule_id="hbs_data_quality_1",
                        rule_name="Data Quality Standards",
                        message=f"Input data {data_key} is empty or missing",
                        severity="high",
                        context={"data_key": data_key, "data_length": 0},
                        timestamp=datetime.now(timezone.utc),
                    )
                )

        return violations

    def _validate_model_validation(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        validation_results = data.get("validation_results", {})
        historical_comparison = data.get("historical_comparison", {})

        if not validation_results:
            violations.append(
                ComplianceViolation(
                    rule_id="hbs_validation_1",
                    rule_name="Model Validation",
                    message="No model validation results provided",
                    severity="critical",
                    context={"validation_results_present": False},
                    timestamp=datetime.now(timezone.utc),
                )
            )

        if not historical_comparison:
            violations.append(
                ComplianceViolation(
                    rule_id="hbs_validation_1",
                    rule_name="Model Validation",
                    message="No historical data comparison performed",
                    severity="high",
                    context={"historical_comparison_present": False},
                    timestamp=datetime.now(timezone.utc),
                )
            )

        accuracy = float(validation_results.get("accuracy", 0.0))
        if accuracy < 0.8:
            violations.append(
                ComplianceViolation(
                    rule_id="hbs_validation_1",
                    rule_name="Model Validation",
                    message=f"Model validation accuracy below threshold: {accuracy:.2%}",
                    severity="critical",
                    context={"accuracy": accuracy, "threshold": 0.8},
                    timestamp=datetime.now(timezone.utc),
                )
            )

        return violations
