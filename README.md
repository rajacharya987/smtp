# MailGate

Self-hosted SMTP receiving and email forwarding for a domain you own.

MailGate does **not** implement SMTP itself. Postfix speaks SMTP, queues mail, and
forwards it. MailGate owns configuration, policy, DNS guidance, logs, and the
dashboard.

```text
Internet
   ↓
MX: mail.example.com
   ↓
Public IP
   ↓
Arch Linux
   ↓
Postfix :25
   ↓
MailGate forwarding rules
   ↓
Gmail / Outlook / other mailbox
```

Primary target: **Arch Linux**. Debian, Ubuntu, and Fedora are best-effort.

This repository is meant to be cloned onto the Arch machine. Do not treat a
Windows workstation as the mail host.

## What it does

- Receive mail for your domain on port 25
- Forward aliases such as `hello@example.com` → `mygmail@gmail.com`
- One-to-many destinations
- Optional catch-all (spam warning included)
- Web dashboard (Next.js) behind Caddy HTTPS
- CLI: `setup`, `start`, `stop`, `status`, `doctor`, `dns`, `backup`
- Open-relay protection (mandatory)
- DNS instructions and live checks for A / MX / PTR / SPF / DKIM / DMARC
- Queue, logs (metadata only — bodies are not stored)

## What it will not do

- It will not assume public IP equals local IP
- It will not assume port 25 is reachable
- It will not rewrite your router
- It will not set PTR / reverse DNS (your ISP or VPS does that)
- It will not bypass an ISP that blocks inbound port 25
- It will not run as an open relay
- It will not ship a default admin password
- It will not permanently store message bodies

## Install (Arch)

```bash
git clone https://github.com/rajacharya987/smtp.git
cd smtp
sudo ./install.sh
sudo mailgate setup
sudo mailgate doctor
```

The installer upgrades **glibc** plus MailGate packages. It does not full-upgrade
the desktop. If Python is broken (`GLIBC_2.xx not found`):

```bash
sudo pacman -Sy
sudo pacman -S glibc
git pull
sudo ./install.sh
```

Do not `chmod 777` the tree.

Then point DNS at this machine and open `https://mail.example.com`.

A domain stays **disabled until A and MX verify**. That is intentional.

## Example forwarder

```text
hello@example.com
        ↓
mygmail@gmail.com
```

Create it in **Forwarders** after the domain verifies.

## Architecture

```text
Internet
   ├── :25  ──────► Postfix
   ├── :80  ──────► Caddy (ACME)
   └── :443 ──────► Caddy
                      ├── /api/*  → 127.0.0.1:8000 (FastAPI)
                      └── /       → static Next.js dashboard
```

PostgreSQL and the API are localhost-only.

## Documentation

| File | Topic |
| --- | --- |
| [docs/INSTALL.md](docs/INSTALL.md) | Installer details |
| [docs/ARCH_LINUX.md](docs/ARCH_LINUX.md) | Arch-specific notes |
| [docs/DNS.md](docs/DNS.md) | MX, A, SPF, DKIM, DMARC, PTR |
| [docs/SMTP.md](docs/SMTP.md) | Postfix, forwarding, queues |
| [docs/SECURITY.md](docs/SECURITY.md) | Relay lock, auth, firewall |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Port 25, NAT, CGNAT |
| [docs/BACKUP.md](docs/BACKUP.md) | Backup and restore |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local development |

## CLI

```bash
mailgate              # interactive menu
mailgate setup
mailgate start
mailgate stop
mailgate restart
mailgate status
mailgate logs
mailgate doctor
mailgate dns
mailgate backup
mailgate restore FILE
mailgate update
mailgate uninstall
```

## License

MIT
