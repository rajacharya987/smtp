"""Domain validation tests."""

from __future__ import annotations

import pytest

from mailgate.validate import ValidationError, normalize_domain


def test_valid_domain():
    assert normalize_domain("Example.COM") == "example.com"
    assert normalize_domain("mail.sub.example.com.") == "mail.sub.example.com"


def test_invalid_domain():
    with pytest.raises(ValidationError):
        normalize_domain("not a domain")
    with pytest.raises(ValidationError):
        normalize_domain("-bad.com")
    with pytest.raises(ValidationError):
        normalize_domain("localhost")
    with pytest.raises(ValidationError):
        normalize_domain("*.example.com")
    with pytest.raises(ValidationError):
        normalize_domain("")


def test_duplicate_domain(admin_client):
    r1 = admin_client.post("/api/domains", json={"name": "example.com"})
    assert r1.status_code == 201, r1.text
    r2 = admin_client.post("/api/domains", json={"name": "EXAMPLE.com"})
    assert r2.status_code == 409


def test_domain_not_enabled_until_verified(admin_client):
    created = admin_client.post("/api/domains", json={"name": "example.com"})
    domain_id = created.json()["id"]
    assert created.json()["enabled"] is False
    assert created.json()["verified"] is False
    patched = admin_client.patch(f"/api/domains/{domain_id}", json={"enabled": True})
    assert patched.status_code == 400
