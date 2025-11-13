"""Prep ETL tooling package."""

from __future__ import annotations

from typing import Any

__all__ = [
    "load_regdocs",
    "process_urls",
    "run_crawler",
    "extract_reg_sections",
    "pdf_to_text",
]


def __getattr__(name: str) -> Any:  # pragma: no cover - thin convenience wrapper
    if name == "load_regdocs":
        from .loader import load_regdocs as attr

        return attr
    if name == "process_urls":
        from .crawler import process_urls as attr

        return attr
    if name == "run_crawler":
        from .crawler import main as attr

        return attr
    if name == "extract_reg_sections":
        from .parser import extract_reg_sections as attr

        return attr
    if name == "pdf_to_text":
        from .parser import pdf_to_text as attr

        return attr
    raise AttributeError(name)
