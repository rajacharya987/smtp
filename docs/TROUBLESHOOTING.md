# Troubleshooting

## Installer: `GLIBC_2.xx not found` / Python cannot `import math`

Python was upgraded without glibc. That is a partial Arch upgrade.

```bash
sudo pacman -Syu
git pull
sudo ./install.sh
```

MailGate no longer uses `pacman -Sy` (sync without upgrade).

## Port 25 is not reachable

Possible causes:

- ISP blocks SMTP
- Router forwarding missing
- Firewall blocking port 25
- Postfix not running
- Incorrect public IP
- CGNAT (`100.64.0.0/10`)

Changing DNS cannot bypass an ISP block.

```bash
sudo systemctl status postfix
ss -lntp | grep ':25'
sudo mailgate doctor
```

## MX failure

No valid MX record.

```text
MX @ → mail.example.com
```

## DNS mismatch

`mail.example.com` resolves to a different address than this machine's
public IP. Senders will deliver to the wrong host.

## Postfix failure

```bash
sudo systemctl status postfix
sudo journalctl -u postfix
sudo postfix check
```

## Mail accepted but Gmail never gets it

- Check **Mail Queue** for deferred mail
- Gmail may reject forwarded mail on SPF (see SRS in SMTP.md)
- Confirm the alias is enabled and the domain is verified
- Read logs: Accepted → Forwarding → Delivered / Deferred / Failed

## Dashboard TLS

Caddy must be running with the production Caddyfile and the hostname must
resolve to this machine. Port 80 must be reachable for ACME.

## NAT diagram

```text
Internet
   │
   ▼
Router
Public IP
   │
   │ Port 25 / 80 / 443
   ▼
192.168.x.x   (this machine — use the detected local IP)
Arch Linux
```

MailGate never writes router settings.
