# Install

Safer recommended method:

```bash
git clone https://github.com/rajacharya987/smtp.git
cd smtp
sudo ./install.sh
```

A `curl | bash` one-liner is **not** the recommended path.

## What the installer does

1. Detects the OS (`/etc/os-release`)
2. Requires root
3. On Arch, runs a **full** `pacman -Syu` then installs postfix, postgresql, caddy, python, nodejs, nftables (never a partial `-Sy`)
4. Creates the `mailgate` system user
5. Creates `/etc/mailgate`, `/var/lib/mailgate`, `/var/log/mailgate`
6. Initializes PostgreSQL and a `mailgate` role (password in `/etc/mailgate/secrets/`)
7. Installs the FastAPI app into `/usr/lib/mailgate/venv`
8. Builds the Next.js dashboard into `/usr/share/mailgate/web`
9. Writes a Postfix managed snippet (not an open relay)
10. Installs systemd units `mailgate-api` and `mailgate-worker`
11. Writes an nftables **suggestion** (not loaded automatically)
12. Installs a tight sudoers file so the API can reload Postfix without a root shell

## After install

```bash
sudo mailgate setup
sudo mailgate doctor
```

Install the Caddyfile once DNS for the mail hostname exists:

```bash
sed 's/MAIL_HOSTNAME/mail.example.com/' /usr/lib/mailgate/caddy/Caddyfile.template \
  > /etc/caddy/Caddyfile
systemctl enable --now caddy
```

Caddy obtains and renews the certificate for `mail.example.com`.

## Ports

| Port | Role |
| --- | --- |
| 25 | SMTP receive (Postfix) |
| 80 | HTTP / ACME |
| 443 | HTTPS dashboard |
| 587 / 465 | Optional, closed by default |

Never expose 5432 (PostgreSQL) or 8000 (API).

## Uninstall

```bash
sudo mailgate uninstall
```

Add `--purge` to also delete `/etc/mailgate` and `/var/lib/mailgate`.
Postfix, PostgreSQL, and Caddy packages stay installed.
