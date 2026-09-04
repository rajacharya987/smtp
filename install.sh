#!/usr/bin/env bash
# MailGate installer. Primary target: Arch Linux. Also attempts Debian/Ubuntu/Fedora.
# Recommended:
#   git clone https://github.com/rajacharya987/smtp.git
#   cd smtp
#   sudo ./install.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${MAILGATE_PREFIX:-/usr/lib/mailgate}"
WEB_ROOT="${MAILGATE_WEB_ROOT:-/usr/share/mailgate/web}"
ETC="${MAILGATE_ETC:-/etc/mailgate}"
DATA="${MAILGATE_DATA:-/var/lib/mailgate}"
LOG="${MAILGATE_LOG:-/var/log/mailgate}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo ./install.sh" >&2
  exit 1
fi

if [[ ! -f /etc/os-release ]]; then
  echo "Cannot detect OS (missing /etc/os-release)" >&2
  exit 1
fi
# shellcheck disable=SC1091
. /etc/os-release

echo "╔══════════════════════════════════╗"
echo "║          MAILGATE INSTALL        ║"
echo "╚══════════════════════════════════╝"
echo
echo "OS: ${PRETTY_NAME:-$ID}"
echo

python_works() {
  python3 -c 'import math, venv' >/dev/null 2>&1
}

# Repo python 3.14.7 was built against glibc 2.44. This host may still be on
# glibc 2.43 (lib32-glibc pins it). Do NOT upgrade glibc or the desktop.
# Roll python back to 3.14.6, which was published before glibc 2.44.
ARCH_PYTHON_ROLLBACK="https://archive.archlinux.org/packages/p/python/python-3.14.6-1-x86_64.pkg.tar.zst"

repair_python_no_sysupgrade() {
  echo
  echo "Python is broken against this glibc. Not upgrading glibc or the desktop."
  echo "Restoring an older python package instead."
  echo

  local cache=/var/cache/pacman/pkg
  local pkg=""
  local f

  if [[ -d "$cache" ]]; then
    for f in "$cache"/python-3.14.6-*.pkg.tar.zst "$cache"/python-3.13.*.pkg.tar.zst "$cache"/python-3.12.*.pkg.tar.zst; do
      [[ -f "$f" ]] || continue
      [[ "$(basename "$f")" == python-3.14.7-* ]] && continue
      pkg="$f"
      break
    done
  fi

  if [[ -n "$pkg" ]]; then
    echo "Installing from cache: $pkg"
    pacman -U --noconfirm "$pkg" || pacman -U --noconfirm --overwrite='*' "$pkg"
  else
    echo "No older python in cache. Downloading python-3.14.6-1 from the Arch Linux Archive."
    pacman -U --noconfirm "$ARCH_PYTHON_ROLLBACK" \
      || pacman -U --noconfirm --overwrite='*' "$ARCH_PYTHON_ROLLBACK"
  fi
}

install_arch() {
  echo "Installing MailGate packages only. Will not upgrade glibc, python, or the desktop."
  pacman -S --needed --noconfirm \
    postfix postgresql caddy nodejs npm nftables git gcc rsync openssl \
    || pacman -S --needed --noconfirm postfix postgresql caddy nodejs npm nftables git rsync

  if python_works; then
    echo "Python is usable: $(python3 --version 2>&1)"
    return 0
  fi

  repair_python_no_sysupgrade
}

check_python() {
  local err
  if python_works; then
    echo "Python: $(python3 --version 2>&1)"
    return 0
  fi
  err="$(python3 -c 'import math, venv' 2>&1 || true)"
  echo
  echo "Python is not usable on this host:"
  echo "  $err"
  echo
  echo "Do not upgrade glibc or run pacman -Syu."
  echo "Roll python back (one package, not the desktop):"
  echo "  sudo pacman -U --noconfirm $ARCH_PYTHON_ROLLBACK"
  echo "  python3 -c 'import math'"
  echo "  sudo ./install.sh"
  echo
  echo "Or from pacman cache if you still have the previous package:"
  echo "  ls /var/cache/pacman/pkg/python-3*.pkg.tar.zst"
  echo "  sudo pacman -U /var/cache/pacman/pkg/python-3.14.6-1-x86_64.pkg.tar.zst"
  exit 1
}

install_debian() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y postfix postgresql caddy python3 python3-venv python3-pip \
    nodejs npm nftables git sudo
}

install_fedora() {
  dnf install -y postfix postgresql-server caddy python3 python3-pip python3-virtualenv \
    nodejs npm nftables git
}

