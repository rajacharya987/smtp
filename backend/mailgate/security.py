"""Authentication, password hashing, CSRF, and request hardening."""

from __future__ import annotations

import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Request, status

from mailgate.config import load_config
from mailgate.paths import JWT_SECRET_FILE, SECRETS_DIR

ph = PasswordHasher()
COOKIE_NAME = "mailgate_session"
CSRF_COOKIE = "mailgate_csrf"
MIN_PASSWORD_LENGTH = 12

_PASSWORD_UPPER = re.compile(r"[A-Z]")
_PASSWORD_LOWER = re.compile(r"[a-z]")
_PASSWORD_DIGIT = re.compile(r"[0-9]")
_PASSWORD_SPECIAL = re.compile(r"[^A-Za-z0-9]")


def ensure_jwt_secret() -> str:
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    if JWT_SECRET_FILE.exists():
        return JWT_SECRET_FILE.read_text(encoding="utf-8").strip()
    secret = secrets.token_urlsafe(48)
    fd = os.open(JWT_SECRET_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(secret)
    return secret


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def validate_password_strength(password: str) -> list[str]:
    errors: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if not _PASSWORD_UPPER.search(password):
        errors.append("Password must contain an uppercase letter")
    if not _PASSWORD_LOWER.search(password):
        errors.append("Password must contain a lowercase letter")
    if not _PASSWORD_DIGIT.search(password):
        errors.append("Password must contain a digit")
    if not _PASSWORD_SPECIAL.search(password):
        errors.append("Password must contain a special character")
    common = {"password", "password123", "admin123", "mailgate", "letmein", "qwerty12345"}
    if password.lower() in common:
        errors.append("Password is too common")
    return errors


def create_session_token(user_id: int, username: str) -> str:
    cfg = load_config()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=cfg.web.session_hours)).timestamp()),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, ensure_jwt_secret(), algorithm="HS256")


def decode_session_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, ensure_jwt_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from exc


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def cookie_kwargs() -> dict[str, Any]:
    cfg = load_config()
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": cfg.web.secure_cookies,
        "path": "/",
        "max_age": cfg.web.session_hours * 3600,
    }


def csrf_cookie_kwargs() -> dict[str, Any]:
    cfg = load_config()
    return {
        "httponly": False,
        "samesite": "lax",
        "secure": cfg.web.secure_cookies,
        "path": "/",
        "max_age": cfg.web.session_hours * 3600,
    }


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def origin_allowed(request: Request) -> bool:
    """Reject cross-site mutating requests.

    Caddy serves the dashboard and API on the same origin in production.
    Development may set MAILGATE_CORS_ORIGINS.
    """
    if request.method in SAFE_METHODS:
        return True
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    host = request.headers.get("host", "")
    cfg = load_config()
    allowed = set(cfg.web.cors_origins)
    if host:
        allowed.add(f"https://{host}")
        allowed.add(f"http://{host}")
    if origin:
        return origin in allowed
    if referer:
        return any(referer.startswith(item) for item in allowed)
    # Same-origin cookie API clients (CLI / curl) without Origin are allowed
    # only from loopback.
    client = request.client.host if request.client else ""
    return client in {"127.0.0.1", "::1", "localhost"}


def csrf_ok(request: Request) -> bool:
    if request.method in SAFE_METHODS:
        return True
    header = request.headers.get("x-csrf-token") or request.headers.get("x-xsrf-token")
    cookie = request.cookies.get(CSRF_COOKIE)
    if not header or not cookie:
        # CLI / local tools using session cookie from loopback.
        client = request.client.host if request.client else ""
        if client in {"127.0.0.1", "::1", "localhost"} and not header:
            return True
        return False
    return hmac.compare_digest(header, cookie)


def safe_service_name(name: str) -> str:
    """Allow only known systemd units. Never interpolate user input into a shell."""
    allowed = {
        "mailgate-api",
        "mailgate-worker",
        "postfix",
        "postgresql",
        "caddy",
        "rspamd",
        "nftables",
    }
    if name not in allowed:
        raise ValueError("Unknown service")
    return name
