"""Alias and destination tests."""

from __future__ import annotations

import pytest

from mailgate.db import get_session_factory
from mailgate.models import Domain
from mailgate.validate import ValidationError, normalize_email, normalize_local_part


def test_valid_alias():
    assert normalize_local_part("Hello") == "hello"
    assert normalize_local_part("jobs+list") == "jobs+list"


def test_invalid_destination():
    with pytest.raises(ValidationError):
        normalize_email("not-an-email")
    with pytest.raises(ValidationError):
        normalize_email("user@localhost")


def test_duplicate_alias(admin_client):
    domain = admin_client.post("/api/domains", json={"name": "example.com"}).json()
    payload = {
        "domain_id": domain["id"],
        "local_part": "hello",
        "destinations": ["mygmail@gmail.com"],
    }
    r1 = admin_client.post("/api/aliases", json=payload)
    assert r1.status_code == 201, r1.text
    r2 = admin_client.post("/api/aliases", json=payload)
    assert r2.status_code == 409


def test_one_to_many_destinations(admin_client):
    domain = admin_client.post("/api/domains", json={"name": "example.com"}).json()
    r = admin_client.post(
        "/api/aliases",
        json={
            "domain_id": domain["id"],
            "local_part": "hello",
            "destinations": ["user1@gmail.com", "user2@outlook.com"],
        },
    )
    assert r.status_code == 201, r.text
    emails = [d["email"] for d in r.json()["destinations"]]
    assert emails == ["user1@gmail.com", "user2@outlook.com"]


def _enable_domain(name: str) -> None:
    from sqlalchemy import select

    session = get_session_factory()()
    domain = session.scalar(select(Domain).where(Domain.name == name))
    assert domain is not None
    domain.verified = True
    domain.enabled = True
    session.commit()
    session.close()


def test_disabled_alias_not_in_virtual_map(admin_client):
    from mailgate.db import get_session_factory
    from mailgate.services.postfix import virtual_maps

    domain = admin_client.post("/api/domains", json={"name": "example.com"}).json()
    admin_client.post(
        "/api/aliases",
        json={
            "domain_id": domain["id"],
            "local_part": "hello",
            "destinations": ["mygmail@gmail.com"],
            "enabled": False,
        },
    )
    _enable_domain("example.com")
    session = get_session_factory()()
    _domains, aliases = virtual_maps(session)
    session.close()
    assert "hello@example.com" not in aliases
