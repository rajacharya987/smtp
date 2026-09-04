"""Pydantic request/response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class SetupAdminRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=12, max_length=256)


class SetupRequest(BaseModel):
    hostname: str
    domain: str
    admin_username: str = Field(min_length=3, max_length=64)
    admin_password: str = Field(min_length=12, max_length=256)
    first_local_part: str | None = None
    first_destination: str | None = None


class DomainCreate(BaseModel):
    name: str
    hostname: str | None = None


class DomainUpdate(BaseModel):
    enabled: bool | None = None
    hostname: str | None = None
    catch_all_enabled: bool | None = None
    catch_all_destination: str | None = None
    dmarc_policy: str | None = None
    dkim_selector: str | None = None


class DomainOut(BaseModel):
    id: int
    name: str
    hostname: str | None
    enabled: bool
    verified: bool
    catch_all_enabled: bool
    catch_all_destination: str | None
    dkim_selector: str
    dmarc_policy: str
    created_at: datetime
    alias_count: int = 0

    model_config = {"from_attributes": True}


class AliasCreate(BaseModel):
    domain_id: int
    local_part: str
    destinations: list[str] = Field(min_length=1)
    enabled: bool = True


class AliasUpdate(BaseModel):
    enabled: bool | None = None
    destinations: list[str] | None = None


class DestinationOut(BaseModel):
    id: int
    email: str
    enabled: bool

    model_config = {"from_attributes": True}


class AliasOut(BaseModel):
    id: int
    domain_id: int
    domain_name: str
    local_part: str
    address: str
    enabled: bool
    destinations: list[DestinationOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class ForwarderCreate(BaseModel):
    domain: str
    local_part: str
    destinations: list[str] = Field(min_length=1)
    enabled: bool = True


class SettingsUpdate(BaseModel):
    hostname: str | None = None
    max_message_size: str | None = None
    retain_events_days: int | None = None
    rspamd_enabled: bool | None = None
    secure_cookies: bool | None = None
    enable_ipv6: bool | None = None
    dmarc_policy_default: str | None = None


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool

    model_config = {"from_attributes": True}
