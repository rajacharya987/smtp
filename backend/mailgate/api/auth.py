"""Login / logout / session."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mailgate.api.deps import current_user, db_session
from mailgate.audit import write_audit
from mailgate.config import load_config
from mailgate.models import User
from mailgate.ratelimit import enforce
from mailgate.schemas import LoginRequest, UserOut
from mailgate.security import (
    COOKIE_NAME,
    CSRF_COOKIE,
    cookie_kwargs,
    create_session_token,
    csrf_cookie_kwargs,
    new_csrf_token,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response, session: Session = Depends(db_session)):
    cfg = load_config()
    enforce(request, name="login", limit=cfg.security.login_max_attempts, window_seconds=60)
    user = session.scalar(select(User).where(func.lower(User.username) == payload.username.lower()))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked after failed logins",
        )

    if not verify_password(payload.password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= cfg.security.login_max_attempts:
            user.locked_until = now + timedelta(minutes=cfg.security.login_lockout_minutes)
        write_audit(session, "login_failed", user_id=user.id, request=request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login = now
    token = create_session_token(user.id, user.username)
    csrf = new_csrf_token()
    response.set_cookie(COOKIE_NAME, token, **cookie_kwargs())
    response.set_cookie(CSRF_COOKIE, csrf, **csrf_cookie_kwargs())
    write_audit(session, "login", user_id=user.id, request=request)
    return {"ok": True, "user": UserOut.model_validate(user), "csrf": csrf}


@router.post("/logout")
def logout(request: Request, response: Response, session: Session = Depends(db_session), user: User = Depends(current_user)):
    response.delete_cookie(COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    write_audit(session, "logout", user_id=user.id, request=request)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return UserOut.model_validate(user)
