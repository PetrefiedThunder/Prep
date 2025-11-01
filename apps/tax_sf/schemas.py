"""Pydantic schemas for the San Francisco tax service."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TaxLine(BaseModel):
    jurisdiction: str
    rate: float
    basis: float
    amount: float
    advisory: Optional[str] = None


class TaxCalculateRequest(BaseModel):
    booking_id: str = Field(..., alias="bookingId")
    host_kitchen_id: str = Field(..., alias="hostKitchenId")
    city: str
    booking_amount: float = Field(..., alias="bookingAmount")

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class TaxCalculateResponse(BaseModel):
    lines: List[TaxLine]
    total_tax: float = Field(..., alias="totalTax")
    classification: Optional[str] = None
    grt_threshold: Optional[float] = Field(None, alias="grtThreshold")

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True


class TaxReportResponse(BaseModel):
    period_start: date = Field(..., alias="periodStart")
    period_end: date = Field(..., alias="periodEnd")
    total_tax_collected: float = Field(..., alias="totalTaxCollected")
    total_booking_amount: float = Field(..., alias="totalBookingAmount")
    file_status: str = Field(..., alias="fileStatus")
    generated_at: Optional[datetime] = Field(None, alias="generatedAt")
    csv: str

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True
