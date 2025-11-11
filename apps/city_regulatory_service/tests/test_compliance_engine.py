"""
Tests for City Compliance Engine

This test suite covers the compliance engine functionality for
validating facility compliance against city regulations.
"""

import os
import sys
from datetime import UTC, datetime, timedelta

import pytest

# Add paths to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from prep.compliance.city_compliance_engine import CityComplianceEngine


class TestCityComplianceEngine:
    """Test the city compliance engine"""

    @pytest.fixture
    def engine(self):
        """Create a test engine instance"""
        return CityComplianceEngine(
            city_name="San Francisco",
            state="CA",
            facility_type="commercial_kitchen"
        )

    @pytest.fixture
    def compliant_facility_data(self):
        """Sample data for a compliant facility"""
        now = datetime.now(UTC)
        future_date = (now + timedelta(days=180)).isoformat()

        return {
            "facility_id": "compliant-facility-123",
            "facility_type": "commercial_kitchen",
            "city": "San Francisco",
            "state": "CA",
            "health_permit": {
                "number": "HP-2024-001",
                "issue_date": (now - timedelta(days=90)).isoformat(),
                "expiration_date": future_date,
                "status": "active",
            },
            "business_license": {
                "number": "BL-2024-001",
                "issue_date": (now - timedelta(days=60)).isoformat(),
                "expiration_date": future_date,
                "status": "valid",
            },
            "insurance": [
                {
                    "type": "general_liability",
                    "provider": "Insurance Co",
                    "policy_number": "GL-123456",
                    "coverage_amount": 2000000.0,
                    "effective_date": (now - timedelta(days=30)).isoformat(),
                    "expiration_date": future_date,
                },
                {
                    "type": "workers_compensation",
                    "provider": "Insurance Co",
                    "policy_number": "WC-789012",
                    "coverage_amount": 1000000.0,
                    "effective_date": (now - timedelta(days=30)).isoformat(),
                    "expiration_date": future_date,
                },
            ],
            "certifications": [
                {
                    "type": "food_handler",
                    "holder_name": "John Doe",
                    "number": "FH-2024-001",
                    "issue_date": (now - timedelta(days=30)).isoformat(),
                    "expiration_date": future_date,
                },
                {
                    "type": "food_safety_manager",
                    "holder_name": "Jane Smith",
                    "number": "FSM-2024-001",
                    "issue_date": (now - timedelta(days=60)).isoformat(),
                    "expiration_date": future_date,
                },
            ],
            "fire_safety": {
                "last_inspection_date": (now - timedelta(days=90)).isoformat(),
                "inspection_status": "passed",
                "next_inspection_due": (now + timedelta(days=275)).isoformat(),
            },
            "employee_count": 8,
            "grease_trap": {
                "installed": True,
                "last_cleaning_date": (now - timedelta(days=45)).isoformat(),
                "maintenance_logs": True,
            },
            "waste_management": {
                "disposal_contract": True,
                "recycling_program": True,
            },
        }

    def test_engine_initialization(self, engine):
        """Test engine initialization"""
        assert engine.city_name == "San Francisco"
        assert engine.state == "CA"
        assert engine.facility_type == "commercial_kitchen"
        assert engine.engine_version == "1.0.0"

    def test_load_rules(self, engine):
        """Test loading compliance rules"""
        engine.load_rules()
        assert len(engine.rules) > 0
        assert len(engine.rule_versions) > 0

        # Check that critical rules are present
        rule_ids = [rule.id for rule in engine.rules]
        assert "CITY-HEALTH-001" in rule_ids
        assert "CITY-BIZ-001" in rule_ids
        assert "CITY-INS-001" in rule_ids
        assert "CITY-FIRE-001" in rule_ids

    def test_validate_compliant_facility(self, engine, compliant_facility_data):
        """Test validation of a fully compliant facility"""
        engine.load_rules()
        violations = engine.validate(compliant_facility_data)

        # Should have minimal violations (maybe permit renewal warnings)
        assert isinstance(violations, list)
        # All violations should be low severity or warnings
        critical_violations = [v for v in violations if v.severity == "critical"]
        assert len(critical_violations) == 0

    def test_validate_missing_health_permit(self, engine, compliant_facility_data):
        """Test validation when health permit is missing"""
        engine.load_rules()
        data = compliant_facility_data.copy()
        del data["health_permit"]

        violations = engine.validate(data)

        # Should have critical violation for missing health permit
        health_violations = [v for v in violations if v.rule_id == "CITY-HEALTH-001"]
        assert len(health_violations) > 0
        assert health_violations[0].severity == "critical"

    def test_validate_expired_health_permit(self, engine, compliant_facility_data):
        """Test validation when health permit is expired"""
        engine.load_rules()
        data = compliant_facility_data.copy()
        data["health_permit"]["expiration_date"] = (
            datetime.now(UTC) - timedelta(days=30)
        ).isoformat()

        violations = engine.validate(data)

        # Should have critical violation for expired health permit
        health_violations = [v for v in violations if v.rule_id == "CITY-HEALTH-001"]
        assert len(health_violations) > 0
        assert "expired" in health_violations[0].message.lower()

    def test_validate_missing_business_license(self, engine, compliant_facility_data):
        """Test validation when business license is missing"""
        engine.load_rules()
        data = compliant_facility_data.copy()
        del data["business_license"]

        violations = engine.validate(data)

        # Should have critical violation for missing business license
        biz_violations = [v for v in violations if v.rule_id == "CITY-BIZ-001"]
        assert len(biz_violations) > 0
        assert biz_violations[0].severity == "critical"

    def test_validate_insufficient_insurance(self, engine, compliant_facility_data):
        """Test validation when insurance coverage is insufficient"""
        engine.load_rules()
        data = compliant_facility_data.copy()
        # Set coverage below minimum ($1M)
        data["insurance"][0]["coverage_amount"] = 500000.0

        violations = engine.validate(data)

        # Should have critical violation for insufficient coverage
        ins_violations = [v for v in violations if v.rule_id == "CITY-INS-001"]
        assert len(ins_violations) > 0
        assert "below minimum" in ins_violations[0].message.lower()

    def test_validate_missing_workers_comp(self, engine, compliant_facility_data):
        """Test validation when workers comp is missing for facility with employees"""
        engine.load_rules()
        data = compliant_facility_data.copy()
        # Remove workers comp but keep employees
        data["insurance"] = [ins for ins in data["insurance"] if ins["type"] != "workers_compensation"]

        violations = engine.validate(data)

        # Should have violation for missing workers comp
        wc_violations = [v for v in violations if v.rule_id == "CITY-INS-002"]
        assert len(wc_violations) > 0

    def test_validate_no_workers_comp_needed_no_employees(self, engine, compliant_facility_data):
        """Test validation when no workers comp needed (no employees)"""
        engine.load_rules()
        data = compliant_facility_data.copy()
        data["employee_count"] = 0
        data["insurance"] = [ins for ins in data["insurance"] if ins["type"] != "workers_compensation"]

        violations = engine.validate(data)

        # Should not have violation for missing workers comp when no employees
        wc_violations = [v for v in violations if v.rule_id == "CITY-INS-002"]
        assert len(wc_violations) == 0

    def test_validate_missing_food_handler_cert(self, engine, compliant_facility_data):
        """Test validation when food handler certifications are missing"""
        engine.load_rules()
        data = compliant_facility_data.copy()
        data["certifications"] = [c for c in data["certifications"] if c["type"] != "food_handler"]

        violations = engine.validate(data)

        # Should have high severity violation for missing food handler certs
        cert_violations = [v for v in violations if v.rule_id == "CITY-CERT-001"]
        assert len(cert_violations) > 0
        assert cert_violations[0].severity == "high"

    def test_validate_failed_fire_inspection(self, engine, compliant_facility_data):
        """Test validation when fire inspection failed"""
        engine.load_rules()
        data = compliant_facility_data.copy()
        data["fire_safety"]["inspection_status"] = "failed"

        violations = engine.validate(data)

        # Should have critical violation for failed fire inspection
        fire_violations = [v for v in violations if v.rule_id == "CITY-FIRE-001"]
        assert len(fire_violations) > 0
        assert fire_violations[0].severity == "critical"

    def test_validate_overdue_fire_inspection(self, engine, compliant_facility_data):
        """Test validation when fire inspection is overdue"""
        engine.load_rules()
        data = compliant_facility_data.copy()
        data["fire_safety"]["next_inspection_due"] = (
            datetime.now(UTC) - timedelta(days=30)
        ).isoformat()

        violations = engine.validate(data)

        # Should have violation for overdue inspection
        fire_violations = [v for v in violations if v.rule_id == "CITY-FIRE-001"]
        assert len(fire_violations) > 0
        assert "overdue" in fire_violations[0].message.lower()

    def test_validate_grease_trap_issues(self, engine, compliant_facility_data):
        """Test validation when grease trap is not maintained"""
        engine.load_rules()
        data = compliant_facility_data.copy()
        # Set last cleaning to over 90 days ago
        data["grease_trap"]["last_cleaning_date"] = (
            datetime.now(UTC) - timedelta(days=120)
        ).isoformat()

        violations = engine.validate(data)

        # Should have medium severity violation for overdue grease trap cleaning
        grease_violations = [v for v in violations if v.rule_id == "CITY-ENV-001"]
        assert len(grease_violations) > 0
        assert "overdue" in grease_violations[0].message.lower()

    def test_validate_permits_expiring_soon(self, engine, compliant_facility_data):
        """Test validation when permits are expiring within 30 days"""
        engine.load_rules()
        data = compliant_facility_data.copy()
        # Set health permit to expire in 15 days
        data["health_permit"]["expiration_date"] = (
            datetime.now(UTC) + timedelta(days=15)
        ).isoformat()

        violations = engine.validate(data)

        # Should have high severity violation for permits expiring soon
        renewal_violations = [v for v in violations if v.rule_id == "CITY-ADMIN-001"]
        assert len(renewal_violations) > 0
        assert "expiring" in renewal_violations[0].message.lower()

    def test_generate_report(self, engine, compliant_facility_data):
        """Test generating a compliance report"""
        engine.load_rules()
        report = engine.generate_report(compliant_facility_data)

        assert report.engine_name.startswith("CityComplianceEngine")
        assert report.total_rules_checked > 0
        assert isinstance(report.violations_found, list)
        assert isinstance(report.passed_rules, list)
        assert 0.0 <= report.overall_compliance_score <= 1.0
        assert len(report.summary) > 0
        assert len(report.recommendations) > 0

    def test_generate_report_non_compliant(self, engine):
        """Test generating a report for non-compliant facility"""
        engine.load_rules()

        # Minimal data - should have many violations
        minimal_data = {
            "facility_id": "non-compliant-123",
            "facility_type": "commercial_kitchen",
            "city": "San Francisco",
            "state": "CA",
            "employee_count": 5,
        }

        report = engine.generate_report(minimal_data)

        # Should have low compliance score
        assert report.overall_compliance_score < 0.5
        assert len(report.violations_found) > 5

        # Should have critical violations
        critical_violations = [v for v in report.violations_found if v.severity == "critical"]
        assert len(critical_violations) > 0

        # Should have recommendations to address critical issues
        assert any("critical" in rec.lower() for rec in report.recommendations)


# Run pytest if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
