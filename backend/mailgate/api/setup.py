"""First-run setup. Disabled once an administrator exists."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mailgate.api.deps import db_session
from mailgate.audit import write_audit
from mailgate.config import dump_config, load_config, reload_config
from mailgate.models import Alias, Destination, Domain, User
from mailgate.ratelimit import enforce
from mailgate.schemas import SetupRequest
from mailgate.security import (
    COOKIE_NAME,
    CSRF_COOKIE,
    cookie_kwargs,
    create_session_token,
    csrf_cookie_kwargs,
    hash_password,
    new_csrf_token,
    validate_password_strength,
)
from mailgate.services.health import collect_status, os_info, package_presence
from mailgate.services.network import detect_network
from mailgate.validate import ValidationError, normalize_domain, normalize_email, normalize_hostname, normalize_local_part

router = APIRouter(prefix="/api/setup", tags=["setup"])


def _has_admin(session: Session) -> bool:
    return (session.scalar(select(func.count()).select_from(User)) or 0) > 0


@router.get("/status")
def setup_status(session: Session = Depends(db_session)):
    net = detect_network()
    return {
        "needs_setup": not _has_admin(session),
        "os": os_info(),
        "packages": package_presence(),
        "network": net.to_dict(),
        "status": collect_status(),
    }


@router.post("")
def run_setup(
    payload: SetupRequest,
    request: Request,
    response: Response,
    session: Session = Depends(db_session),
):
    enforce(request, name="setup", limit=5, window_seconds=300)
    if _has_admin(session):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Setup already completed")
    errors = validate_password_strength(payload.admin_password)
    if errors:
        raise HTTPException(status_code=400, detail=errors)
    try:
        hostname = normalize_hostname(payload.hostname)
        domain_name = normalize_domain(payload.domain)
        username = payload.admin_username.strip()
        if not username.replace("_", "").replace("-", "").isalnum():
            raise ValidationError("Username may contain letters, digits, _ and - only")
        local = None
        dest = None
        if payload.first_local_part or payload.first_destination:
            if not (payload.first_local_part and payload.first_destination):
                raise ValidationError("Both local part and destination are required to create the first forwarder")
            local = normalize_local_part(payload.first_local_part)
            dest = normalize_email(payload.first_destination)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cfg = load_config()
    cfg.server.hostname = hostname
    dump_config(cfg)
    reload_config()

    user = User(username=username, password_hash=hash_password(payload.admin_password), is_admin=True)
    session.add(user)
    domain = Domain(name=domain_name, hostname=hostname, enabled=False, verified=False)
    session.add(domain)
    session.flush()
    if local and dest:
        alias = Alias(domain_id=domain.id, local_part=local, enabled=True)
        session.add(alias)
        session.flush()
        session.add(Destination(alias_id=alias.id, email=dest, enabled=True))
    write_audit(session, "setup.complete", user_id=None, target=domain_name, request=request)
    session.flush()
    token = create_session_token(user.id, user.username)
    csrf = new_csrf_token()
    response.set_cookie(COOKIE_NAME, token, **cookie_kwargs())
    response.set_cookie(CSRF_COOKIE, csrf, **csrf_cookie_kwargs())
    return {
        "ok": True,
        "csrf": csrf,
        "hostname": hostname,
        "domain": domain_name,
        "needs_dns": True,
        "message": "Administrator created. Verify DNS before enabling the domain.",
    }
