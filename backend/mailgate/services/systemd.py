"""Control only MailGate-related systemd units. No shell interpolation."""

from __future__ import annotations

import shutil
import subprocess

from mailgate.security import safe_service_name

MAILGATE_UNITS = (
    "mailgate-api",
    "mailgate-worker",
    "postfix",
    "caddy",
    "postgresql",
    "rspamd",
)

# Units MailGate is allowed to start/stop. PostgreSQL is listed for status
# only — stopping it blindly would break other software on the machine.
CONTROLLED_UNITS = ("mailgate-api", "mailgate-worker")
OPTIONAL_CONTROLLED = ("postfix", "caddy", "rspamd")


def _systemctl(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    binary = shutil.which("systemctl")
    if not binary:
        raise FileNotFoundError("systemctl not found")
    cmd = [binary, *args]
    import os

    if args and args[0] in {"start", "stop", "restart", "reload"} and hasattr(os, "geteuid") and os.geteuid() != 0:
        sudo = shutil.which("sudo")
        if sudo:
            cmd = [sudo, "-n", "--", *cmd]
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def unit_status(name: str) -> dict:
    unit = safe_service_name(name)
    if not shutil.which("systemctl"):
        return {
            "name": unit,
            "active": "unknown",
            "enabled": "unknown",
            "running": False,
            "detail": "systemctl not available on this host",
        }
    show = _systemctl(
        [
            "show",
            f"{unit}.service",
            "--property=ActiveState,SubState,UnitFileState,Description,MainPID",
            "--no-page",
        ]
    )
    props = {}
    for line in show.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            props[key] = value
    active = props.get("ActiveState", "unknown")
    return {
        "name": unit,
        "active": active,
        "sub": props.get("SubState"),
        "enabled": props.get("UnitFileState"),
        "running": active == "active",
        "description": props.get("Description"),
        "pid": props.get("MainPID"),
        "detail": show.stderr.strip() or None,
    }


def list_units() -> list[dict]:
    return [unit_status(name) for name in MAILGATE_UNITS]


def control(name: str, action: str, allow_optional: bool = False) -> dict:
    unit = safe_service_name(name)
    if action not in {"start", "stop", "restart", "reload", "enable", "disable"}:
        raise ValueError("Invalid action")
    allowed = set(CONTROLLED_UNITS)
    if allow_optional:
        allowed.update(OPTIONAL_CONTROLLED)
    if unit not in allowed and action in {"start", "stop", "restart"}:
        if unit == "postgresql":
            raise ValueError("Refusing to start/stop PostgreSQL from MailGate — manage it separately")
        raise ValueError(f"Refusing to {action} {unit}")
    result = _systemctl([action, f"{unit}.service"])
    return {
        "name": unit,
        "action": action,
        "ok": result.returncode == 0,
        "output": (result.stdout + result.stderr).strip(),
        "status": unit_status(unit),
    }
