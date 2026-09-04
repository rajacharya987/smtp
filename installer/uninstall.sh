#!/usr/bin/env bash
set -euo pipefail
if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root" >&2
  exit 1
fi
systemctl disable --now mailgate-api.service mailgate-worker.service 2>/dev/null || true
rm -f /etc/systemd/system/mailgate-api.service /etc/systemd/system/mailgate-worker.service
systemctl daemon-reload
rm -f /usr/bin/mailgate /etc/sudoers.d/mailgate
rm -rf /usr/lib/mailgate /usr/share/mailgate
if [[ "${1:-}" == "--purge" ]]; then
  rm -rf /etc/mailgate /var/lib/mailgate /var/log/mailgate
fi
echo "MailGate removed. Postfix, PostgreSQL, and Caddy packages were left installed."
