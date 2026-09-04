"""Mail event logs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from mailgate.api.deps import admin_user, db_session
from mailgate.models import MailEvent, User

router = APIRouter(prefix="/api/logs", tags=["logs"])

FILTERS = {
    "all": None,
    "accepted": "accepted",
    "rejected": "rejected",
    "forwarded": "forwarded",
    "delivered": "delivered",
    "deferred": "deferred",
    "failed": "failed",
    "spam": "spam",
}


@router.get("")
def list_logs(
    status_filter: str = Query("all", alias="status"),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(db_session),
    _: User = Depends(admin_user),
):
    stmt = select(MailEvent).order_by(MailEvent.timestamp.desc()).limit(limit)
    wanted = FILTERS.get(status_filter, None)
    if wanted:
        stmt = stmt.where(MailEvent.event_type == wanted)
    rows = session.scalars(stmt).all()
    return [
        {
            "id": row.id,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "event_type": row.event_type,
            "queue_id": row.queue_id,
            "message_id": row.message_id,
            "sender": row.sender,
            "recipient": row.recipient,
            "destination": row.destination,
            "size": row.size,
            "status": row.status,
            "response": row.response,
            "spam_score": row.spam_score,
        }
        for row in rows
    ]
