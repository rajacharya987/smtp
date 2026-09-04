"""Mandatory open-relay protection tests.

An internet sender MUST NOT be able to use MailGate as a free relay to
an arbitrary external recipient such as victim@gmail.com.
"""

from __future__ import annotations

from mailgate.models import Alias, Destination, Domain
from mailgate.policy import assert_not_open_relay, decide_recipient
from mailgate.services.postfix import render_main_cf_snippet, virtual_maps
from mailgate.validate import ValidationError


def _domain_with_forwarder() -> list[Domain]:
    domain = Domain(
        id=1,
        name="example.com",
        hostname="mail.example.com",
        enabled=True,
        verified=True,
        catch_all_enabled=False,
    )
    alias = Alias(id=1, domain_id=1, local_part="hello", enabled=True)
    alias.destinations = [
        Destination(id=1, alias_id=1, email="mygmail@gmail.com", enabled=True)
    ]
    domain.aliases = [alias]
    return [domain]


def test_valid_recipient_accepted():
    decision = decide_recipient("hello@example.com", _domain_with_forwarder())
    assert decision.allowed is True
    assert decision.destinations == ["mygmail@gmail.com"]


def test_unknown_local_part_rejected():
    decision = decide_recipient("nobody@example.com", _domain_with_forwarder())
    assert decision.allowed is False


def test_unknown_domain_rejected():
    decision = decide_recipient("hello@not-configured.test", _domain_with_forwarder())
    assert decision.allowed is False


def test_external_relay_attempt_rejected():
    """MAIL FROM:<attacker@example.net> RCPT TO:<victim@gmail.com> must fail.

    gmail.com is a forwarding *destination*, not a local domain. Accepting
    it as RCPT TO would make MailGate an open relay.
    """
    decision = assert_not_open_relay("victim@gmail.com", _domain_with_forwarder())
    assert decision.allowed is False
    assert "open relay" in decision.reason.lower() or "not local" in decision.reason.lower()


def test_destination_address_is_not_a_recipient():
    domains = _domain_with_forwarder()
    # The Gmail mailbox is where we forward TO. It is not a mailbox we receive FOR.
    decision = decide_recipient("mygmail@gmail.com", domains)
    assert decision.allowed is False


def test_unverified_domain_rejected():
    domains = _domain_with_forwarder()
    domains[0].verified = False
    decision = decide_recipient("hello@example.com", domains)
    assert decision.allowed is False


def test_disabled_domain_rejected():
    domains = _domain_with_forwarder()
    domains[0].enabled = False
    decision = decide_recipient("hello@example.com", domains)
    assert decision.allowed is False


def test_postfix_snippet_is_not_an_open_relay():
    snippet = render_main_cf_snippet()
    assert "relay_domains =" in snippet
    assert "mynetworks = 127.0.0.0/8" in snippet
    assert "reject_unauth_destination" in snippet
    assert "inet_interfaces = all" in snippet
    # Must not permit the world
    assert "mynetworks = 0.0.0.0/0" not in snippet
    assert "smtpd_recipient_restrictions = permit" not in snippet.replace("permit_mynetworks", "")


def test_virtual_maps_only_include_enabled_verified(db):
    from mailgate.db import get_session_factory

    session = get_session_factory()()
    domain = Domain(name="example.com", enabled=True, verified=True, hostname="mail.example.com")
    session.add(domain)
    session.flush()
    alias = Alias(domain_id=domain.id, local_part="hello", enabled=True)
    session.add(alias)
    session.flush()
    session.add(Destination(alias_id=alias.id, email="mygmail@gmail.com", enabled=True))
    session.commit()
    domains_file, aliases_file = virtual_maps(session)
    session.close()
    assert "example.com OK" in domains_file
    assert "hello@example.com" in aliases_file
    assert "mygmail@gmail.com" in aliases_file
    assert "victim@gmail.com" not in aliases_file.split("hello@example.com")[0]


def test_catch_all_warning_path():
    domain = Domain(
        id=1,
        name="example.com",
        enabled=True,
        verified=True,
        catch_all_enabled=True,
        catch_all_destination="inbox@gmail.com",
    )
    domain.aliases = []
    decision = decide_recipient("random@example.com", [domain])
    assert decision.allowed is True
    assert decision.destinations == ["inbox@gmail.com"]


def test_invalid_rcpt_syntax():
    decision = decide_recipient("not-an-address", _domain_with_forwarder())
    assert decision.allowed is False
