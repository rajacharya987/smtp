"""MailGate command-line interface."""

from __future__ import annotations

import argparse
import getpass
import os
import shutil
import subprocess
import sys
from pathlib import Path

from mailgate import __version__
from mailgate.paths import CONFIG_FILE, ETC_DIR


def _color(enabled: bool, code: str, text: str) -> str:
    if not enabled:
        return text
    return f"\033[{code}m{text}\033[0m"


def _ok(text: str) -> str:
    return f"✓ {text}"


def _warn(text: str) -> str:
    return f"⚠ {text}"


def _fail(text: str) -> str:
    return f"✗ {text}"


def _box(title: str) -> str:
    inner = f"  {title}  "
    line = "═" * len(inner)
    return f"╔{line}╗\n║{inner}║\n╚{line}╝"


def _need_root(cmd: str) -> None:
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        print(f"This command needs root. Try: sudo mailgate {cmd}", file=sys.stderr)
        raise SystemExit(1)


def _load_app():
    from mailgate.config import load_config
    from mailgate.db import init_db

    init_db()
    return load_config()


def cmd_menu(_args) -> int:
    while True:
        print()
        print(_box("MAILGATE SETUP"))
        print()
        print("1. Check system")
        print("2. Check network")
        print("3. Detect public IP")
        print("4. Configure firewall")
        print("5. Configure SMTP")
        print("6. Configure domain")
        print("7. Start services")
        print("8. Open dashboard")
        print("9. View status")
        print("0. Exit")
        print()
        choice = input("Select: ").strip()
        mapping = {
            "1": lambda: cmd_doctor(argparse.Namespace()),
            "2": lambda: cmd_network(),
            "3": lambda: cmd_network(),
            "4": lambda: cmd_firewall(),
            "5": lambda: cmd_smtp_hint(),
            "6": lambda: cmd_dns(argparse.Namespace(domain=None)),
            "7": lambda: cmd_start(argparse.Namespace()),
            "8": lambda: cmd_dashboard(),
            "9": lambda: cmd_status(argparse.Namespace()),
            "0": lambda: 0,
        }
        if choice == "0":
            return 0
        action = mapping.get(choice)
        if action is None:
            print("Unknown selection")
            continue
        action()
    return 0


def cmd_network() -> int:
    from mailgate.services.network import check_ports, detect_network

    info = detect_network()
    print()
    print("Network Information")
    print()
    print(f"Local IP:       {info.local_ipv4 or 'unknown'}")
    print(f"Public IPv4:    {info.public_ipv4 or 'unknown'}")
    print(f"Public IPv6:    {info.public_ipv6 or 'unknown'}")
    print(f"Interface:      {info.interface or 'unknown'}")
    print(f"Gateway:        {info.gateway or 'unknown'}")
    print()
    if info.behind_nat:
        print("This machine is behind NAT.")
        print("Your public IP must be reachable from the internet.")
        print("If this machine is behind a router, port forwarding may be required.")
        print("MailGate will not modify your router automatically.")
        print()
        print("Typical forwards:")
        print(f"  TCP 25  → {info.local_ipv4}:25")
        print(f"  TCP 80  → {info.local_ipv4}:80")
        print(f"  TCP 443 → {info.local_ipv4}:443")
    if info.possibly_cgnat:
        print()
        print("CGNAT detected. Inbound SMTP almost certainly will not work here.")
    if info.possibly_dynamic:
        print()
        print("Your public IP may be dynamic.")
        print("For reliable mail hosting, a static public IP is recommended.")
    print()
    print("Port Status (local listen only — not internet reachability)")
    print()
    for row in check_ports():
        mark = "✓ listening" if row["listening"] else "✗ closed"
        print(f"{row['port']:<5} {row['label']:<12} {mark}")
    print()
    print("Inbound SMTP normally uses TCP port 25.")
    print("Some residential ISPs block port 25.")
    print("If inbound port 25 is blocked, this machine cannot directly")
    print("receive mail from the public internet.")
    print("Changing DNS cannot bypass an ISP block.")
    return 0


