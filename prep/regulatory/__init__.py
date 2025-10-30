"""Regulatory compliance utilities for the Prep platform."""

from __future__ import annotations

from importlib import import_module
from typing import Iterable

__all__: list[str] = []


def _safe_import(module: str, names: Iterable[str]) -> None:
    try:
        mod = import_module(module, package=__name__)
    except Exception:  # pragma: no cover - defensive against legacy modules
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
    ["InsuranceRequirement", "RegDoc", "Regulation", "RegulationSource"],
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
]
