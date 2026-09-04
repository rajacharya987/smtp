"""Pytest fixtures. Uses a temporary SQLite database."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("MAILGATE_ETC", str(Path(os.environ.get("TMP", "/tmp")) / "mailgate-test-etc"))
os.environ.setdefault("MAILGATE_DATA_DIR", str(Path(os.environ.get("TMP", "/tmp")) / "mailgate-test-data"))
os.environ.setdefault("MAILGATE_SECRETS_DIR", str(Path(os.environ["MAILGATE_ETC"]) / "secrets"))
os.environ.setdefault("MAILGATE_POSTFIX_DIR", str(Path(os.environ["MAILGATE_ETC"]) / "postfix"))
os.environ["MAILGATE_DATABASE_URL"] = "sqlite:///" + str(
    Path(os.environ["MAILGATE_DATA_DIR"]) / "test.db"
)

# Point config at a writable location before importing the app.
from mailgate.paths import DATA_DIR, ETC_DIR, SECRETS_DIR  # noqa: E402

for path in (ETC_DIR, DATA_DIR, SECRETS_DIR):
    path.mkdir(parents=True, exist_ok=True)

# Force sqlite regardless of yaml
os.environ["MAILGATE_CONFIG"] = str(ETC_DIR / "config.yml")
(ETC_DIR / "config.yml").write_text(
    f"""
server:
  hostname: mail.example.com
web:
  host: 127.0.0.1
  port: 8000
  secure_cookies: false
  cors_origins: []
smtp:
  host: 0.0.0.0
  port: 25
database:
  url: sqlite:///{DATA_DIR / "test.db"}
security:
  login_max_attempts: 5
  login_lockout_minutes: 15
  rate_limit_per_minute: 10000
logging:
  level: info
  retain_events_days: 30
  store_bodies: false
""",
    encoding="utf-8",
)


@pytest.fixture
def db():
    from mailgate.config import reload_config
    from mailgate.db import Base, get_engine, init_db, reset_engine

    reload_config()
    reset_engine()
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield engine
    reset_engine()


@pytest.fixture
def client(db):
    from mailgate.config import reload_config
    from mailgate.main import create_app

    reload_config()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_client(client):
    from mailgate.db import get_session_factory
    from mailgate.models import User
    from mailgate.security import hash_password

    session = get_session_factory()()
    session.add(User(username="admin", password_hash=hash_password("CorrectHorse-1!"), is_admin=True))
    session.commit()
    session.close()
    response = client.post("/api/auth/login", json={"username": "admin", "password": "CorrectHorse-1!"})
    assert response.status_code == 200, response.text
    return client
