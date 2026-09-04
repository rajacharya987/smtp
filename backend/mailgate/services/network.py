"""Network discovery. Never assume public IP equals local IP."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any

PUBLIC_IP_ENDPOINTS = (
    ("https://api.ipify.org?format=json", "ip"),
    ("https://api64.ipify.org?format=json", "ip"),
    ("https://ifconfig.me/ip", None),
    ("https://icanhazip.com", None),
    ("https://ipv4.icanhazip.com", None),
)

IP_CHECK_TIMEOUT = 4


@dataclass
class NetworkInfo:
    local_ipv4: str | None = None
    local_ipv6: str | None = None
    public_ipv4: str | None = None
    public_ipv6: str | None = None
    interface: str | None = None
    gateway: str | None = None
    behind_nat: bool | None = None
    possibly_cgnat: bool = False
    possibly_dynamic: bool = False
    warning: str | None = None
    notes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


def _run(cmd: list[str]) -> str:
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _http_text(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MailGate/0.1"})
        with urllib.request.urlopen(req, timeout=IP_CHECK_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace").strip()
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def detect_public_ip() -> tuple[str | None, str | None]:
    v4 = None
    v6 = None
    for url, json_key in PUBLIC_IP_ENDPOINTS:
        body = _http_text(url)
        if not body:
            continue
        value = body
        if json_key:
            try:
                value = json.loads(body).get(json_key) or ""
            except json.JSONDecodeError:
                continue
        value = value.strip()
        if ":" in value and v6 is None:
            v6 = value
        elif value.count(".") == 3 and v4 is None:
            v4 = value
        if v4:
            break
    return v4, v6


def detect_local_ipv4() -> tuple[str | None, str | None]:
    """Return (address, interface) for the default-route IPv4 address."""
    # ip route get 1.1.1.1
    out = _run(["ip", "-4", "route", "get", "1.1.1.1"])
    if out:
        parts = out.split()
        addr = None
        iface = None
        if "src" in parts:
            addr = parts[parts.index("src") + 1]
        if "dev" in parts:
            iface = parts[parts.index("dev") + 1]
        if addr:
            return addr, iface
    # Fallback: UDP socket trick (does not send packets)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("1.1.1.1", 80))
        addr = sock.getsockname()[0]
        sock.close()
        return addr, None
    except OSError:
        return None, None


def detect_gateway() -> str | None:
    out = _run(["ip", "-4", "route", "show", "default"])
    if out:
        parts = out.split()
        if "via" in parts:
            return parts[parts.index("via") + 1]
    return None


def _is_cgnat(ip: str | None) -> bool:
    if not ip:
        return False
    # RFC 6598 shared address space 100.64.0.0/10
    try:
        octets = [int(x) for x in ip.split(".")]
    except ValueError:
        return False
    if octets[0] == 100 and 64 <= octets[1] <= 127:
        return True
    return False


def _is_private(ip: str | None) -> bool:
    if not ip:
        return True
    try:
        octets = [int(x) for x in ip.split(".")]
    except ValueError:
        return False
    a, b = octets[0], octets[1]
    if a == 10:
        return True
    if a == 192 and b == 168:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    if a == 127:
        return True
    if a == 100 and 64 <= b <= 127:
        return True
    return False


def detect_network() -> NetworkInfo:
    local_ip, iface = detect_local_ipv4()
    gateway = detect_gateway()
    public_v4, public_v6 = detect_public_ip()
    notes: list[str] = []

    behind_nat = None
    if local_ip and public_v4:
        behind_nat = local_ip != public_v4
        if behind_nat:
            notes.append(
                "This machine's local IP is not the public IP. "
                "It is behind NAT. Router port forwarding is required "
                f"for TCP 25, 80, and 443 to {local_ip}."
            )
    elif local_ip and _is_private(local_ip) and not public_v4:
        behind_nat = True
        notes.append("Local address is private and the public IP could not be detected.")
    elif local_ip and public_v4 and local_ip == public_v4:
        behind_nat = False
        notes.append("Local IP matches public IP. This host appears directly on the internet.")

    possibly_cgnat = _is_cgnat(public_v4) or _is_cgnat(local_ip)
    if possibly_cgnat:
        notes.append(
            "Address is in 100.64.0.0/10 (CGNAT). Inbound connections usually "
            "cannot be forwarded by your router. A VPS or a provider that gives "
            "you a real public IP is required to receive mail."
        )

    warning = None
    if behind_nat:
        warning = (
            "Your public IP must be reachable from the internet. "
            "If this machine is behind a router, port forwarding may be required. "
            "MailGate will not modify your router automatically."
        )

    return NetworkInfo(
        local_ipv4=local_ip,
        public_ipv4=public_v4,
        public_ipv6=public_v6,
        interface=iface or os.environ.get("MAILGATE_IFACE"),
        gateway=gateway,
        behind_nat=behind_nat,
        possibly_cgnat=possibly_cgnat,
        possibly_dynamic=bool(behind_nat and not possibly_cgnat),
        warning=warning,
        notes=notes,
    )


def port_listening(port: int, host: str = "0.0.0.0") -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.4)
        # bind check: if something is listening, connect to localhost
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        return result == 0
    except OSError:
        return False


def check_ports() -> list[dict[str, Any]]:
    ports = [
        (25, "SMTP"),
        (80, "HTTP"),
        (443, "HTTPS"),
        (587, "Submission"),
        (465, "SMTPS"),
    ]
    rows = []
    for port, label in ports:
        listening = port_listening(port)
        rows.append(
            {
                "port": port,
                "label": label,
                "listening": listening,
                "reachable_from_internet": None,
                "note": (
                    "Listening locally. Internet reachability is a separate check — "
                    "ISP blocks, NAT, and CGNAT can still hide this port."
                    if listening
                    else "Nothing is listening on this port on localhost."
                ),
            }
        )
    return rows


def internet_ok() -> bool:
    v4, _ = detect_public_ip()
    return bool(v4)
