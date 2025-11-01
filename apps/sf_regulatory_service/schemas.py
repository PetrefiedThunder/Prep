"""Pydantic schemas for the San Francisco regulatory service."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class RemediationAction(BaseModel):
    field: str
    action: str


class SFHostProfilePayload(BaseModel):
    host_kitchen_id: str = Field(..., alias="hostKitchenId")
    business_registration_certificate: str = Field(..., alias="businessRegistrationCertificate")
    business_registration_expires: date = Field(..., alias="businessRegistrationExpires")
    health_permit_number: str = Field(..., alias="healthPermitNumber")
    health_permit_expires: date = Field(..., alias="healthPermitExpires")
    facility_type: str = Field(..., alias="facilityType")
    zoning_use_district: str = Field(..., alias="zoningUseDistrict")
    fire_suppression_certificate: Optional[str] = Field(None, alias="fireSuppressionCertificate")
    fire_last_inspection: Optional[date] = Field(None, alias="fireLastInspection")
    grease_trap_certificate: Optional[str] = Field(None, alias="greaseTrapCertificate")
    grease_last_service: Optional[date] = Field(None, alias="greaseLastService")
    tax_classification: str = Field(..., alias="taxClassification")
    lease_gross_receipts_ytd: Optional[float] = Field(0.0, alias="leaseGrossReceiptsYtd")

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class ComplianceResponse(BaseModel):
    status: str
    issues: List[str]
    remediation: List[RemediationAction]


class HostStatusResponse(BaseModel):
    profile: SFHostProfilePayload
    status: str
    warnings: List[str]
    issues: List[str]


class ZoningCheckResponse(BaseModel):
    kitchen_use_allowed: bool = Field(..., alias="kitchenUseAllowed")
    zoning_use_district: str = Field(..., alias="zoningUseDistrict")
    manual_review_required: bool = Field(..., alias="manualReviewRequired")
    message: str

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class HealthPermitValidationRequest(BaseModel):
    permit_number: str = Field(..., alias="permitNumber")
    facility_type: str = Field(..., alias="facilityType")
    address: str

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class HealthPermitValidationResponse(BaseModel):
    status: str
    expiry_date: Optional[date] = Field(None, alias="expiryDate")
    verification_method: str = Field(..., alias="verificationMethod")

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class FireVerificationRequest(BaseModel):
    host_kitchen_id: str = Field(..., alias="hostKitchenId")
    certificate: str
    last_inspection_date: date = Field(..., alias="lastInspectionDate")
    system_type: str = Field(..., alias="systemType")

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class FireVerificationResponse(BaseModel):
    status: str
    message: str


class WasteVerificationRequest(BaseModel):
    host_kitchen_id: str = Field(..., alias="hostKitchenId")
    certificate: str
    last_service_date: date = Field(..., alias="lastServiceDate")

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class WasteVerificationResponse(BaseModel):
    status: str


class ComplianceCheckRequest(BaseModel):
    host_kitchen_id: str = Field(..., alias="hostKitchenId")
    booking_id: Optional[str] = Field(None, alias="bookingId")

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class ComplianceCheckResponse(ComplianceResponse):
    booking_id: Optional[str] = Field(None, alias="bookingId")

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True
