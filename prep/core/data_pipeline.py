"""Unified data ingestion and transformation utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from .orchestration import ComplianceDomain


class DataSource(Enum):
    """Supported input data sources for compliance workloads."""

    API = "api"
    DATABASE = "database"
    FILE_UPLOAD = "file_upload"
    WEB_SCRAPING = "web_scraping"


@dataclass
class DataStream:
    """Represents standardized ingested data."""

    source: DataSource
    payload: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StandardizedData:
    """Transformed data ready for compliance engines."""

    domain: ComplianceDomain
    content: Any
    quality_score: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class DataIngester(Protocol):
    async def ingest(self, config: dict[str, Any]) -> DataStream: ...


class DataTransformer(Protocol):
    async def transform(self, raw_data: Any) -> StandardizedData: ...


class APIDataIngester:
    async def ingest(self, config: dict[str, Any]) -> DataStream:
        payload = config.get("data")
        metadata = {"endpoint": config.get("endpoint"), "headers": config.get("headers", {})}
        return DataStream(source=DataSource.API, payload=payload, metadata=metadata)


class DatabaseIngester:
    async def ingest(self, config: dict[str, Any]) -> DataStream:
        query = config.get("query", "")
        payload = config.get("data")
        metadata = {"connection": config.get("connection"), "query": query}
        return DataStream(source=DataSource.DATABASE, payload=payload, metadata=metadata)


class FileIngester:
    async def ingest(self, config: dict[str, Any]) -> DataStream:
        payload = config.get("data")
        metadata = {"filename": config.get("filename"), "content_type": config.get("content_type")}
        return DataStream(source=DataSource.FILE_UPLOAD, payload=payload, metadata=metadata)


class WebScraperIngester:
    async def ingest(self, config: dict[str, Any]) -> DataStream:
        payload = config.get("data")
        metadata = {"url": config.get("url"), "selector": config.get("selector")}
        return DataStream(source=DataSource.WEB_SCRAPING, payload=payload, metadata=metadata)


class GDPRDataTransformer:
    async def transform(self, raw_data: Any) -> StandardizedData:
        content = {
            "data_subjects": raw_data.get("data_subjects", []),
            "consents": raw_data.get("consents", []),
        }
        return StandardizedData(
            domain=ComplianceDomain.GDPR_CCPA, content=content, quality_score=0.95
        )


class AMLDataTransformer:
    async def transform(self, raw_data: Any) -> StandardizedData:
        content = {
            "customers": raw_data.get("customers", []),
            "transactions": raw_data.get("transactions", []),
        }
        return StandardizedData(domain=ComplianceDomain.AML_KYC, content=content, quality_score=0.9)


class AccountingDataTransformer:
    async def transform(self, raw_data: Any) -> StandardizedData:
        content = {
            "ledger_entries": raw_data.get("ledger_entries", []),
            "financial_statements": raw_data.get("financial_statements", []),
        }
        return StandardizedData(
            domain=ComplianceDomain.GAAP_IFRS, content=content, quality_score=0.92
        )


class UnifiedDataPipeline:
    """Facade over ingestion and transformation utilities."""

    def __init__(self) -> None:
        self._ingesters = {
            DataSource.API: APIDataIngester(),
            DataSource.DATABASE: DatabaseIngester(),
            DataSource.FILE_UPLOAD: FileIngester(),
            DataSource.WEB_SCRAPING: WebScraperIngester(),
        }

        self._transformers = {
            ComplianceDomain.GDPR_CCPA: GDPRDataTransformer(),
            ComplianceDomain.AML_KYC: AMLDataTransformer(),
            ComplianceDomain.GAAP_IFRS: AccountingDataTransformer(),
        }

    async def ingest_data(self, source_type: DataSource, config: dict[str, Any]) -> DataStream:
        """Ingest data from the provided source using a unified interface."""

        try:
            ingester = self._ingesters[source_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported data source: {source_type}") from exc

        return await ingester.ingest(config)

    async def transform_for_compliance(
        self, raw_data: Any, target_domain: ComplianceDomain
    ) -> StandardizedData:
        """Transform raw data into the format expected by a compliance engine."""

        transformer = self._transformers.get(target_domain)
        if transformer is None:
            raise ValueError(f"No transformer registered for domain {target_domain}")

        return await transformer.transform(raw_data)


__all__ = [
    "UnifiedDataPipeline",
    "DataSource",
    "DataStream",
    "StandardizedData",
]
