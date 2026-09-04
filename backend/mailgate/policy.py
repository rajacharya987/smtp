"""Recipient policy — the source of truth for open-relay protection.

MailGate must accept mail only when:

1. The recipient domain is a configured, enabled MailGate domain, AND
2. The recipient matches an enabled alias, or an enabled catch-all.

An internet sender mailing an arbitrary external address (for example
victim@gmail.com) MUST be rejected. Matching a destination address is
not enough: destinations are where we *send*, not addresses we *receive*.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mailgate.models import Alias, Domain
from mailgate.validate import ValidationError, normalize_domain, normalize_email, split_address


@dataclass
class RecipientDecision:
    allowed: bool
    reason: str
    domain: str | None = None
    local_part: str | None = None
    destinations: list[str] | None = None


def load_routing_table(session: Session) -> list[Domain]:
    stmt = select(Domain).options(
        selectinload(Domain.aliases).selectinload(Alias.destinations)
    )
    return list(session.scalars(stmt))


def destinations_for_alias(alias: Alias) -> list[str]:
    return [d.email.lower() for d in alias.destinations if d.enabled]


def decide_recipient(address: str, domains: list[Domain]) -> RecipientDecision:
    """Return whether Postfix should accept this RCPT TO address."""
    try:
        local, domain_name = split_address(address)
    except ValidationError as exc:
        return RecipientDecision(False, str(exc))

    domain = next((d for d in domains if d.name == domain_name), None)
    if domain is None:
        return RecipientDecision(
            False,
            "Unknown domain — not configured in MailGate",
            domain=domain_name,
            local_part=local,
        )
    if not domain.enabled:
        return RecipientDecision(
            False,
            "Domain is disabled",
            domain=domain_name,
            local_part=local,
        )
    if not domain.verified:
        return RecipientDecision(
            False,
            "Domain is not verified",
            domain=domain_name,
            local_part=local,
        )

    alias = next(
        (a for a in domain.aliases if a.local_part == local and a.enabled),
        None,
    )
    if alias is not None:
        dests = destinations_for_alias(alias)
        if not dests:
            return RecipientDecision(
                False,
                "Alias has no enabled destinations",
                domain=domain_name,
                local_part=local,
            )
        return RecipientDecision(
            True,
            "Matched alias",
            domain=domain_name,
            local_part=local,
            destinations=dests,
        )

    if domain.catch_all_enabled and domain.catch_all_destination:
        try:
            dest = normalize_email(domain.catch_all_destination)
        except ValidationError:
            return RecipientDecision(
                False,
                "Catch-all destination is invalid",
                domain=domain_name,
                local_part=local,
            )
        return RecipientDecision(
            True,
            "Matched catch-all",
            domain=domain_name,
            local_part=local,
            destinations=[dest],
        )

    return RecipientDecision(
        False,
        "No matching alias or catch-all",
        domain=domain_name,
        local_part=local,
    )


def is_configured_destination(email: str, domains: list[Domain]) -> bool:
    """True if email is a forwarding *target*. Never used to accept inbound RCPT."""
    try:
        target = normalize_email(email)
    except ValidationError:
        return False
    for domain in domains:
        if domain.catch_all_enabled and domain.catch_all_destination:
            try:
                if normalize_email(domain.catch_all_destination) == target:
                    return True
            except ValidationError:
                pass
        for alias in domain.aliases:
            if target in destinations_for_alias(alias):
                return True
    return False


def assert_not_open_relay(rcpt_to: str, domains: list[Domain]) -> RecipientDecision:
    """Mandatory helper for tests and runtime checks."""
    decision = decide_recipient(rcpt_to, domains)
    # Extra belt-and-suspenders: if the recipient domain is not local, deny
    # even if someone later confuses destinations with recipients.
    try:
        _, domain_name = split_address(rcpt_to)
        local_names = {d.name for d in domains}
        if domain_name not in local_names:
            return RecipientDecision(
                False,
                "Recipient domain is not local — open relay blocked",
                domain=domain_name,
            )
    except ValidationError as exc:
        return RecipientDecision(False, str(exc))
    return decision


def domain_is_local(name: str, domains: list[Domain]) -> bool:
    try:
        normalized = normalize_domain(name)
    except ValidationError:
        return False
    return any(d.name == normalized for d in domains)
