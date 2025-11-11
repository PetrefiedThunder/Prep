"""HTTP middleware that records high-value Prep API requests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TrackedPrefixes = ("/compliance/evaluate", "/admin", "/bookings")


def _parse_user_id(raw: str | None) -> UUID | None:
    if not raw:
        return None
    try:
        return UUID(raw)
    except (TypeError, ValueError):
        return None


async def audit_logger(request: Request, call_next: Callable):
    """Record audit events for sensitive routes when a session factory is available."""

    response = await call_next(request)

    try:
        path = request.url.path
        if not any(path.startswith(prefix) for prefix in TrackedPrefixes):
            return response

        session_factory = getattr(request.app.state, "db", None)
        if session_factory is None:
            return response

        user_header = request.headers.get("X-User-Id")
        user_id = _parse_user_id(user_header)
        metadata = {
            "path": path,
            "status_code": response.status_code,
            "method": request.method,
        }
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        async with session_factory() as session:  # type: ignore[misc]
            await _insert_audit_record(
                session=session,
                event_type=f"HTTP_{request.method.upper()}",
                entity_type="route",
                entity_id=uuid4(),
                user_id=user_id,
                metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await session.commit()
    except Exception as exc:
        # The audit trail must never impact the customer request, but we should log failures
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            "Audit logging failed - this should be investigated",
            exc_info=exc,
            extra={
                "path": path if "path" in locals() else "unknown",
                "user_id": str(user_id) if "user_id" in locals() and user_id else None,
                "status_code": response.status_code,
                "audit_failure": True,
            },
        )
        # In production, also emit metric for monitoring
        # metrics.increment("audit.logging.failure")

    return response


async def _insert_audit_record(
    *,
    session: AsyncSession,
    event_type: str,
    entity_type: str,
    entity_id: UUID,
    user_id: UUID | None,
    metadata: dict[str, object],
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    query = text(
        """
        INSERT INTO audit_logs (
            event_type,
            entity_type,
            entity_id,
            user_id,
            changes,
            metadata,
            ip_address,
            user_agent,
            created_at
        )
        VALUES (
            :event_type,
            :entity_type,
            :entity_id,
            :user_id,
            :changes,
            :metadata,
            :ip_address,
            :user_agent,
            :created_at
        )
        """
    )
    await session.execute(
        query,
        {
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "user_id": str(user_id) if user_id else None,
            "changes": None,
            "metadata": metadata,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.now(timezone.utc),
        },
    )
