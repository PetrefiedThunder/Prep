"""
Improved Compliance Engine (D15)
Enhanced JSON summary with confidence scores, violation codes, and remediation steps
"""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class ViolationDetail:
    violation_code: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    description: str
    rule_id: str
    confidence: float
    remediation_steps: list[str]
    detected_at: str


@dataclass
class ComplianceResult:
    certificate_id: str
    certificate_type: str
    overall_pass: bool
    confidence_score: float
    violations: list[ViolationDetail]
    metadata: dict[str, Any]
    validation_timestamp: str
    validator_version: str


class ComplianceEngine:
    """Enhanced compliance validation engine with structured output"""

    VERSION = "2.0.0"

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> dict[str, Any]:
        """Load compliance rules (would come from database/config)"""
        return {
            "health_permit": {
                "expiration_check": {"severity": "critical", "confidence": 1.0, "code": "HP-001"},
                "issuing_agency_valid": {"severity": "high", "confidence": 0.9, "code": "HP-002"},
                "signature_present": {"severity": "medium", "confidence": 0.85, "code": "HP-003"},
            },
            "food_handler": {
                "expiration_check": {"severity": "critical", "confidence": 1.0, "code": "FH-001"},
                "certification_level": {"severity": "high", "confidence": 0.9, "code": "FH-002"},
            },
            "business_license": {
                "expiration_check": {"severity": "critical", "confidence": 1.0, "code": "BL-001"},
                "jurisdiction_match": {"severity": "high", "confidence": 0.85, "code": "BL-002"},
            },
        }

    def validate(
        self,
        certificate_id: str,
        certificate_type: str,
        document_text: str,
        metadata: dict[str, Any],
    ) -> ComplianceResult:
        """
        Validate a certificate with enhanced structured output

        Args:
            certificate_id: Unique certificate identifier
            certificate_type: Type of certificate
            document_text: Extracted text from document
            metadata: Additional metadata (expiration, issuer, etc.)

        Returns:
            ComplianceResult with detailed violations and confidence scores
        """
        violations: list[ViolationDetail] = []

        # Apply rules for this certificate type
        type_rules = self.rules.get(certificate_type, {})

        # Rule 1: Expiration check
        if "expiration_date" in metadata:
            expiration = metadata["expiration_date"]
            if self._is_expired(expiration):
                violations.append(
                    ViolationDetail(
                        violation_code=type_rules["expiration_check"]["code"],
                        severity=type_rules["expiration_check"]["severity"],
                        description=f"Certificate expired on {expiration}",
                        rule_id="expiration_check",
                        confidence=type_rules["expiration_check"]["confidence"],
                        remediation_steps=[
                            "Renew certificate with issuing agency",
                            "Upload updated certificate to platform",
                            "Wait for re-validation",
                        ],
                        detected_at=datetime.now(UTC).isoformat(),
                    )
                )

        # Rule 2: Issuing agency validation
        if "issuing_agency" in metadata:
            agency = metadata["issuing_agency"]
            if not self._is_valid_agency(agency, certificate_type):
                violations.append(
                    ViolationDetail(
                        violation_code=type_rules.get("issuing_agency_valid", {}).get(
                            "code", "GEN-001"
                        ),
                        severity="high",
                        description=f"Unrecognized issuing agency: {agency}",
                        rule_id="issuing_agency_valid",
                        confidence=0.85,
                        remediation_steps=[
                            "Verify agency is authorized to issue this certificate type",
                            "Contact support if agency should be recognized",
                            "Upload certificate from recognized agency",
                        ],
                        detected_at=datetime.now(UTC).isoformat(),
                    )
                )

        # Rule 3: Document completeness (signature, seal)
        if certificate_type == "health_permit":
            if not self._has_signature(document_text):
                violations.append(
                    ViolationDetail(
                        violation_code="HP-003",
                        severity="medium",
                        description="Missing signature or seal",
                        rule_id="signature_present",
                        confidence=0.8,
                        remediation_steps=[
                            "Ensure document includes official signature",
                            "Verify seal is visible and legible",
                            "Upload higher quality scan if needed",
                        ],
                        detected_at=datetime.now(UTC).isoformat(),
                    )
                )

        # Calculate overall confidence and pass/fail
        overall_pass = len([v for v in violations if v.severity in ["critical", "high"]]) == 0

        # Average confidence across all checks
        confidence_score = self._calculate_confidence(violations)

        return ComplianceResult(
            certificate_id=certificate_id,
            certificate_type=certificate_type,
            overall_pass=overall_pass,
            confidence_score=confidence_score,
            violations=violations,
            metadata={
                "total_violations": len(violations),
                "critical_violations": len([v for v in violations if v.severity == "critical"]),
                "high_violations": len([v for v in violations if v.severity == "high"]),
                "checks_performed": len(type_rules),
                "document_quality": self._assess_document_quality(document_text),
            },
            validation_timestamp=datetime.now(UTC).isoformat(),
            validator_version=self.VERSION,
        )

    def _is_expired(self, expiration_date: str) -> bool:
        """Check if certificate is expired"""
        try:
            exp = datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
            return exp < datetime.now(UTC)
        except:
            return True  # Assume expired if date is invalid

    def _is_valid_agency(self, agency: str, cert_type: str) -> bool:
        """Check if issuing agency is recognized"""
        recognized_agencies = {
            "health_permit": [
                "County Health Department",
                "State Health Department",
                "City Health Dept",
            ],
            "food_handler": ["ServSafe", "National Registry", "State Board"],
            "business_license": ["City Clerk", "County Clerk", "State Business Bureau"],
        }

        valid_agencies = recognized_agencies.get(cert_type, [])
        return any(valid.lower() in agency.lower() for valid in valid_agencies)

    def _has_signature(self, document_text: str) -> bool:
        """Check if document has signature indicators"""
        signature_indicators = ["signed", "signature", "authorized by", "seal"]
        return any(indicator in document_text.lower() for indicator in signature_indicators)

    def _calculate_confidence(self, violations: list[ViolationDetail]) -> float:
        """Calculate overall confidence score"""
        if not violations:
            return 0.95  # High confidence if no violations

        # Average confidence of all checks
        total_confidence = sum(v.confidence for v in violations)
        avg_confidence = total_confidence / len(violations) if violations else 0.95

        # Reduce confidence if multiple violations
        confidence_penalty = 0.1 * len(violations)
        return max(0.5, avg_confidence - confidence_penalty)

    def _assess_document_quality(self, document_text: str) -> str:
        """Assess quality of document text extraction"""
        if len(document_text) < 100:
            return "poor"
        elif len(document_text) < 500:
            return "fair"
        else:
            return "good"

    def to_json(self, result: ComplianceResult) -> dict[str, Any]:
        """Convert result to JSON-serializable dict"""
        return asdict(result)


# Example usage
if __name__ == "__main__":
    engine = ComplianceEngine()

    # Test case
    result = engine.validate(
        certificate_id="cert-123",
        certificate_type="health_permit",
        document_text="This health permit is issued... signature on file...",
        metadata={
            "expiration_date": "2024-01-01T00:00:00Z",  # Expired
            "issuing_agency": "County Health Department",
        },
    )

    import json

    print(json.dumps(engine.to_json(result), indent=2))
