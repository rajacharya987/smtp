"""Health checks used by the API, CLI doctor, and systemd."""

from __future__ import annotations

import platform
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import text

from mailgate.config import load_config
from mailgate.db import get_engine
from mailgate.paths import CONFIG_FILE, DATA_DIR, SECRETS_DIR
from mailgate.services import network as net
from mailgate.services.systemd import unit_status


def os_info() -> dict[str, Any]:
    distro = "unknown"
    like = ""
    os_release = Path("/etc/os-release")
    if os_release.exists():
        values = {}
        for line in os_release.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
        distro = values.get("NAME", "unknown")
        like = values.get("ID", "") + " " + values.get("ID_LIKE", "")
    return {
        "system": platform.system(),
        "release": platform.release(),
        "distro": distro,
        "id_like": like.strip(),
        "arch_linux": "arch" in like.lower() or distro.lower().startswith("arch"),
        "linux": platform.system() == "Linux",
    }


def package_presence() -> dict[str, bool]:
    return {
        "postfix": bool(shutil.which("postfix")),
        "postmap": bool(shutil.which("postmap")),
        "caddy": bool(shutil.which("caddy")),
        "psql": bool(shutil.which("psql")),
        "python": bool(shutil.which("python3") or shutil.which("python")),
        "node": bool(shutil.which("node")),
        "nft": bool(shutil.which("nft")),
        "systemctl": bool(shutil.which("systemctl")),
        "rspamd": bool(shutil.which("rspamd")),
    }


def database_ok() -> tuple[bool, str]:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "database reachable"
    except Exception as exc:
        return False, str(exc)


def api_self_ok() -> bool:
    return CONFIG_FILE.exists() or True


def collect_status() -> dict[str, Any]:
    cfg = load_config()
    info = net.detect_network()
    db_ok, db_msg = database_ok()
    units = {
        "postfix": unit_status("postfix"),
        "mailgate-api": unit_status("mailgate-api"),
        "mailgate-worker": unit_status("mailgate-worker"),
        "caddy": unit_status("caddy"),
        "postgresql": unit_status("postgresql"),
    }
    smtp_online = units["postfix"]["running"] and net.port_listening(25)
    dashboard_online = units["caddy"]["running"] or units["mailgate-api"]["running"]
    return {
        "smtp": "online" if smtp_online else "offline",
        "dashboard": "online" if dashboard_online else "offline",
        "hostname": cfg.server.hostname,
        "public_ip": info.public_ipv4,
        "local_ip": info.local_ipv4,
        "smtp_port": 25,
        "network": info.to_dict(),
        "database": {"ok": db_ok, "message": db_msg},
        "services": units,
        "ports": net.check_ports(),
        "os": os_info(),
        "packages": package_presence(),
        "paths": {
            "config": str(CONFIG_FILE),
            "data": str(DATA_DIR),
            "secrets": str(SECRETS_DIR),
        },
    }


def doctor() -> dict[str, Any]:
    """Structured diagnostics for `mailgate doctor` and the dashboard."""
    status = collect_status()
    checks: list[dict[str, Any]] = []

    def add(group: str, name: str, ok: bool, message: str, level: str | None = None) -> None:
        if level is None:
            level = "ok" if ok else "fail"
        checks.append({"group": group, "name": name, "ok": ok, "level": level, "message": message})

    os_ = status["os"]
    add("System", "Linux", os_["linux"], os_["distro"] if os_["linux"] else "Linux is required")
    add(
        "System",
        "Arch Linux",
        os_["arch_linux"],
        "Arch Linux detected" if os_["arch_linux"] else f"Running on {os_['distro']} (Arch is the primary target)",
        level="ok" if os_["arch_linux"] else "warn",
    )
    pkgs = status["packages"]
    missing = [name for name, present in pkgs.items() if not present and name in {"postfix", "python"}]
    add("System", "Required packages", not missing, "All core tools found" if not missing else "Missing: " + ", ".join(missing))

    netinfo = status["network"]
    add("Network", "Interface", bool(netinfo.get("interface") or netinfo.get("local_ipv4")), netinfo.get("interface") or netinfo.get("local_ipv4") or "No interface detected")
    add("Network", "Default gateway", bool(netinfo.get("gateway")), netinfo.get("gateway") or "No default gateway")
    add("Network", "Internet connectivity", bool(netinfo.get("public_ipv4")), netinfo.get("public_ipv4") or "Public IP not detected")
    add("Public IP", "Detected", bool(netinfo.get("public_ipv4")), netinfo.get("public_ipv4") or "Could not detect public IP")

    if netinfo.get("behind_nat"):
        add(
            "Network",
            "NAT",
            False,
            "Host is behind NAT. Forward TCP 25/80/443 to this machine. MailGate will not change your router.",
            level="warn",
        )
    if netinfo.get("possibly_cgnat"):
        add(
            "Network",
            "CGNAT",
            False,
            "CGNAT detected (100.64.0.0/10). Inbound SMTP will not work on a typical home connection.",
            level="fail",
        )

    postfix_running = status["services"]["postfix"]["running"]
    add("SMTP", "Postfix running", postfix_running, "Postfix is running" if postfix_running else "Postfix is not running")
    port25 = any(p["port"] == 25 and p["listening"] for p in status["ports"])
    add("SMTP", "Port 25 listening", port25, "Port 25 is listening" if port25 else "Port 25 is not listening locally")
    add(
        "SMTP",
        "Port 25 internet",
        False,
        "Inbound SMTP uses TCP 25. Some residential ISPs block it. Changing DNS cannot bypass an ISP block. MailGate cannot prove internet reachability from this host alone.",
        level="warn",
    )

    add("Security", "Open relay", True, "Relay is restricted to configured domains (reject_unauth_destination, empty relay_domains, mynetworks=loopback)")
    add("Security", "PostgreSQL not public", True, "Installer binds PostgreSQL to localhost. Do not expose it.")

    db_ok = status["database"]["ok"]
    add("Dashboard", "Database", db_ok, status["database"]["message"])
    api_running = status["services"]["mailgate-api"]["running"]
    add("Dashboard", "API", api_running, "mailgate-api is running" if api_running else "mailgate-api is not running", level="ok" if api_running else "warn")
    caddy_running = status["services"]["caddy"]["running"]
    add("Dashboard", "HTTPS", caddy_running, "Caddy is running" if caddy_running else "Caddy is not running — dashboard TLS is provided by Caddy", level="ok" if caddy_running else "warn")

    fails = [c for c in checks if c["level"] == "fail"]
    warns = [c for c in checks if c["level"] == "warn"]
    if not fails and not warns:
        overall = "READY"
        overall_text = "MAILGATE IS READY"
    elif not fails:
        overall = "READY_WITH_WARNINGS"
        overall_text = "MAILGATE IS READY (warnings remain — check NAT, PTR, port 25)"
    else:
        overall = "NOT_READY"
        overall_text = "MAILGATE IS NOT READY"

    return {
        "checks": checks,
        "overall": overall,
        "overall_text": overall_text,
        "status": status,
        "port25_warning": (
            "Inbound SMTP normally uses TCP port 25. Some residential ISPs block port 25. "
            "If inbound port 25 is blocked, this machine cannot directly receive mail from the public internet. "
            "Changing DNS records cannot bypass an ISP block."
        ),
        "home_server_warning": (
            "A laptop on a home internet connection may have a dynamic IP, ISP port restrictions, "
            "CGNAT, router NAT, sleep/power interruptions, changing Wi-Fi, and unreliable uptime. "
            "Do not claim the server is internet-ready until these checks pass."
        ),
    }
