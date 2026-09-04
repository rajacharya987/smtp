"""Mail queue from Postfix, mirrored into the database when possible."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from mailgate.api.deps import admin_user, db_session
from mailgate.audit import write_audit
from mailgate.models import User
from mailgate.services.postfix import inspect_queue, queue_action, queue_json

router = APIRouter(prefix="/api/queue", tags=["queue"])


def _normalize(item: dict) -> dict:
    recipients = item.get("recipients") or []
    first = recipients[0] if recipients else {}
    return {
        "queue_id": item.get("queue_id"),
        "sender": item.get("sender"),
        "recipient": first.get("address"),
        "status": (first.get("delay_reason") and "deferred") or item.get("queue_name") or "unknown",
        "created": item.get("arrival_time"),
        "attempts": None,
        "size": item.get("message_size"),
        "reason": first.get("delay_reason"),
        "recipients": recipients,
    }


@router.get("")
def list_queue(_: User = Depends(admin_user)):
    return [_normalize(item) for item in queue_json()]


@router.post("/{queue_id}/retry")
def retry(queue_id: str, request=None, session: Session = Depends(db_session), user: User = Depends(admin_user)):
    ok, message = queue_action(queue_id, "retry")
    if not ok:
        raise HTTPException(status_code=400, detail=message or "Retry failed")
    write_audit(session, "queue.retry", user_id=user.id, target=queue_id, request=request)
    return {"ok": True, "message": message}


@router.delete("/{queue_id}")
def delete(queue_id: str, request=None, session: Session = Depends(db_session), user: User = Depends(admin_user)):
    ok, message = queue_action(queue_id, "delete")
    if not ok:
        raise HTTPException(status_code=400, detail=message or "Delete failed")
    write_audit(session, "queue.delete", user_id=user.id, target=queue_id, request=request)
    return {"ok": True, "message": message}


@router.get("/{queue_id}")
def inspect(queue_id: str, _: User = Depends(admin_user)):
    ok, text = inspect_queue(queue_id)
    if not ok:
        raise HTTPException(status_code=400, detail=text or "Inspect failed")
    return {"queue_id": queue_id, "headers": text}
