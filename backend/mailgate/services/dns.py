"""DNS instruction generation and live verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import dns.exception
import dns.resolver
import dns.reversename

from mailgate.config import load_config
from mailgate.models import Domain
from mailgate.services.network import detect_network


@dataclass
class DnsRecord:
    type: str
    name: str
    value: str
    priority: int | None = None
    purpose: str = ""


@dataclass
class DnsCheckResult:
    check: str
    status: str  # ok | fail | warn | unknown
    expected: str | None = None
    actual: str | None = None
    message: str = ""


@dataclass
class DnsReport:
    domain: str
    hostname: str
    public_ip: str | None
    records: list[DnsRecord] = field(default_factory=list)
    checks: list[DnsCheckResult] = field(default_factory=list)
    verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "hostname": self.hostname,
            "public_ip": self.public_ip,
            "records": [r.__dict__ for r in self.records],
            "checks": [c.__dict__ for c in self.checks],
            "verified": self.verified,
        }


def _resolver() -> dns.resolver.Resolver:
    res = dns.resolver.Resolver()
    res.lifetime = 4
    res.timeout = 3
    return res


def lookup(name: str, rdtype: str) -> list[str]:
    try:
        answers = _resolver().resolve(name, rdtype)
        return sorted(str(item).strip() for item in answers)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
        return []
    except Exception:
        return []


def lookup_ptr(ip: str) -> list[str]:
    try:
        rev = dns.reversename.from_address(ip)
        answers = _resolver().resolve(rev, "PTR")
        return sorted(str(item).rstrip(".") for item in answers)
    except Exception:
        return []


def mail_hostname(domain: Domain | None = None) -> str:
    cfg = load_config()
    if domain and domain.hostname:
        return domain.hostname
    return cfg.server.hostname


def recommended_records(domain_name: str, hostname: str, public_ip: str | None, selector: str = "mail") -> list[DnsRecord]:
    ip_value = public_ip or "YOUR_PUBLIC_IP"
    host_label = hostname
    if hostname.endswith("." + domain_name):
        host_label = hostname[: -(len(domain_name) + 1)]
    elif hostname == domain_name:
        host_label = "@"

    records = [
        DnsRecord("A", host_label, ip_value, purpose="SMTP hostname"),
        DnsRecord("MX", "@", hostname, priority=10, purpose="Mail exchanger"),
        DnsRecord("TXT", "@", f"v=spf1 mx a:{hostname} ~all", purpose="SPF"),
        DnsRecord(
            "TXT",
            "_dmarc",
            f"v=DMARC1; p=none; rua=mailto:dmarc@{domain_name}",
            purpose="DMARC (start with p=none)",
        ),
        DnsRecord(
            "TXT",
            f"{selector}._domainkey",
            "v=DKIM1; k=rsa; p=PUBLIC_KEY",
            purpose="DKIM (replace PUBLIC_KEY after generation)",
        ),
    ]
    return records


def verify_domain(domain: Domain, public_ip: str | None = None) -> DnsReport:
    hostname = mail_hostname(domain)
    net = detect_network()
    ip = public_ip or net.public_ipv4
    records = recommended_records(domain.name, hostname, ip, domain.dkim_selector)
    checks: list[DnsCheckResult] = []

    a_records = lookup(hostname, "A")
    if ip and ip in a_records:
        checks.append(
            DnsCheckResult("A", "ok", expected=ip, actual=", ".join(a_records), message=f"{hostname} points at {ip}")
        )
    elif a_records and ip and ip not in a_records:
        checks.append(
            DnsCheckResult(
                "A",
                "fail",
                expected=ip,
                actual=", ".join(a_records),
                message=(
                    f"{hostname} resolves to {', '.join(a_records)}. "
                    f"Expected {ip}. Mail servers will deliver to the wrong host."
                ),
            )
        )
    elif a_records:
        checks.append(
            DnsCheckResult(
                "A",
                "warn",
                expected=ip,
                actual=", ".join(a_records),
                message="A record exists but the public IP of this machine is unknown, so it cannot be compared.",
            )
        )
    else:
        checks.append(
            DnsCheckResult(
                "A",
                "fail",
                expected=ip,
                actual=None,
                message=f"No A record for {hostname}. Create: {hostname} → {ip or 'YOUR_PUBLIC_IP'}",
            )
        )

    mx = lookup(domain.name, "MX")
    mx_hosts = []
    for item in mx:
        parts = item.split()
        host = parts[-1].rstrip(".") if parts else item.rstrip(".")
        mx_hosts.append(host)
    if hostname.rstrip(".") in mx_hosts:
        checks.append(
            DnsCheckResult(
                "MX",
                "ok",
                expected=f"{domain.name} MX 10 {hostname}",
                actual="; ".join(mx),
                message="MX points at this mail hostname",
            )
        )
    elif mx:
        checks.append(
            DnsCheckResult(
                "MX",
                "fail",
                expected=f"{domain.name} MX 10 {hostname}",
                actual="; ".join(mx),
                message=f"MX record not pointing at {hostname}. Configure: MX @ → {hostname}",
            )
        )
    else:
        checks.append(
            DnsCheckResult(
                "MX",
                "fail",
                expected=f"{domain.name} MX 10 {hostname}",
                actual=None,
                message=f"MX record not found. Expected: {domain.name} MX 10 {hostname}",
            )
        )

    if ip:
        ptrs = lookup_ptr(ip)
        if hostname.rstrip(".") in ptrs:
            checks.append(
                DnsCheckResult(
                    "PTR",
                    "ok",
                    expected=hostname,
                    actual=", ".join(ptrs),
                    message="Reverse DNS matches the mail hostname",
                )
            )
        elif ptrs:
            checks.append(
                DnsCheckResult(
                    "PTR",
                    "warn",
                    expected=hostname,
                    actual=", ".join(ptrs),
                    message=(
                        "Reverse DNS is set but does not match the mail hostname. "
                        "PTR records are normally configured by your ISP/VPS provider, "
                        "not through your DNS hosting panel. MailGate cannot change PTR records."
                    ),
                )
            )
        else:
            checks.append(
                DnsCheckResult(
                    "PTR",
                    "warn",
                    expected=hostname,
                    actual=None,
                    message=(
                        "Reverse DNS is not configured. PTR records are normally configured by "
                        "your ISP/VPS/provider, not through DNS hosting. MailGate cannot set PTR."
                    ),
                )
            )
    else:
        checks.append(
            DnsCheckResult(
                "PTR",
                "unknown",
                message="Public IP unknown, PTR cannot be checked",
            )
        )

    txt = lookup(domain.name, "TXT")
    spf = [t.strip('"') for t in txt if "v=spf1" in t.lower().replace(" ", "")]
    # TXT records may come quoted
    spf = [t.replace('"', "") for t in txt if "spf1" in t.lower()]
    if spf:
        checks.append(DnsCheckResult("SPF", "ok", actual="; ".join(spf), message="SPF record present"))
    else:
        checks.append(
            DnsCheckResult(
                "SPF",
                "warn",
                expected=f"v=spf1 mx a:{hostname} ~all",
                message="No SPF record. Recommended TXT @ → v=spf1 mx a:%s ~all" % hostname,
            )
        )

    dmarc = lookup(f"_dmarc.{domain.name}", "TXT")
    if dmarc:
        checks.append(DnsCheckResult("DMARC", "ok", actual="; ".join(dmarc), message="DMARC record present"))
    else:
        checks.append(
            DnsCheckResult(
                "DMARC",
                "warn",
                expected=f"v=DMARC1; p={domain.dmarc_policy}; rua=mailto:dmarc@{domain.name}",
                message="No DMARC record. Start with p=none until forwarding is confirmed.",
            )
        )

    dkim_name = f"{domain.dkim_selector}._domainkey.{domain.name}"
    dkim = lookup(dkim_name, "TXT")
    if dkim:
        checks.append(DnsCheckResult("DKIM", "ok", actual="; ".join(dkim), message="DKIM TXT present"))
    else:
        checks.append(
            DnsCheckResult(
                "DKIM",
                "warn",
                expected=dkim_name,
                message="No DKIM record yet. Generate a key in the Security page, then publish the TXT record.",
            )
        )

    required_ok = all(
        c.status == "ok" for c in checks if c.check in {"A", "MX"}
    )
    report = DnsReport(
        domain=domain.name,
        hostname=hostname,
        public_ip=ip,
        records=records,
        checks=checks,
        verified=required_ok,
    )
    return report
