"""Write audit log rows for administrative actions."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from mailgate.models import AuditLog


def write_audit(
    session: Session,
    action: str,
    *,
    user_id: int | None = None,
    target: str | None = None,
    request: Request | None = None,
    details: str | None = None,
) -> None:
    ip = None
    ua = None
    if request is not None:
        ip = request.client.host if request.client else None
        ua = (request.headers.get("user-agent") or "")[:255]
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            target=target,
            ip=ip,
            user_agent=ua,
            details=details,
        )
    )
