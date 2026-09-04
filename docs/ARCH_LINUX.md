# Arch Linux

Arch is the primary target.

## Packages

```bash
sudo pacman -S postfix postgresql caddy python python-pip nodejs npm nftables git
```

The installer runs this for you.

## PostgreSQL on Arch

```bash
sudo -u postgres initdb -D /var/lib/postgres/data
sudo systemctl enable --now postgresql
```

MailGate creates the `mailgate` role and database.

## Postfix

`postfix.service` must be enabled so mail survives reboot:

```bash
sudo systemctl enable --now postfix
```

## nftables

Suggested ruleset: `/etc/mailgate/nftables.nft`

```bash
sudo nft -f /etc/mailgate/nftables.nft
```

Review it first. Policy is drop-inbound except 22/25/80/443. Loading this over
SSH without port 22 allowed will lock you out.

## Reboot recovery

After `sudo reboot`, `mailgate status` should show:

```text
Postfix          ONLINE
MailGate API     ONLINE
Worker           ONLINE
Caddy            ONLINE
Database         ONLINE
```

Units are `enabled` by the installer so systemd starts them.

## Laptop caveats

A laptop on home internet may have:

- Dynamic IP
- ISP port 25 blocks
- CGNAT (`100.64.0.0/10`)
- Router NAT
- Sleep / lid close
- Changing Wi-Fi
- Unreliable uptime

MailGate will warn. It will not pretend the host is internet-ready.