def cmd_firewall() -> int:
    from mailgate.services.firewall import guidance
    from mailgate.services.network import detect_network

    info = detect_network()
    data = guidance(info.local_ipv4)
    print()
    print("Firewall guidance (nftables)")
    print("Expose only: 22 (optional), 25, 80, 443")
    print("Never expose: PostgreSQL 5432, MailGate API 8000")
    print()
    print("Router port forwarding:")
    for line in data["router_forwarding"]:
        print(f"  {line}")
    print()
    print("Suggested nftables ruleset:")
    print(data["nftables"])
    dest = ETC_DIR / "nftables.nft"
    try:
        ETC_DIR.mkdir(parents=True, exist_ok=True)
        dest.write_text(data["nftables"], encoding="utf-8")
        print(f"Wrote {dest}")
        print("Review, then load with: sudo nft -f /etc/mailgate/nftables.nft")
    except PermissionError:
        print("Could not write /etc/mailgate/nftables.nft (need root)")
    return 0


def cmd_smtp_hint() -> int:
    print()
    print("SMTP is handled by Postfix, not by a custom Python SMTP stack.")
    print("MailGate generates maps under /etc/mailgate/postfix/ and reloads Postfix.")
    print("Open relay protection:")
    print("  mynetworks = loopback only")
    print("  relay_domains = empty")
    print("  smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination")
    print("  virtual_alias_domains = only verified MailGate domains")
    print()
    print("A RCPT TO of victim@gmail.com from the internet is rejected")
    print("unless gmail.com is a local MailGate domain — which it is not.")
    return 0


def cmd_dashboard() -> int:
    from mailgate.config import load_config

    cfg = load_config()
    print()
    print(f"Dashboard: https://{cfg.server.hostname}")
    print("The API listens on 127.0.0.1 only. Caddy terminates HTTPS.")
    return 0


def cmd_setup(_args) -> int:
    _need_root("setup")
    print()
    print("Welcome to MailGate")
    print()
    print("This computer will be used as a public mail server.")
    print()
    print("[1] Continue")
    print("[2] Exit")
    choice = input("Select: ").strip() or "1"
    if choice != "1":
        return 0

    print()
    print("Checking system...")
    print()
    from mailgate.services.health import os_info, package_presence

    os_ = os_info()
    print(_ok("Linux detected") if os_["linux"] else _fail("Linux not detected"))
    print(_ok("Arch Linux detected") if os_["arch_linux"] else _warn(f"{os_['distro']} detected"))
    root = hasattr(os, "geteuid") and os.geteuid() == 0
    print(_ok("Root access available") if root else _fail("Root access missing"))
    pkgs = package_presence()
    missing = [name for name, present in pkgs.items() if not present and name in {"postfix", "python", "caddy"}]
    for name, present in pkgs.items():
        print(_ok(f"{name} detected") if present else _warn(f"{name} missing"))
    if missing:
        print()
        print("The following packages are required:")
        print()
        for name in missing:
            print(name)
        print()
        ans = input("Install them now? [Y/n] ").strip().lower() or "y"
        if ans == "y":
            installer = Path(__file__).resolve().parents[2] / "install.sh"
            if installer.exists():
                subprocess.call(["bash", str(installer)])
            else:
                print("install.sh not found. Install postfix postgresql caddy python nodejs nftables manually.")

    cmd_network()

    hostname = input("Mail hostname [mail.example.com]: ").strip()
    domain = input("Domain [example.com]: ").strip()
    if not hostname or not domain:
        print("Hostname and domain are required")
        return 1
    username = input("Administrator username [admin]: ").strip() or "admin"
    while True:
        password = getpass.getpass("Administrator password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match")
            continue
        from mailgate.security import validate_password_strength

        errors = validate_password_strength(password)
        if errors:
            for err in errors:
                print(_fail(err))
            continue
        break

    local = input("First alias local part (blank to skip) [hello]: ").strip()
    dest = input("Forward to (blank to skip): ").strip()

    from mailgate.config import dump_config, load_config, reload_config
    from mailgate.db import get_session_factory, init_db
    from mailgate.models import Alias, Destination, Domain, User
    from mailgate.security import hash_password
    from mailgate.validate import normalize_domain, normalize_email, normalize_hostname, normalize_local_part

    cfg = load_config()
    cfg.server.hostname = normalize_hostname(hostname)
    dump_config(cfg)
    reload_config()
    init_db()
    session = get_session_factory()()
    try:
        from sqlalchemy import select

        if session.scalar(select(User.id)):
            print("An administrator already exists. Use the dashboard to continue.")
            return 1
        user = User(username=username, password_hash=hash_password(password), is_admin=True)
        session.add(user)
        d = Domain(name=normalize_domain(domain), hostname=cfg.server.hostname, enabled=False, verified=False)
        session.add(d)
        session.flush()
        if local and dest:
            alias = Alias(domain_id=d.id, local_part=normalize_local_part(local), enabled=True)
            session.add(alias)
            session.flush()
            session.add(Destination(alias_id=alias.id, email=normalize_email(dest), enabled=True))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print()
    print("Setup saved. Next:")
    print(f"  1. Create DNS A {hostname} → your public IP")
    print(f"  2. Create DNS MX {domain} → {hostname}")
    print("  3. Run: mailgate dns")
    print("  4. Run: mailgate doctor")
    print(f"  5. Open https://{hostname}")
    print()
    print("The domain stays disabled until A and MX records verify.")
    print("This is intentional — MailGate will not accept mail for unverified domains.")
    return 0


