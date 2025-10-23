from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .base_engine import ComplianceEngine, ComplianceRule, ComplianceViolation


class MultiVoiceComplianceUI(ComplianceEngine):
    """Multi-language compliance user interface engine."""

    def __init__(self) -> None:
        super().__init__("MultiVoice_Compliance_UI")
        self.supported_languages = ["en", "es", "fr", "de", "zh"]
        self.load_rules()

    def load_rules(self) -> None:  # type: ignore[override]
        now = datetime.now(timezone.utc)
        self.rules = [
            ComplianceRule(
                id="ui_accessibility_1",
                name="Accessibility Standards",
                description="UI must meet WCAG 2.1 accessibility standards",
                category="accessibility",
                severity="high",
                applicable_regulations=["WCAG_2.1"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="ui_localization_1",
                name="Localization Requirements",
                description="Content must be properly localized for target markets",
                category="localization",
                severity="medium",
                applicable_regulations=["ISO_17100"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="ui_consent_1",
                name="Consent Interface",
                description="Consent mechanisms must be clear and unambiguous",
                category="user_interface",
                severity="critical",
                applicable_regulations=["GDPR", "CCPA"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="ui_transparency_1",
                name="Transparency Requirements",
                description="Privacy and compliance information must be transparent",
                category="transparency",
                severity="high",
                applicable_regulations=["GDPR", "CCPA"],
                created_at=now,
                updated_at=now,
            ),
        ]

    def validate(self, data: Dict[str, Any]) -> List[ComplianceViolation]:  # type: ignore[override]
        violations: List[ComplianceViolation] = []

        violations.extend(self._validate_accessibility(data))
        violations.extend(self._validate_localization(data))
        violations.extend(self._validate_consent_interface(data))
        violations.extend(self._validate_transparency(data))

        return violations

    def _validate_accessibility(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []

        for element in data.get("ui_elements", []):
            element_type = element.get("type")
            if element_type in {"image", "button", "link"}:
                has_accessibility = element.get("aria_label") or element.get("alt_text")
                if not has_accessibility:
                    violations.append(
                        ComplianceViolation(
                            rule_id="ui_accessibility_1",
                            rule_name="Accessibility Standards",
                            message=(
                                "UI element missing accessibility attributes: "
                                f"{element.get('id', 'unnamed')}"
                            ),
                            severity="high",
                            context={
                                "element_id": element.get("id"),
                                "element_type": element_type,
                                "missing_attributes": ["aria_label", "alt_text"],
                            },
                            timestamp=datetime.now(timezone.utc),
                        )
                    )

        return violations

    def _validate_localization(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []

        content = data.get("localized_content", {})
        target_languages = data.get("target_languages", [])

        for language in target_languages:
            language_content = content.get(language)
            if language_content is None:
                violations.append(
                    ComplianceViolation(
                        rule_id="ui_localization_1",
                        rule_name="Localization Requirements",
                        message=f"Missing localized content for language: {language}",
                        severity="medium",
                        context={
                            "missing_language": language,
                            "available_languages": list(content.keys()),
                        },
                        timestamp=datetime.now(timezone.utc),
                    )
                )
            elif not language_content.get("translated", False):
                violations.append(
                    ComplianceViolation(
                        rule_id="ui_localization_1",
                        rule_name="Localization Requirements",
                        message=f"Content for {language} not marked as translated",
                        severity="medium",
                        context={
                            "language": language,
                            "translation_status": language_content.get("translated", False),
                        },
                        timestamp=datetime.now(timezone.utc),
                    )
                )

        return violations

    def _validate_consent_interface(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []

        for mechanism in data.get("consent_mechanisms", []):
            if not mechanism.get("clear_options", False):
                violations.append(
                    ComplianceViolation(
                        rule_id="ui_consent_1",
                        rule_name="Consent Interface",
                        message=(
                            f"Consent mechanism lacks clear options: {mechanism.get('type', 'unknown')}"
                        ),
                        severity="critical",
                        context={
                            "mechanism_type": mechanism.get("type"),
                            "clear_options": mechanism.get("clear_options", False),
                        },
                        timestamp=datetime.now(timezone.utc),
                    )
                )

            purposes = mechanism.get("purposes", [])
            if not purposes:
                violations.append(
                    ComplianceViolation(
                        rule_id="ui_consent_1",
                        rule_name="Consent Interface",
                        message="Consent mechanism lacks purpose specification",
                        severity="high",
                        context={
                            "mechanism_type": mechanism.get("type"),
                            "purposes_specified": len(purposes),
                        },
                        timestamp=datetime.now(timezone.utc),
                    )
                )

        return violations

    def _validate_transparency(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []

        privacy_info = data.get("privacy_information", {})
        required_sections = ["data_collection", "data_usage", "data_sharing", "user_rights"]

        for section in required_sections:
            if not privacy_info.get(section):
                violations.append(
                    ComplianceViolation(
                        rule_id="ui_transparency_1",
                        rule_name="Transparency Requirements",
                        message=f"Missing transparency information section: {section}",
                        severity="high",
                        context={
                            "missing_section": section,
                            "available_sections": list(privacy_info.keys()),
                        },
                        timestamp=datetime.now(timezone.utc),
                    )
                )

        return violations
