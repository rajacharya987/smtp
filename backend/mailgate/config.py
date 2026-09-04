"""Load and validate /etc/mailgate/config.yml."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from mailgate.paths import CONFIG_FILE, DATA_DIR, SECRETS_DIR


class ServerConfig(BaseModel):
    hostname: str = "mail.local"


class WebConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    secure_cookies: bool = True
    session_hours: int = 12
    cors_origins: list[str] = Field(default_factory=list)


class SmtpConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 25
    submission_port: int = 587
    smtps_port: int = 465
    max_message_size: str = "25MB"
    enable_ipv6: bool = True
    banner_hostname: str | None = None


class DatabaseConfig(BaseModel):
    url: str = f"sqlite:///{DATA_DIR / 'mailgate.db'}"


class SecurityConfig(BaseModel):
    max_message_size: str = "25MB"
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15
    rate_limit_per_minute: int = 60
    smtp_conn_rate: int = 20
    smtp_conn_count: int = 10
    smtp_recipient_limit: int = 50


class LoggingConfig(BaseModel):
    level: str = "info"
    retain_events_days: int = 30
    store_bodies: bool = False


class SpamConfig(BaseModel):
    rspamd_enabled: bool = False
    rspamd_action: str = "reject"  # accept | reject | quarantine
    clamav_enabled: bool = False


class FirewallConfig(BaseModel):
    backend: str = "nftables"  # nftables | ufw | none
    allow_ssh: bool = True
    ssh_port: int = 22


class MailgateConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    smtp: SmtpConfig = Field(default_factory=SmtpConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    spam: SpamConfig = Field(default_factory=SpamConfig)
    firewall: FirewallConfig = Field(default_factory=FirewallConfig)
    secrets_dir: str = str(SECRETS_DIR)

    @field_validator("server")
    @classmethod
    def hostname_not_empty(cls, value: ServerConfig) -> ServerConfig:
        if not value.hostname.strip():
            raise ValueError("server.hostname must not be empty")
        return value


def _read_yaml(path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config {path} must be a YAML mapping")
    return data


@lru_cache(maxsize=1)
def load_config() -> MailgateConfig:
    return MailgateConfig.model_validate(_read_yaml(CONFIG_FILE))


def reload_config() -> MailgateConfig:
    load_config.cache_clear()
    return load_config()


def dump_config(cfg: MailgateConfig, path=None) -> None:
    target = path or CONFIG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = cfg.model_dump(mode="json")
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, default_flow_style=False)


def parse_size(value: str) -> int:
    """Parse values like 25MB / 10MiB / 1024 into bytes."""
    raw = value.strip().upper().replace(" ", "")
    multipliers = {
        "B": 1,
        "KB": 1000,
        "KIB": 1024,
        "K": 1024,
        "MB": 1000**2,
        "MIB": 1024**2,
        "M": 1024**2,
        "GB": 1000**3,
        "GIB": 1024**3,
        "G": 1024**3,
    }
    for suffix, mul in sorted(multipliers.items(), key=lambda item: -len(item[0])):
        if raw.endswith(suffix):
            return int(float(raw[: -len(suffix)]) * mul)
    return int(raw)
