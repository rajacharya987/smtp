"""Aliases and forwarding destinations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mailgate.api.deps import admin_user, db_session
from mailgate.audit import write_audit
from mailgate.models import Alias, Destination, Domain, User
from mailgate.schemas import AliasCreate, AliasOut, AliasUpdate, DestinationOut, ForwarderCreate
from mailgate.services.postfix import apply_and_reload
from mailgate.validate import ValidationError, normalize_domain, normalize_email, normalize_local_part

router = APIRouter(tags=["forwarders"])


def _alias_out(alias: Alias) -> AliasOut:
    return AliasOut(
        id=alias.id,
        domain_id=alias.domain_id,
        domain_name=alias.domain.name,
        local_part=alias.local_part,
        address=f"{alias.local_part}@{alias.domain.name}",
        enabled=alias.enabled,
        destinations=[DestinationOut.model_validate(d) for d in alias.destinations],
        created_at=alias.created_at,
    )


@router.get("/api/aliases")
@router.get("/api/forwarders")
def list_forwarders(session: Session = Depends(db_session), _: User = Depends(admin_user)):
    rows = session.scalars(
        select(Alias).options(selectinload(Alias.domain), selectinload(Alias.destinations)).order_by(Alias.id)
    ).all()
    return [_alias_out(a) for a in rows]


def _create_alias(
    session: Session,
    domain: Domain,
    local_part: str,
    destinations: list[str],
    enabled: bool,
) -> Alias:
    exists = session.scalar(
        select(Alias).where(Alias.domain_id == domain.id, Alias.local_part == local_part)
    )
    if exists:
        raise HTTPException(status_code=409, detail="Alias already exists on this domain")
    dests = []
    seen = set()
    for raw in destinations:
        email = normalize_email(raw)
        if email in seen:
            continue
        seen.add(email)
        dests.append(email)
    if not dests:
        raise HTTPException(status_code=400, detail="At least one destination is required")
    alias = Alias(domain_id=domain.id, local_part=local_part, enabled=enabled)
    session.add(alias)
    session.flush()
    for email in dests:
        session.add(Destination(alias_id=alias.id, email=email, enabled=True))
    session.flush()
    alias = session.scalar(
        select(Alias).options(selectinload(Alias.domain), selectinload(Alias.destinations)).where(Alias.id == alias.id)
    )
    assert alias is not None
    return alias


@router.post("/api/aliases", status_code=status.HTTP_201_CREATED)
def create_alias(
    payload: AliasCreate,
    request: Request,
    session: Session = Depends(db_session),
    user: User = Depends(admin_user),
):
    domain = session.get(Domain, payload.domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    try:
        local = normalize_local_part(payload.local_part)
        alias = _create_alias(session, domain, local, payload.destinations, payload.enabled)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    apply_and_reload(session)
    write_audit(
        session,
        "alias.create",
        user_id=user.id,
        target=f"{local}@{domain.name}",
        request=request,
    )
    return _alias_out(alias)


@router.post("/api/forwarders", status_code=status.HTTP_201_CREATED)
def create_forwarder(
    payload: ForwarderCreate,
    request: Request,
    session: Session = Depends(db_session),
    user: User = Depends(admin_user),
):
    try:
        domain_name = normalize_domain(payload.domain)
        local = normalize_local_part(payload.local_part)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    domain = session.scalar(select(Domain).where(Domain.name == domain_name))
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    try:
        alias = _create_alias(session, domain, local, payload.destinations, payload.enabled)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    apply_and_reload(session)
    write_audit(
        session,
        "forwarder.create",
        user_id=user.id,
        target=f"{local}@{domain_name}",
        request=request,
    )
    return _alias_out(alias)


@router.patch("/api/aliases/{alias_id}")
@router.patch("/api/forwarders/{alias_id}")
def update_alias(
    alias_id: int,
    payload: AliasUpdate,
    request: Request,
    session: Session = Depends(db_session),
    user: User = Depends(admin_user),
):
    alias = session.scalar(
        select(Alias).options(selectinload(Alias.domain), selectinload(Alias.destinations)).where(Alias.id == alias_id)
    )
    if alias is None:
        raise HTTPException(status_code=404, detail="Alias not found")
    if payload.enabled is not None:
        alias.enabled = payload.enabled
    if payload.destinations is not None:
        try:
            emails = []
            seen = set()
            for raw in payload.destinations:
                email = normalize_email(raw)
                if email not in seen:
                    seen.add(email)
                    emails.append(email)
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not emails:
            raise HTTPException(status_code=400, detail="At least one destination is required")
        alias.destinations.clear()
        session.flush()
        for email in emails:
            session.add(Destination(alias_id=alias.id, email=email, enabled=True))
    session.flush()
    apply_and_reload(session)
    write_audit(session, "alias.update", user_id=user.id, target=str(alias_id), request=request)
    alias = session.scalar(
        select(Alias).options(selectinload(Alias.domain), selectinload(Alias.destinations)).where(Alias.id == alias_id)
    )
    return _alias_out(alias)


@router.delete("/api/aliases/{alias_id}")
@router.delete("/api/forwarders/{alias_id}")
def delete_alias(
    alias_id: int,
    request: Request,
    session: Session = Depends(db_session),
    user: User = Depends(admin_user),
):
    alias = session.get(Alias, alias_id)
    if alias is None:
        raise HTTPException(status_code=404, detail="Alias not found")
    session.delete(alias)
    session.flush()
    apply_and_reload(session)
    write_audit(session, "alias.delete", user_id=user.id, target=str(alias_id), request=request)
    return {"ok": True}
