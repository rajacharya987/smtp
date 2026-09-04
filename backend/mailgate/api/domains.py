"""Domain management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from mailgate.api.deps import admin_user, db_session
from mailgate.audit import write_audit
from mailgate.config import load_config
from mailgate.models import Alias, Domain, User
from mailgate.schemas import DomainCreate, DomainOut, DomainUpdate
from mailgate.services.dns import verify_domain
from mailgate.services.postfix import apply_and_reload
from mailgate.validate import ValidationError, normalize_domain, normalize_email, normalize_hostname

router = APIRouter(prefix="/api/domains", tags=["domains"])


def _to_out(domain: Domain) -> DomainOut:
    return DomainOut(
        id=domain.id,
        name=domain.name,
        hostname=domain.hostname,
        enabled=domain.enabled,
        verified=domain.verified,
        catch_all_enabled=domain.catch_all_enabled,
        catch_all_destination=domain.catch_all_destination,
        dkim_selector=domain.dkim_selector,
        dmarc_policy=domain.dmarc_policy,
        created_at=domain.created_at,
        alias_count=len(domain.aliases) if domain.aliases is not None else 0,
    )


@router.get("")
def list_domains(session: Session = Depends(db_session), _: User = Depends(admin_user)):
    rows = session.scalars(select(Domain).options(selectinload(Domain.aliases)).order_by(Domain.name)).all()
    return [_to_out(d) for d in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_domain(
    payload: DomainCreate,
    request: Request,
    session: Session = Depends(db_session),
    user: User = Depends(admin_user),
):
    try:
        name = normalize_domain(payload.name)
        hostname = normalize_hostname(payload.hostname) if payload.hostname else load_config().server.hostname
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    exists = session.scalar(select(Domain).where(func.lower(Domain.name) == name))
    if exists:
        raise HTTPException(status_code=409, detail="Domain already exists")
    domain = Domain(name=name, hostname=hostname, enabled=False, verified=False)
    session.add(domain)
    session.flush()
    write_audit(session, "domain.create", user_id=user.id, target=name, request=request)
    session.refresh(domain)
    domain.aliases = []
    return _to_out(domain)


@router.get("/{domain_id}")
def get_domain(domain_id: int, session: Session = Depends(db_session), _: User = Depends(admin_user)):
    domain = session.scalar(select(Domain).options(selectinload(Domain.aliases)).where(Domain.id == domain_id))
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    return _to_out(domain)


@router.patch("/{domain_id}")
def update_domain(
    domain_id: int,
    payload: DomainUpdate,
    request: Request,
    session: Session = Depends(db_session),
    user: User = Depends(admin_user),
):
    domain = session.get(Domain, domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    try:
        if payload.hostname is not None:
            domain.hostname = normalize_hostname(payload.hostname)
        if payload.catch_all_enabled is not None:
            domain.catch_all_enabled = payload.catch_all_enabled
        if payload.catch_all_destination is not None:
            domain.catch_all_destination = (
                normalize_email(payload.catch_all_destination) if payload.catch_all_destination else None
            )
        if payload.dmarc_policy is not None:
            if payload.dmarc_policy not in {"none", "quarantine", "reject"}:
                raise ValidationError("DMARC policy must be none, quarantine, or reject")
            domain.dmarc_policy = payload.dmarc_policy
        if payload.dkim_selector is not None:
            selector = payload.dkim_selector.strip().lower()
            if not selector.isalnum():
                raise ValidationError("DKIM selector must be alphanumeric")
            domain.dkim_selector = selector
        if payload.enabled is not None:
            if payload.enabled and not domain.verified:
                raise HTTPException(
                    status_code=400,
                    detail="Domain cannot be enabled until A and MX records verify",
                )
            domain.enabled = payload.enabled
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if domain.catch_all_enabled and not domain.catch_all_destination:
        raise HTTPException(status_code=400, detail="Catch-all requires a destination address")
    write_audit(session, "domain.update", user_id=user.id, target=domain.name, request=request)
    session.flush()
    apply_and_reload(session)
    session.refresh(domain)
    domain.aliases = session.scalars(select(Alias).where(Alias.domain_id == domain.id)).all()
    return _to_out(domain)


@router.delete("/{domain_id}")
def delete_domain(
    domain_id: int,
    request: Request,
    session: Session = Depends(db_session),
    user: User = Depends(admin_user),
):
    domain = session.get(Domain, domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    name = domain.name
    session.delete(domain)
    session.flush()
    apply_and_reload(session)
    write_audit(session, "domain.delete", user_id=user.id, target=name, request=request)
    return {"ok": True}


@router.post("/{domain_id}/verify")
def verify(domain_id: int, session: Session = Depends(db_session), user: User = Depends(admin_user), request: Request = None):
    domain = session.get(Domain, domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    report = verify_domain(domain)
    domain.verified = report.verified
    if not report.verified:
        domain.enabled = False
    write_audit(session, "domain.verify", user_id=user.id, target=domain.name, request=request)
    session.flush()
    apply_and_reload(session)
    return report.to_dict()
