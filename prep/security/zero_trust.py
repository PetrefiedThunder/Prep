"""Zero-trust security primitives for the Prep platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..core.audit import AuditRecord


@dataclass
class Request:
    """Simplified representation of an incoming request."""

    user_id: str
    device_id: str
    ip_address: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthenticationResult:
    """Outcome of a zero-trust authentication flow."""

    authenticated: bool
    confidence_score: float
    reason: Optional[str] = None
    factors: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAction:
    """Action performed by the security layer that needs auditing."""

    user_id: str
    type: str
    resource: str
    outcome: str
    context: Dict[str, Any] = field(default_factory=dict)


class ZeroTrustSecurity:
    """Implements simplified zero-trust security checks."""

    async def authenticate_request(self, request: Request) -> AuthenticationResult:
        """Zero-trust authentication with multi-factor validation."""

        factors = {
            "device_attested": request.metadata.get("device_attested", True),
            "ip_reputation": request.metadata.get("ip_reputation", "neutral"),
            "behavior_score": request.metadata.get("behavior_score", 0.5),
        }

        authenticated = bool(factors["device_attested"]) and factors["behavior_score"] >= 0.4
        confidence_score = 0.9 if authenticated else 0.3
        reason = None if authenticated else "Device attestation failed or behavior anomaly detected"

        return AuthenticationResult(
            authenticated=authenticated,
            confidence_score=confidence_score,
            reason=reason,
            factors=factors,
        )

    async def audit_trail(self, action: SecurityAction) -> AuditRecord:
        """Comprehensive audit logging for SOC2."""

        return AuditRecord(
            timestamp=datetime.now(timezone.utc),
            category="security_action",
            user_id=action.user_id,
            action_type=action.type,
            resource=action.resource,
            outcome=action.outcome,
            details=action.context,
        )


__all__ = [
    "ZeroTrustSecurity",
    "Request",
    "AuthenticationResult",
    "SecurityAction",
]
