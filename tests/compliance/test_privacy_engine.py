from __future__ import annotations

from datetime import UTC, datetime, timedelta

from prep.compliance.gdpr_ccpa_core import GDPRCCPACore


def test_privacy_engine_initialization() -> None:
    engine = GDPRCCPACore()
    assert engine.name == "GDPR_CCPA_Compliance_Engine"
    assert len(engine.rules) >= 5


def test_consent_validation() -> None:
    engine = GDPRCCPACore()
    data = {"users": [{"id": "user1", "consent_given": False}]}
    violations = engine.validate(data)
    consent = [v for v in violations if v.rule_id == "privacy_consent_1"]
    assert len(consent) == 1
    assert consent[0].severity == "critical"
    assert all(v.timestamp.tzinfo == UTC for v in consent)


def test_data_minimization_validation() -> None:
    engine = GDPRCCPACore()
    data = {
        "collected_data": {"sensitive_data": "value"},
        "data_purpose": "",
    }
    violations = engine.validate(data)
    minimization = [v for v in violations if v.rule_id == "privacy_data_minimization_1"]
    assert len(minimization) == 1
    assert all(v.timestamp.tzinfo == UTC for v in minimization)


def test_data_breach_validation() -> None:
    engine = GDPRCCPACore()
    data = {
        "data_breaches": [
            {
                "id": "breach1",
                "detected_at": datetime.now(UTC) - timedelta(hours=80),
                "notified_at": datetime.now(UTC),
            }
        ]
    }
    violations = engine.validate(data)
    breach = [v for v in violations if v.rule_id == "privacy_data_breach_1"]
    assert len(breach) == 1
    assert breach[0].severity == "critical"
    assert all(v.timestamp.tzinfo == UTC for v in breach)


def test_third_party_sharing_validation() -> None:
    engine = GDPRCCPACore()
    data = {
        "third_party_sharing": [
            {
                "name": "PartnerA",
                "user_consent_obtained": False,
                "data_processing_agreement": False,
            }
        ]
    }
    violations = engine.validate(data)
    sharing = [v for v in violations if v.rule_id == "privacy_third_party_1"]
    assert len(sharing) == 2
    assert all(v.timestamp.tzinfo == UTC for v in sharing)
