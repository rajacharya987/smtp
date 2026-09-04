# Arch Linux

Arch is the primary target.

## Packages

Python 3.14 needs a matching glibc. The installer upgrades **glibc** and the
MailGate packages only. It does **not** run a full `pacman -Syu`, because that
often dies on unrelated desktop conflicts (`geocode-glib`, `akonadi`).

If Python is already broken (`GLIBC_2.xx not found` / `import math`):

```bash
sudo pacman -Sy
sudo pacman -S glibc
python3 -c 'import math'
cd smtp
git pull
sudo ./install.sh
```

If you still want a full desktop upgrade and pacman stops on:

```text
geocode-glib and geocode-glib-common are in conflict
```

```bash
sudo pacman -Rdd geocode-glib-common
sudo pacman -Syu
```

Answer **y** to replace `geocode-glib-2` and `libakonadi`. That conflict is
KDE/GNOME, not MailGate.

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