case "${ID}" in
  arch) install_arch ;;
  debian|ubuntu) install_debian ;;
  fedora) install_fedora ;;
  *)
    echo "Unsupported ID=${ID}. Install postfix postgresql caddy python nodejs npm nftables, then re-run."
    echo "Continuing with whatever is already installed..."
    ;;
esac

check_python

id mailgate >/dev/null 2>&1 || useradd --system --home "$DATA" --shell /usr/bin/nologin mailgate
getent group postfix >/dev/null 2>&1 && usermod -aG postfix mailgate || true
getent group systemd-journal >/dev/null 2>&1 && usermod -aG systemd-journal mailgate || true

install -d -m 0755 "$PREFIX" "$WEB_ROOT" /usr/lib/mailgate/bin
install -d -m 0750 -o mailgate -g mailgate "$ETC" "$ETC/secrets" "$ETC/secrets/dkim" "$ETC/postfix" "$DATA" "$LOG" "$DATA/backups"

# Copy application tree (exclude VCS and local junk)
rsync -a --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude 'frontend/.next' \
  --exclude 'frontend/out' \
  --exclude '.venv' \
  --exclude 'backend/.venv' \
  --exclude '__pycache__' \
  "$ROOT/" "$PREFIX/" 2>/dev/null || {
    mkdir -p "$PREFIX"
    cp -a "$ROOT/." "$PREFIX/"
  }

install -m 0755 "$ROOT/installer/helpers/mailgate-apply-postfix" /usr/lib/mailgate/bin/mailgate-apply-postfix
install -m 0755 "$ROOT/installer/helpers/mailgate-queue" /usr/lib/mailgate/bin/mailgate-queue
install -m 0440 "$ROOT/installer/sudoers.mailgate" /etc/sudoers.d/mailgate
visudo -cf /etc/sudoers.d/mailgate >/dev/null

system_python_ok_for_venv() {
  python3 -c 'import math, venv, pyexpat, ssl, hashlib' >/dev/null 2>&1
}

install_standalone_python_venv() {
  local uvdir="$PREFIX/uv"
  mkdir -p "$uvdir" "$PREFIX/cpython"
  if [[ ! -x "$uvdir/uv" ]]; then
    echo "Downloading uv (standalone Python installer)..."
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$uvdir" UV_NO_MODIFY_PATH=1 sh
  fi
  export UV_PYTHON_INSTALL_DIR="$PREFIX/cpython"
  "$uvdir/uv" python install 3.13
  "$uvdir/uv" venv "$PREFIX/venv" --python 3.13 --python-preference only-managed
}

echo "Creating MailGate virtualenv..."
rm -rf "$PREFIX/venv"
if system_python_ok_for_venv; then
  echo "Using system Python $(python3 --version 2>&1)"
  if command -v virtualenv >/dev/null 2>&1; then
    virtualenv "$PREFIX/venv" || python3 -m venv --without-pip "$PREFIX/venv"
  else
    python3 -m venv --without-pip "$PREFIX/venv"
  fi
  if [[ ! -x "$PREFIX/venv/bin/pip" && ! -x "$PREFIX/venv/bin/pip3" ]]; then
    curl -fsSL https://bootstrap.pypa.io/get-pip.py | "$PREFIX/venv/bin/python"
  fi
else
  echo "System Python cannot import pyexpat (libexpat mismatch)."
  echo "Not upgrading expat/glibc. Installing a standalone CPython for MailGate only."
  install_standalone_python_venv
fi
"$PREFIX/venv/bin/python" -m pip install --upgrade pip
"$PREFIX/venv/bin/python" -m pip install "$PREFIX/backend"
ln -sfn "$PREFIX/venv/bin/mailgate" /usr/bin/mailgate

# Frontend
if command -v npm >/dev/null 2>&1; then
  (cd "$PREFIX/frontend" && npm install && npm run build)
  if [[ -d "$PREFIX/frontend/out" ]]; then
    rm -rf "$WEB_ROOT"
    mkdir -p "$WEB_ROOT"
    cp -a "$PREFIX/frontend/out/." "$WEB_ROOT/"
  fi
else
  echo "npm not found — dashboard static files were not built."
fi

# Secrets
if [[ ! -f "$ETC/secrets/db_password" ]]; then
  umask 077
  openssl rand -base64 24 | tr -d '\n' > "$ETC/secrets/db_password"
  chmod 600 "$ETC/secrets/db_password"
  chown mailgate:mailgate "$ETC/secrets/db_password"
fi
DB_PASS="$(cat "$ETC/secrets/db_password")"

if [[ ! -f "$ETC/secrets/jwt_secret" ]]; then
  umask 077
  openssl rand -base64 48 | tr -d '\n' > "$ETC/secrets/jwt_secret"
  chmod 600 "$ETC/secrets/jwt_secret"
  chown mailgate:mailgate "$ETC/secrets/jwt_secret"
