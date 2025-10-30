"""Tests for city ingestion adapters."""

import pytest

from apps.city_regulatory_service.src.adapters import (
    SanFranciscoAdapter,
    NewYorkCityAdapter,
)


class TestSanFranciscoAdapter:
    """Test suite for San Francisco adapter."""

    def test_city_metadata(self):
        """Test city metadata is correct."""
        assert SanFranciscoAdapter.CITY_NAME == "San Francisco"
        assert SanFranciscoAdapter.STATE == "CA"

    def test_portals_defined(self):
        """Test portal URLs are defined."""
        assert "business_registration" in SanFranciscoAdapter.PORTALS
        assert "health_permits" in SanFranciscoAdapter.PORTALS
        assert SanFranciscoAdapter.PORTALS["health_permits"].startswith("https://")

    def test_get_business_license_requirements(self):
        """Test business license requirements extraction."""
        requirements = SanFranciscoAdapter.get_business_license_requirements()

        assert len(requirements) > 0
        req = requirements[0]

        assert req["jurisdiction"] == "San Francisco"
        assert req["requirement_type"] == "business_license"
        assert "agency" in req
        assert "required_documents" in req
        assert isinstance(req["required_documents"], list)

    def test_get_health_permit_requirements(self):
        """Test health permit requirements extraction."""
        requirements = SanFranciscoAdapter.get_health_permit_requirements()

        assert len(requirements) > 0

        # Find food permit
        food_permit = next(
            (r for r in requirements if "Food" in r["requirement_label"]),
            None
        )
        assert food_permit is not None
        assert food_permit["inspection_required"] is True

    def test_get_insurance_requirements(self):
        """Test insurance requirements extraction."""
        requirements = SanFranciscoAdapter.get_insurance_requirements()

        assert len(requirements) > 0
        req = requirements[0]

        assert req["requirement_type"] == "insurance"
        assert "rules" in req
        assert "minimum_coverage" in req["rules"]

    def test_get_all_requirements(self):
        """Test getting all requirements."""
        all_reqs = SanFranciscoAdapter.get_all_requirements()

        assert len(all_reqs) > 0

        # Should include business, health, and insurance requirements
        types = {req["requirement_type"] for req in all_reqs}
        assert "business_license" in types
        assert "restaurant_license" in types or "health_permit" in types
        assert "insurance" in types


class TestNewYorkCityAdapter:
    """Test suite for New York City adapter."""

    def test_city_metadata(self):
        """Test city metadata is correct."""
        assert NewYorkCityAdapter.CITY_NAME == "New York"
        assert NewYorkCityAdapter.STATE == "NY"

    def test_portals_defined(self):
        """Test portal URLs are defined."""
        assert "business_licenses" in NewYorkCityAdapter.PORTALS
        assert "health_permits" in NewYorkCityAdapter.PORTALS
        assert NewYorkCityAdapter.PORTALS["health_permits"].startswith("https://")

    def test_get_business_license_requirements(self):
        """Test business license requirements extraction."""
        requirements = NewYorkCityAdapter.get_business_license_requirements()

        assert len(requirements) > 0
        req = requirements[0]

        assert req["jurisdiction"] == "New York"
        assert req["requirement_type"] == "business_license"
        assert "agency" in req
        assert "required_documents" in req

    def test_get_health_permit_requirements(self):
        """Test health permit requirements extraction."""
        requirements = NewYorkCityAdapter.get_health_permit_requirements()

        assert len(requirements) > 0

        # NYC should have food service and mobile food permits
        labels = {req["requirement_label"] for req in requirements}
        assert any("Food Service" in label for label in labels)

    def test_mobile_food_vending(self):
        """Test mobile food vending requirements."""
        requirements = NewYorkCityAdapter.get_health_permit_requirements()

        mobile_req = next(
            (r for r in requirements if "Mobile" in r["requirement_label"]),
            None
        )

        if mobile_req:
            assert "food truck" in mobile_req["applies_to"]
            assert mobile_req["inspection_required"] is True

    def test_get_insurance_requirements(self):
        """Test insurance requirements extraction."""
        requirements = NewYorkCityAdapter.get_insurance_requirements()

        assert len(requirements) > 0
        req = requirements[0]

        assert req["requirement_type"] == "insurance"
        assert "rules" in req

    def test_get_all_requirements(self):
        """Test getting all requirements."""
        all_reqs = NewYorkCityAdapter.get_all_requirements()

        assert len(all_reqs) > 0

        # Should include business, health, and insurance requirements
        types = {req["requirement_type"] for req in all_reqs}
        assert len(types) > 0


class TestAdapterConsistency:
    """Test consistency across adapters."""

    def test_required_fields_present(self):
        """Test that all requirements have required fields."""
        required_fields = [
            "jurisdiction",
            "requirement_type",
            "agency",
            "requirement_label",
            "applies_to",
            "required_documents",
            "official_url",
        ]

        for adapter_class in [SanFranciscoAdapter, NewYorkCityAdapter]:
            all_reqs = adapter_class.get_all_requirements()

            for req in all_reqs:
                for field in required_fields:
                    assert field in req, f"Missing field '{field}' in {adapter_class.__name__}"

    def test_applies_to_is_list(self):
        """Test that applies_to is always a list."""
        for adapter_class in [SanFranciscoAdapter, NewYorkCityAdapter]:
            all_reqs = adapter_class.get_all_requirements()

            for req in all_reqs:
                assert isinstance(req["applies_to"], list)
                assert len(req["applies_to"]) > 0

    def test_required_documents_is_list(self):
        """Test that required_documents is always a list."""
        for adapter_class in [SanFranciscoAdapter, NewYorkCityAdapter]:
            all_reqs = adapter_class.get_all_requirements()

            for req in all_reqs:
                assert isinstance(req["required_documents"], list)
