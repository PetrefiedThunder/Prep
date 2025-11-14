"""External API integrations for regulatory intelligence."""

from .esignature import DocuSignAPIError, DocuSignClient, EnvelopeSummary
from .health_departments import (
    BaseAPIClient,
    CaliforniaHealthDepartmentAPI,
    InspectionRecord,
    NewYorkHealthDepartmentAPI,
    RegulatoryAPIError,
)
from .insurance import (
    AllStateAPI,
    InsuranceAPIError,
    InsuranceVerificationAPI,
    LibertyMutualAPI,
    PolicyVerificationResult,
    StateFarmAPI,
)
from .zoning import (
    ChicagoZoningAPI,
    MunicipalZoningAPI,
    NYCPlanningAPI,
    SFPlanningAPI,
    ZoningAPIError,
    ZoningResult,
)

__all__ = [
    "BaseAPIClient",
    "RegulatoryAPIError",
    "InspectionRecord",
    "DocuSignClient",
    "DocuSignAPIError",
    "EnvelopeSummary",
    "CaliforniaHealthDepartmentAPI",
    "NewYorkHealthDepartmentAPI",
    "InsuranceVerificationAPI",
    "InsuranceAPIError",
    "PolicyVerificationResult",
    "StateFarmAPI",
    "AllStateAPI",
    "LibertyMutualAPI",
    "MunicipalZoningAPI",
    "SFPlanningAPI",
    "NYCPlanningAPI",
    "ChicagoZoningAPI",
    "ZoningAPIError",
    "ZoningResult",
]
