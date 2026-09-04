"""Input validation for domains, aliases, and destinations.

All user-supplied values that later appear in Postfix maps must pass
through these helpers. Values are stored as data files, never interpolated
into shell commands.
"""

from __future__ import annotations

import re

from email_validator import EmailNotValidError, validate_email

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)
LOCAL_PART_RE = re.compile(r"^[A-Za-z0-9._+-]{1,64}$")
HOSTNAME_RE = DOMAIN_RE

RESERVED_DOMAINS = {
    "localhost",
    "localhost.localdomain",
    "example.com",
    "example.net",
    "example.org",
    "invalid",
    "test",
}

# example.com is allowed as a documented demo domain in local/dev setups,
# but we still reject obviously unsafe names.
BLOCKED_DOMAINS = {
    "localhost",
    "localhost.localdomain",
    "invalid",
}


class ValidationError(ValueError):
    pass


def normalize_domain(value: str) -> str:
    name = value.strip().lower().rstrip(".")
    if name.startswith("*."):
        raise ValidationError("Wildcard domains are not supported; use catch-all on a real domain")
    if not DOMAIN_RE.match(name):
        raise ValidationError("Invalid domain name")
    if name in BLOCKED_DOMAINS:
        raise ValidationError("This domain name is not allowed")
    labels = name.split(".")
    if any(label.startswith("xn--") is False and not label.isascii() for label in labels):
        # IDNA: encode then store ASCII form
        try:
            name = name.encode("idna").decode("ascii")
        except Exception as exc:
            raise ValidationError("Invalid internationalized domain") from exc
        if not DOMAIN_RE.match(name):
            raise ValidationError("Invalid domain name")
    if len(labels) < 2:
        raise ValidationError("Domain must include a TLD")
    return name


def normalize_hostname(value: str) -> str:
    return normalize_domain(value)


def normalize_local_part(value: str) -> str:
    local = value.strip().lower()
    if local in {"*", "@"}:
        raise ValidationError("Use the catch-all option instead of '*' as a local part")
    if not LOCAL_PART_RE.match(local):
        raise ValidationError("Invalid local part")
    if ".." in local or local.startswith(".") or local.endswith("."):
        raise ValidationError("Invalid local part")
    return local


def normalize_email(value: str) -> str:
    try:
        result = validate_email(value.strip(), check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValidationError("Invalid email address") from exc
    email = result.normalized
    if email.count("@") != 1:
        raise ValidationError("Invalid email address")
    local, domain = email.rsplit("@", 1)
    if domain in BLOCKED_DOMAINS:
        raise ValidationError("Destination domain is not allowed")
    return email.lower()


def split_address(address: str) -> tuple[str, str]:
    if address.count("@") != 1:
        raise ValidationError("Address must look like user@domain")
    local, domain = address.strip().lower().split("@", 1)
    return normalize_local_part(local), normalize_domain(domain)


def postfix_map_safe(value: str) -> str:
    """Reject characters that could break Postfix map files."""
    if any(ch in value for ch in ["\n", "\r", "\t", "#", " ", ","]):
        raise ValidationError("Value contains characters that cannot appear in mail maps")
    return value
