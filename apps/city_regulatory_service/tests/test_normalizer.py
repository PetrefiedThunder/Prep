"""Tests for requirement normalizer."""

from apps.city_regulatory_service.src.normalizers import RequirementNormalizer


class TestRequirementNormalizer:
    """Test suite for RequirementNormalizer."""

    def test_normalize_requirement_type_business_license(self):
        """Test normalization of business license types."""
        assert (
            RequirementNormalizer.normalize_requirement_type("Business Registration Certificate")
            == "business_license"
        )

        assert (
            RequirementNormalizer.normalize_requirement_type("General Business License")
            == "business_license"
        )

    def test_normalize_requirement_type_restaurant(self):
        """Test normalization of restaurant license types."""
        assert (
            RequirementNormalizer.normalize_requirement_type("Food Service Permit")
            == "restaurant_license"
        )

        assert (
            RequirementNormalizer.normalize_requirement_type("Common Victualler License")
            == "restaurant_license"
        )

    def test_normalize_requirement_type_food_safety(self):
        """Test normalization of food safety training types."""
        assert (
            RequirementNormalizer.normalize_requirement_type("Food Manager Certification")
            == "food_safety_training"
        )

    def test_normalize_requirement_type_fallback(self):
        """Test fallback for unknown requirement types."""
        assert RequirementNormalizer.normalize_requirement_type("Unknown Permit Type") == "other"

    def test_normalize_renewal_frequency_annual(self):
        """Test normalization of annual renewal frequency."""
        assert RequirementNormalizer.normalize_renewal_frequency("annual") == "annual"
        assert RequirementNormalizer.normalize_renewal_frequency("yearly") == "annual"
        assert RequirementNormalizer.normalize_renewal_frequency("12 months") == "annual"

    def test_normalize_renewal_frequency_biannual(self):
        """Test normalization of biannual renewal frequency."""
        assert RequirementNormalizer.normalize_renewal_frequency("biannual") == "biannual"
        assert RequirementNormalizer.normalize_renewal_frequency("6 months") == "biannual"

    def test_normalize_renewal_frequency_unknown(self):
        """Test fallback for unknown renewal frequency."""
        assert RequirementNormalizer.normalize_renewal_frequency("") == "unknown"
        assert RequirementNormalizer.normalize_renewal_frequency("whenever") == "unknown"

    def test_normalize_submission_channel(self):
        """Test normalization of submission channels."""
        assert RequirementNormalizer.normalize_submission_channel("online portal") == "online"
        assert RequirementNormalizer.normalize_submission_channel("by mail") == "mail"
        assert RequirementNormalizer.normalize_submission_channel("in person") == "in_person"

    def test_normalize_business_types(self):
        """Test normalization of business types."""
        result = RequirementNormalizer.normalize_business_types(
            ["Restaurant", "Food Truck", "Caterer"]
        )
        assert "restaurant" in result
        assert "food truck" in result
        assert "caterer" in result

    def test_normalize_business_types_fallback(self):
        """Test fallback for unmapped business types."""
        result = RequirementNormalizer.normalize_business_types([])
        assert result == ["all"]

    def test_extract_fee_amount_with_amount(self):
        """Test fee extraction with numeric amount."""
        amount, schedule = RequirementNormalizer.extract_fee_amount(
            {"amount": 686.00, "frequency": "annual"}
        )
        assert amount == 686.00
        assert schedule == "annual"

    def test_extract_fee_amount_variable(self):
        """Test fee extraction with variable amount."""
        amount, schedule = RequirementNormalizer.extract_fee_amount(
            {"amount": None, "schedule": "variable by revenue"}
        )
        assert amount is None
        assert schedule == "variable by revenue"

    def test_extract_fee_amount_empty(self):
        """Test fee extraction with empty data."""
        amount, schedule = RequirementNormalizer.extract_fee_amount({})
        assert amount is None
        assert schedule == "unknown"

    def test_normalize_complete_requirement(self):
        """Test normalization of complete requirement."""
        raw_data = {
            "requirement_id": "sf_dph_food_permit_001",
            "jurisdiction": "San Francisco",
            "requirement_label": "Retail Food Establishment Permit",
            "agency": "San Francisco Department of Public Health",
            "agency_type": "health",
            "applies_to": ["restaurant", "shared kitchen"],
            "required_documents": ["Floor plan", "Menu"],
            "renewal_cycle": "annual",
            "fee_structure": {"amount": 686.00, "frequency": "annual"},
            "submission_channel": "online",
            "application_url": "https://example.com",
            "inspection_required": True,
            "official_url": "https://sfdph.org",
        }

        normalized = RequirementNormalizer.normalize(raw_data)

        assert normalized.requirement_id == "sf_dph_food_permit_001"
        assert normalized.jurisdiction == "San Francisco"
        assert normalized.normalized_type == "restaurant_license"
        assert normalized.renewal_frequency == "annual"
        assert normalized.submission_channel == "online"
        assert normalized.fee_amount == 686.00
        assert normalized.inspection_required is True
        assert "restaurant" in normalized.applies_to
        assert len(normalized.required_documents) == 2
