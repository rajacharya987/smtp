"""System status, health, services."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mailgate.api.deps import admin_user, db_session
from mailgate.audit import write_audit
from mailgate.models import Alias, Domain, MailEvent, User
from mailgate.services.health import collect_status, doctor
from mailgate.services.postfix import queue_json
from mailgate.services.systemd import control, list_units

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health")
def health():
    """Unauthenticated liveness probe for Caddy / systemd. No internals leaked."""
    return {"status": "ok"}


@router.get("/status")
def status_endpoint(session: Session = Depends(db_session), _: User = Depends(admin_user)):
    status = collect_status()
    domains = session.scalar(select(func.count()).select_from(Domain)) or 0
    forwarders = session.scalar(select(func.count()).select_from(Alias)) or 0
    failed = session.scalar(
        select(func.count()).select_from(MailEvent).where(MailEvent.event_type == "failed")
    ) or 0
    queued = len(queue_json())
    status.update(
        {
            "domains": domains,
            "forwarders": forwarders,
            "queued_mail": queued,
            "failed_mail": failed,
        }
    )
    return status


@router.get("/doctor")
def doctor_endpoint(_: User = Depends(admin_user)):
    return doctor()


@router.get("/services")
def services(_: User = Depends(admin_user)):
    return list_units()


@router.post("/services/{name}/{action}")
def service_action(
    name: str,
    action: str,
    request: Request,
    session: Session = Depends(db_session),
    user: User = Depends(admin_user),
):
    try:
        result = control(name, action, allow_optional=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    write_audit(session, f"service.{action}", user_id=user.id, target=name, request=request)
    return result
