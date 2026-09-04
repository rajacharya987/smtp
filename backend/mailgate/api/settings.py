"""Application settings."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from mailgate.api.deps import admin_user, db_session
from mailgate.audit import write_audit
from mailgate.config import dump_config, load_config, reload_config
from mailgate.models import User
from mailgate.schemas import SettingsUpdate
from mailgate.services.dkim import generate_keypair, public_record
from mailgate.services.firewall import guidance
from mailgate.services.network import detect_network
from mailgate.services.postfix import apply_and_reload
from mailgate.validate import ValidationError, normalize_hostname

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings(_: User = Depends(admin_user)):
    cfg = load_config()
    return cfg.model_dump(mode="json")


@router.put("")
def update_settings(
    payload: SettingsUpdate,
    request: Request,
    session: Session = Depends(db_session),
    user: User = Depends(admin_user),
):
    cfg = load_config()
    try:
        if payload.hostname:
            cfg.server.hostname = normalize_hostname(payload.hostname)
        if payload.max_message_size:
            cfg.smtp.max_message_size = payload.max_message_size
            cfg.security.max_message_size = payload.max_message_size
        if payload.retain_events_days is not None:
            if payload.retain_events_days < 1 or payload.retain_events_days > 365:
                raise ValidationError("Retention must be between 1 and 365 days")
            cfg.logging.retain_events_days = payload.retain_events_days
        if payload.rspamd_enabled is not None:
            cfg.spam.rspamd_enabled = payload.rspamd_enabled
        if payload.secure_cookies is not None:
            cfg.web.secure_cookies = payload.secure_cookies
        if payload.enable_ipv6 is not None:
            cfg.smtp.enable_ipv6 = payload.enable_ipv6
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    dump_config(cfg)
    reload_config()
    apply_and_reload(session)
    write_audit(session, "settings.update", user_id=user.id, request=request)
    return cfg.model_dump(mode="json")


@router.get("/network")
def network_settings(_: User = Depends(admin_user)):
    net = detect_network()
    return {
        "network": net.to_dict(),
        "firewall": guidance(net.local_ipv4),
        "dynamic_ip_warning": (
            "Your public IP may be dynamic. For reliable mail hosting, a static public IP "
            "or stable DNS/IP configuration is recommended."
            if net.possibly_dynamic
            else None
        ),
        "port25_warning": (
            "Inbound SMTP normally uses TCP port 25. Some residential ISPs block port 25. "
            "If inbound port 25 is blocked, this machine cannot directly receive mail from "
            "the public internet. Changing DNS cannot bypass an ISP block."
        ),
    }


@router.get("/dkim/{domain}")
def dkim_info(domain: str, selector: str = "mail", _: User = Depends(admin_user)):
    return public_record(domain, selector)


@router.post("/dkim/{domain}")
def dkim_generate(
    domain: str,
    request: Request,
    selector: str = "mail",
    session: Session = Depends(db_session),
    user: User = Depends(admin_user),
):
    record = generate_keypair(domain, selector)
    write_audit(session, "dkim.generate", user_id=user.id, target=domain, request=request)
    return record