fi

# PostgreSQL
init_postgres() {
  if [[ "$ID" == "arch" ]]; then
    if [[ ! -d /var/lib/postgres/data ]] || [[ -z "$(ls -A /var/lib/postgres/data 2>/dev/null || true)" ]]; then
      sudo -u postgres initdb -D /var/lib/postgres/data >/dev/null
    fi
  fi
  if [[ "$ID" == "fedora" ]] && [[ ! -d /var/lib/pgsql/data/base ]]; then
    postgresql-setup --initdb || true
  fi
  systemctl enable --now postgresql 2>/dev/null || systemctl enable --now postgresql.service || true
  sleep 1
  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='mailgate'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE USER mailgate WITH PASSWORD '${DB_PASS}';"
  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='mailgate'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE DATABASE mailgate OWNER mailgate;"
  sudo -u postgres psql -c "ALTER USER mailgate WITH PASSWORD '${DB_PASS}';"
}

if command -v psql >/dev/null 2>&1; then
  init_postgres || echo "PostgreSQL init skipped/failed — SQLite can be used as a fallback."
  DB_URL="postgresql://mailgate:${DB_PASS}@127.0.0.1:5432/mailgate"
else
  DB_URL="sqlite:///${DATA}/mailgate.db"
fi

if [[ ! -f "$ETC/config.yml" ]]; then
  sed "s|postgresql://mailgate:CHANGE_ME@127.0.0.1:5432/mailgate|${DB_URL}|" \
    "$ROOT/config.example.yml" > "$ETC/config.yml"
  chown mailgate:mailgate "$ETC/config.yml"
  chmod 640 "$ETC/config.yml"
fi

# Postfix baseline
if [[ -f /etc/postfix/main.cf ]]; then
  if ! grep -q "BEGIN MAILGATE MANAGED" /etc/postfix/main.cf; then
    cat "$ROOT/postfix/main.cf.snippet" >> /etc/postfix/main.cf
  fi
else
  install -m 644 "$ROOT/postfix/main.cf.snippet" /etc/postfix/main.cf
fi
touch "$ETC/postfix/virtual" "$ETC/postfix/virtual_domains"
chown mailgate:mailgate "$ETC/postfix/virtual" "$ETC/postfix/virtual_domains"
postmap "$ETC/postfix/virtual" || true
postmap "$ETC/postfix/virtual_domains" || true
systemctl enable postfix
systemctl restart postfix || true

# Caddy
if [[ -d /etc/caddy ]]; then
  if [[ ! -f /etc/caddy/Caddyfile ]] || ! grep -q "mailgate" /etc/caddy/Caddyfile 2>/dev/null; then
    echo "MailGate Caddy template is in $PREFIX/caddy/Caddyfile.template"
    echo "Replace MAIL_HOSTNAME and install it after DNS exists, e.g.:"
    echo "  sed 's/MAIL_HOSTNAME/mail.example.com/' $PREFIX/caddy/Caddyfile.template > /etc/caddy/Caddyfile"
    echo "  systemctl enable --now caddy"
  fi
fi
systemctl enable caddy 2>/dev/null || true

# systemd units
install -m 644 "$ROOT/systemd/mailgate-api.service" /etc/systemd/system/mailgate-api.service
install -m 644 "$ROOT/systemd/mailgate-worker.service" /etc/systemd/system/mailgate-worker.service
systemctl daemon-reload
systemctl enable mailgate-api.service mailgate-worker.service
systemctl restart mailgate-api.service mailgate-worker.service || true

install -m 644 "$ROOT/installer/nftables.nft" "$ETC/nftables.nft"
echo
echo "Firewall ruleset written to $ETC/nftables.nft (not loaded automatically)."
echo "Review, then: nft -f $ETC/nftables.nft"
echo "This would drop inbound traffic except 22/25/80/443. Do not load it over SSH without 22 allowed."
echo

chown -R mailgate:mailgate "$ETC" "$DATA" "$LOG"
chmod 750 "$ETC/secrets"

echo
echo "Installed."
echo
echo "Next:"
echo "  sudo mailgate setup"
echo "  sudo mailgate doctor"
echo
echo "Dashboard is served by Caddy on https://<mail hostname> after you install the Caddyfile."
echo "The API listens on 127.0.0.1:8000 only."
echo
echo "Inbound SMTP uses TCP 25. Some residential ISPs block it. DNS cannot bypass that."
echo "If this machine is behind NAT, forward 25/80/443 to the local IP."
echo "MailGate will not modify your router."
echo
