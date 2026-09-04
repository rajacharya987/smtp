"""Network helpers must never assume public IP equals local IP."""

from __future__ import annotations

from mailgate.services.network import NetworkInfo, _is_cgnat, _is_private


def test_private_ranges():
    assert _is_private("192.168.1.20")
    assert _is_private("10.0.0.5")
    assert _is_private("172.16.0.2")
    assert not _is_private("203.0.113.10")


def test_cgnat_range():
    assert _is_cgnat("100.64.1.1")
    assert _is_cgnat("100.127.0.1")
    assert not _is_cgnat("100.63.0.1")
    assert not _is_cgnat("8.8.8.8")


def test_behind_nat_flag_when_ips_differ():
    info = NetworkInfo(
        local_ipv4="192.168.1.20",
        public_ipv4="203.0.113.10",
        behind_nat=True,
    )
    assert info.local_ipv4 != info.public_ipv4
    assert info.behind_nat is True


def test_dns_records_use_detected_ip():
    from mailgate.services.dns import recommended_records

    records = recommended_records("example.com", "mail.example.com", "203.0.113.10")
    a = next(r for r in records if r.type == "A")
    mx = next(r for r in records if r.type == "MX")
    assert a.value == "203.0.113.10"
    assert mx.value == "mail.example.com"
    assert mx.priority == 10
    spf = next(r for r in records if r.purpose == "SPF")
    assert "v=spf1" in spf.value
    assert "mail.example.com" in spf.value
