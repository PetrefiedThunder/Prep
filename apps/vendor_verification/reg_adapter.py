"""Simple RegEngine adapter for vendor verification."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from apps.vendor_verification.models import (
    CheckEvidence,
    CheckResult,
    CheckStatus,
    Decision,
    DecisionOutcome,
    DocumentType,
    Location,
    Recommendation,
)

if TYPE_CHECKING:
    from apps.vendor_verification.orm_models import Vendor, VendorDocument


# Hardcoded ruleset for San Francisco shared kitchens (v1)
SF_RULESET_NAME = "sf_shared_kitchen_v1"
SF_REGULATION_VERSION = "sfph_2025-09-01"
ENGINE_VERSION = "prep-regengine-1.0.0"

# Required documents for SF shared kitchen
SF_REQUIRED_DOCS = {
    DocumentType.BUSINESS_LICENSE,
    DocumentType.FOOD_HANDLER_CARD,
    DocumentType.LIABILITY_INSURANCE,
}


def _is_document_expired(document: VendorDocument) -> bool:
    """Check if a document is expired."""
    if document.expires_on is None:
        return False

    # Handle both date and datetime objects
    if hasattr(document.expires_on, "date"):
        # It's a datetime
        expiry_date = document.expires_on.date()
    else:
        # It's already a date
        expiry_date = document.expires_on

    return expiry_date < datetime.now(UTC).date()


def _matches_jurisdiction(doc_jurisdiction: dict, target_jurisdiction: Location) -> bool:
    """Check if document jurisdiction matches target jurisdiction."""
    # For now, simple country match (can be enhanced)
    if doc_jurisdiction.get("country") != target_jurisdiction.country:
        return False

    # If state is specified in target, it must match
    return not (
        target_jurisdiction.state and doc_jurisdiction.get("state") != target_jurisdiction.state
    )


def run_verification(
    vendor: Vendor,
    documents: list[VendorDocument],
    jurisdiction: Location,
) -> tuple[Decision, Recommendation]:
    """
    Run verification for a vendor in a jurisdiction.

    For v1, implements simple San Francisco shared kitchen rules:
    - Requires business_license, food_handler_card, liability_insurance
    - All must be present and not expired
    - All must match the jurisdiction

    Args:
        vendor: The vendor being verified
        documents: List of vendor documents
        jurisdiction: The jurisdiction for verification

    Returns:
        Tuple of (Decision, Recommendation)
    """
    check_results: list[CheckResult] = []

    # Filter documents for the target jurisdiction
    jurisdiction_docs = [
        doc for doc in documents if _matches_jurisdiction(doc.jurisdiction, jurisdiction)
    ]

    # Check for required documents
    present_doc_types = {DocumentType(doc.type) for doc in jurisdiction_docs}

    for required_type in SF_REQUIRED_DOCS:
        doc_type_name = required_type.value.replace("_", " ").title()

        # Check if document type is present
        if required_type not in present_doc_types:
            check_results.append(
                CheckResult(
                    code=f"{required_type.value}_present",
                    status=CheckStatus.FAIL,
                    details=f"{doc_type_name} is required but not found",
                    regulation_version=SF_REGULATION_VERSION,
                    evidence=[],
                )
            )
            continue

        # Find the document(s) of this type
        type_docs = [doc for doc in jurisdiction_docs if DocumentType(doc.type) == required_type]

        # Check expiration
        expired_docs = [doc for doc in type_docs if _is_document_expired(doc)]
        valid_docs = [doc for doc in type_docs if not _is_document_expired(doc)]

        if not valid_docs:
            # All documents of this type are expired
            check_results.append(
                CheckResult(
                    code=f"{required_type.value}_valid",
                    status=CheckStatus.FAIL,
                    details=f"{doc_type_name} has expired and needs renewal",
                    regulation_version=SF_REGULATION_VERSION,
                    evidence=[
                        CheckEvidence(document_id=doc.id, note="Expired") for doc in expired_docs
                    ],
                )
            )
        else:
            # At least one valid document
            check_results.append(
                CheckResult(
                    code=f"{required_type.value}_valid",
                    status=CheckStatus.PASS,
                    details=f"{doc_type_name} is present and valid",
                    regulation_version=SF_REGULATION_VERSION,
                    evidence=[
                        CheckEvidence(document_id=doc.id, note="Valid") for doc in valid_docs
                    ],
                )
            )

    # Determine overall outcome
    failed_checks = [check for check in check_results if check.status == CheckStatus.FAIL]

    if failed_checks:
        overall = DecisionOutcome.FAIL
        score = max(0.0, 1.0 - (len(failed_checks) * 0.34))  # Each failure reduces score
        summary = f"Vendor verification failed: {len(failed_checks)} requirement(s) not met"
        operator_action = "Request vendor to submit missing or expired documents before proceeding"
    else:
        overall = DecisionOutcome.PASS
        score = 0.97  # High confidence pass
        summary = "Vendor has all required documents and is approved for operation"
        operator_action = "Proceed with onboarding"

    decision = Decision(
        overall=overall,
        score=score,
        check_results=check_results,
    )

    recommendation = Recommendation(
        summary=summary,
        operator_action=operator_action,
    )

    return decision, recommendation


def get_ruleset_metadata(jurisdiction: Location) -> tuple[str, str, str]:
    """
    Get ruleset metadata for a jurisdiction.

    For v1, only San Francisco is supported.

    Args:
        jurisdiction: The jurisdiction

    Returns:
        Tuple of (ruleset_name, regulation_version, engine_version)
    """
    # For v1, hardcoded to SF
    # In future, this would lookup based on jurisdiction
    return SF_RULESET_NAME, SF_REGULATION_VERSION, ENGINE_VERSION
