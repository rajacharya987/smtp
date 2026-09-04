"""Authentication, injection, CSRF, path traversal, rate-limit tests."""

from __future__ import annotations

from mailgate.security import safe_service_name, validate_password_strength, verify_password, hash_password
from mailgate.services.backup import _safe_extract
from mailgate.services.postfix import queue_action
from mailgate.validate import ValidationError, normalize_domain


def test_passwords_are_hashed():
    hashed = hash_password("CorrectHorse-1!")
    assert hashed != "CorrectHorse-1!"
    assert hashed.startswith("$argon2")
    assert verify_password("CorrectHorse-1!", hashed)
    assert not verify_password("wrong", hashed)


def test_default_password_rejected():
    errors = validate_password_strength("admin")
    assert errors
    errors = validate_password_strength("CorrectHorse-1!")
    assert errors == []


def test_auth_required(client):
    r = client.get("/api/domains")
    assert r.status_code == 401


def test_login_wrong_password(admin_client):
    r = admin_client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_sql_injection_in_domain(admin_client):
    r = admin_client.post("/api/domains", json={"name": "example.com'); DROP TABLE domains;--"})
    assert r.status_code == 400
    listing = admin_client.get("/api/domains")
    assert listing.status_code == 200


def test_command_injection_rejected_in_service_name():
    try:
        safe_service_name("postfix; rm -rf /")
        assert False, "should have raised"
    except ValueError:
        pass
    try:
        safe_service_name("postfix$(reboot)")
        assert False, "should have raised"
    except ValueError:
        pass
    assert safe_service_name("postfix") == "postfix"


def test_queue_id_rejects_shell_metacharacters():
    ok, message = queue_action("abc;reboot", "retry")
    assert ok is False
    assert "Invalid" in message


def test_path_traversal_domain():
    try:
        normalize_domain("../../etc/passwd")
        assert False, "should have raised"
    except ValidationError:
        pass


def test_csrf_and_origin(admin_client):
    # Same-origin loopback without Origin is allowed for local tools.
    r = admin_client.post("/api/domains", json={"name": "ok.example"})
    assert r.status_code in {201, 409}
    # Cross-site Origin must be rejected.
    r = admin_client.post(
        "/api/domains",
        json={"name": "evil.example"},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403


def test_xss_not_stored_raw_script_as_domain(admin_client):
    r = admin_client.post("/api/domains", json={"name": "<script>alert(1)</script>.com"})
    assert r.status_code == 400


def test_health_unauthenticated(client):
    r = client.get("/api/system/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_setup_creates_admin_once(client):
    payload = {
        "hostname": "mail.example.com",
        "domain": "example.com",
        "admin_username": "admin",
        "admin_password": "CorrectHorse-1!",
        "first_local_part": "hello",
        "first_destination": "mygmail@gmail.com",
    }
    r1 = client.post("/api/setup", json=payload)
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/setup", json=payload)
    assert r2.status_code == 409