def cmd_start(_args) -> int:
    _need_root("start")
    print("Starting MailGate...")
    print()
    from mailgate.db import init_db
    from mailgate.services.systemd import control

    try:
        init_db()
        print(_ok("Database"))
    except Exception as exc:
        print(_fail(f"Database: {exc}"))
        return 1
    for unit in ("mailgate-api", "mailgate-worker", "postfix", "caddy"):
        try:
            result = control(unit, "start", allow_optional=True)
            print(_ok(unit) if result["ok"] else _fail(f"{unit}: {result['output']}"))
        except Exception as exc:
            print(_warn(f"{unit}: {exc}"))
    print()
    return cmd_status(_args)


def cmd_stop(_args) -> int:
    _need_root("stop")
    from mailgate.services.systemd import control

    print("Stopping MailGate-managed services (API and worker).")
    print("Postfix, Caddy, and PostgreSQL are left running so other mail is not cut off.")
    print("Pass --all to also stop Postfix and Caddy.")
    units = ["mailgate-api", "mailgate-worker"]
    if "--all" in sys.argv:
        units += ["postfix", "caddy"]
    for unit in units:
        try:
            result = control(unit, "stop", allow_optional=True)
            print(_ok(f"stopped {unit}") if result["ok"] else _fail(result["output"]))
        except Exception as exc:
            print(_fail(str(exc)))
    return 0


def cmd_restart(_args) -> int:
    _need_root("restart")
    cmd_stop(_args)
    return cmd_start(_args)


def cmd_status(_args) -> int:
    from mailgate.services.health import collect_status

    status = collect_status()
    print()
    print(f"SMTP:      {status['smtp'].upper()}")
    print(f"Dashboard: {status['dashboard'].upper()}")
    print(f"Hostname:  {status['hostname']}")
    print(f"Public IP: {status['public_ip'] or 'unknown'}")
    print()
    for name, unit in status["services"].items():
        flag = "ONLINE" if unit["running"] else "OFFLINE"
        print(f"{name:<18} {flag}")
    print()
    print(f"Dashboard: https://{status['hostname']}")
    return 0


def cmd_logs(_args) -> int:
    from mailgate.services.logs import read_journal

    for line in read_journal("postfix", 100) + read_journal("mailgate-api", 50):
        print(line)
    return 0


def cmd_doctor(_args) -> int:
    from mailgate.services.health import doctor

    report = doctor()
    print()
    print("MailGate Diagnostics")
    print("────────────────────────────")
    print()
    current = None
    for check in report["checks"]:
        if check["group"] != current:
            current = check["group"]
            print(current)
        mark = {"ok": "✓", "warn": "⚠", "fail": "✗"}.get(check["level"], "•")
        print(f"{mark} {check['name']:<22} {check['message']}")
        if check["group"] != report["checks"][-1]["group"]:
            pass
    print()
    print("Overall:")
    print(report["overall_text"])
    print()
    print(report["port25_warning"])
    print()
    print(report["home_server_warning"])
    return 0 if report["overall"] != "NOT_READY" else 2


