"""Regulatory compliance utilities for the Prep platform."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from libs.safe_import import safe_import

__all__: list[str] = []
logger = logging.getLogger(__name__)


def _safe_import(module: str, names: Iterable[str]) -> None:
    # Construct full module path (relative to this package)
    full_module = f"prep.regulatory{module}"
    mod = safe_import(full_module, optional=True)
    if mod is None:
        logger.info("Optional regulatory module %s not available, skipping exports", full_module)
        return

    exported: list[str] = []
    for name in names:
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            exported.append(name)

    __all__.extend(exported)


_safe_import(
    ".analyzer",
    ["ComplianceAnalysis", "ComplianceLevel", "RegulatoryAnalyzer"],
)
_safe_import(
    ".analytics.impact",
    ["ImpactDataSource", "RegulatoryImpactAssessor"],
)
_safe_import(
    ".analytics.trends",
    ["RegulatoryTrendAnalyzer", "TrendDataSource"],
)
_safe_import(
    ".apis.health_departments",
    [
        "CaliforniaHealthDepartmentAPI",
        "InspectionRecord",
        "NewYorkHealthDepartmentAPI",
        "RegulatoryAPIError",
    ],
)
_safe_import(
    ".apis.insurance",
    [
        "AllStateAPI",
        "InsuranceAPIError",
        "InsuranceVerificationAPI",
        "LibertyMutualAPI",
        "PolicyVerificationResult",
        "StateFarmAPI",
    ],
)
_safe_import(
    ".apis.zoning",
    [
        "ChicagoZoningAPI",
        "MunicipalZoningAPI",
        "NYCPlanningAPI",
        "SFPlanningAPI",
        "ZoningAPIError",
        "ZoningResult",
    ],
)
_safe_import(
    ".models",
    [
        "InsuranceRequirement",
        "RegDoc",
        "RegRequirement",
        "FeeSchedule",
        "Regulation",
        "RegulationSource",
    ],
)
_safe_import(
    ".monitoring.changes",
    ["Change", "RegulatoryChangeDetector"],
)
_safe_import(
    ".nlp.analyzer",
    ["RegulationNLP", "Requirement"],
)
from .apis.esignature import DocuSignAPIError, DocuSignClient, EnvelopeSummary
from .apis.insurance import (
    AllStateAPI,
    InsuranceAPIError,
    InsuranceVerificationAPI,
    LibertyMutualAPI,
    PolicyVerificationResult,
    StateFarmAPI,
)

_safe_import(
    ".prediction.engine",
    ["CompliancePredictor", "PredictionResult"],
)
_safe_import(".scheduler", ["RegulatoryScheduler"])
_safe_import(".scraper", ["RegulatoryScraper"])
_safe_import(".loader", ["load_regdoc"])
_safe_import(
    ".writer",
    ["write_fee_schedule", "write_reg_requirements"],
)

__all__ = [
    "ComplianceAnalysis",
    "ComplianceLevel",
    "RegulatoryAnalyzer",
    "RegulatoryScraper",
    "DocuSignClient",
    "DocuSignAPIError",
    "EnvelopeSummary",
    "RegulatoryScheduler",
    "Regulation",
    "RegulationSource",
    "InsuranceRequirement",
    "CaliforniaHealthDepartmentAPI",
    "NewYorkHealthDepartmentAPI",
    "InspectionRecord",
    "RegulatoryAPIError",
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
    "RegulatoryTrendAnalyzer",
    "TrendDataSource",
    "RegulatoryImpactAssessor",
    "ImpactDataSource",
    "RegulatoryChangeDetector",
    "Change",
    "RegulationNLP",
    "Requirement",
    "CompliancePredictor",
    "PredictionResult",
    "RegRequirement",
    "FeeSchedule",
    "write_fee_schedule",
    "write_reg_requirements",
]
