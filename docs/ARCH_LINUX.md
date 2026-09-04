# Arch Linux

Arch is the primary target.

## Packages

Arch must be fully upgraded. A partial sync (`pacman -Sy` without `-u`) can
install a new Python that needs a newer glibc than you have:

```text
ImportError: /usr/lib/libm.so.6: version `GLIBC_2.44' not found
(required by .../math.cpython-314-...so)
```

The installer now runs `pacman -Syu` (full upgrade + MailGate packages).

If you already hit that error:

```bash
sudo pacman -Syu
cd smtp
git pull
sudo ./install.sh
```

Do **not** `chmod 777` the tree. `install.sh` only needs to be executable:

```bash
chmod 755 install.sh
```

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