def cmd_dns(args) -> int:
    from mailgate.db import get_session_factory, init_db
    from mailgate.models import Domain
    from mailgate.services.dns import recommended_records, verify_domain
    from mailgate.services.network import detect_network
    from sqlalchemy import select

    init_db()
    session = get_session_factory()()
    try:
        q = select(Domain)
        if args.domain:
            q = q.where(Domain.name == args.domain.lower())
        domains = list(session.scalars(q))
        if not domains:
            print("No domains configured")
            return 1
        net = detect_network()
        for domain in domains:
            print()
            print(f"Domain: {domain.name}")
            print(f"Hostname: {domain.hostname}")
            print(f"Public IP: {net.public_ipv4 or 'YOUR_PUBLIC_IP'}")
            print()
            for rec in recommended_records(domain.name, domain.hostname or "", net.public_ipv4, domain.dkim_selector):
                prio = f" {rec.priority}" if rec.priority is not None else ""
                print(f"  {rec.type:<6} {rec.name:<24}{prio} {rec.value}")
            print()
            report = verify_domain(domain)
            domain.verified = report.verified
            if not report.verified:
                domain.enabled = False
            for check in report.checks:
                mark = {"ok": "✓", "warn": "⚠", "fail": "✗", "unknown": "?"}.get(check.status, "?")
                print(f"  {mark} {check.check:<8} {check.message}")
            session.commit()
    finally:
        session.close()
    return 0


def cmd_backup(args) -> int:
    from mailgate.services.backup import create_backup

    path = create_backup(include_secrets=bool(args.secrets))
    print(f"Backup written to {path}")
    return 0


def cmd_restore(args) -> int:
    from mailgate.services.backup import restore_backup

    report = restore_backup(Path(args.archive), include_secrets=bool(args.secrets))
    print("Restored:", ", ".join(report["restored"]) or "(nothing)")
    return 0


def cmd_update(_args) -> int:
    print("Pull the latest tree and re-run install.sh:")
    print("  cd /usr/lib/mailgate")
    print("  sudo git pull")
    print("  sudo ./install.sh")
    return 0


def cmd_uninstall(_args) -> int:
    _need_root("uninstall")
    print("This removes MailGate units and /usr/lib/mailgate.")
    print("Postfix, PostgreSQL, and Caddy packages are left installed.")
    print("Configuration in /etc/mailgate is left in place unless you pass --purge.")
    ans = input("Continue? [y/N] ").strip().lower()
    if ans != "y":
        return 1
    for unit in ("mailgate-api", "mailgate-worker"):
        subprocess.call(["systemctl", "disable", "--now", f"{unit}.service"])
        path = Path(f"/etc/systemd/system/{unit}.service")
        if path.exists():
            path.unlink()
    if "--purge" in sys.argv:
        shutil.rmtree("/etc/mailgate", ignore_errors=True)
        shutil.rmtree("/var/lib/mailgate", ignore_errors=True)
    print("MailGate uninstalled.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mailgate", description="MailGate SMTP forwarding gateway")
    parser.add_argument("--version", action="version", version=f"MailGate {__version__}")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup").set_defaults(func=cmd_setup)
    sub.add_parser("start").set_defaults(func=cmd_start)
    sub.add_parser("stop").set_defaults(func=cmd_stop)
    sub.add_parser("restart").set_defaults(func=cmd_restart)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("logs").set_defaults(func=cmd_logs)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    dns_p = sub.add_parser("dns")
    dns_p.add_argument("domain", nargs="?")
    dns_p.set_defaults(func=cmd_dns)
    sub.add_parser("update").set_defaults(func=cmd_update)
    sub.add_parser("uninstall").set_defaults(func=cmd_uninstall)
    b = sub.add_parser("backup")
    b.add_argument("--secrets", action="store_true")
    b.set_defaults(func=cmd_backup)
    r = sub.add_parser("restore")
    r.add_argument("archive")
    r.add_argument("--secrets", action="store_true")
    r.set_defaults(func=cmd_restore)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return cmd_menu(argparse.Namespace())
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    return args.func(args)
