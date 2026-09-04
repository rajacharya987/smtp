"""DNS instructions and live checks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from mailgate.api.deps import admin_user, db_session
from mailgate.models import Domain, User
from mailgate.services.dns import recommended_records, verify_domain
from mailgate.services.network import detect_network

router = APIRouter(prefix="/api/dns", tags=["dns"])


def _domain(session: Session, key: str) -> Domain:
    domain = None
    if key.isdigit():
        domain = session.get(Domain, int(key))
    if domain is None:
        from sqlalchemy import select

        domain = session.scalar(select(Domain).where(Domain.name == key.lower()))
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain


@router.get("/{domain_key}")
def dns_for_domain(domain_key: str, session: Session = Depends(db_session), _: User = Depends(admin_user)):
    domain = _domain(session, domain_key)
    net = detect_network()
    from mailgate.config import load_config

    hostname = domain.hostname or load_config().server.hostname
    records = recommended_records(domain.name, hostname, net.public_ipv4, domain.dkim_selector)
    return {
        "domain": domain.name,
        "hostname": hostname,
        "public_ip": net.public_ipv4,
        "records": [r.__dict__ for r in records],
        "spf": f"v=spf1 mx a:{hostname} ~all",
        "dmarc": f"v=DMARC1; p={domain.dmarc_policy}; rua=mailto:dmarc@{domain.name}",
        "dmarc_name": f"_dmarc.{domain.name}",
        "ptr_note": (
            "PTR / reverse DNS is set by your ISP or VPS provider, not by MailGate "
            "and not by your domain DNS panel."
        ),
    }


@router.post("/{domain_key}/check")
def check_domain(domain_key: str, session: Session = Depends(db_session), _: User = Depends(admin_user)):
    domain = _domain(session, domain_key)
    report = verify_domain(domain)
    domain.verified = report.verified
    if not report.verified:
        domain.enabled = False
    return report.to_dict()
