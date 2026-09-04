"""Filesystem locations used by MailGate.

Runtime paths default to production locations under /etc and /var.
They can be overridden with environment variables so the same code
runs in development without writing to system directories.
"""

from __future__ import annotations

import os
from pathlib import Path


def _env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default))


ETC_DIR = _env_path("MAILGATE_ETC", "/etc/mailgate")
CONFIG_FILE = Path(os.environ.get("MAILGATE_CONFIG", str(ETC_DIR / "config.yml")))
SECRETS_DIR = _env_path("MAILGATE_SECRETS_DIR", str(ETC_DIR / "secrets"))
POSTFIX_DIR = _env_path("MAILGATE_POSTFIX_DIR", str(ETC_DIR / "postfix"))
DATA_DIR = _env_path("MAILGATE_DATA_DIR", "/var/lib/mailgate")
LOG_DIR = _env_path("MAILGATE_LOG_DIR", "/var/log/mailgate")
WEB_DIR = _env_path("MAILGATE_WEB_DIR", "/usr/share/mailgate/web")
BACKUP_DIR = _env_path("MAILGATE_BACKUP_DIR", str(DATA_DIR / "backups"))

JWT_SECRET_FILE = SECRETS_DIR / "jwt_secret"
DB_PASSWORD_FILE = SECRETS_DIR / "db_password"
DKIM_DIR = SECRETS_DIR / "dkim"


def ensure_runtime_dirs() -> None:
    """Create runtime directories when the process is allowed to write them."""
    for path in (ETC_DIR, SECRETS_DIR, POSTFIX_DIR, DATA_DIR, LOG_DIR, DKIM_DIR, BACKUP_DIR):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            continue
