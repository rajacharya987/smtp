# Backup and restore

```bash
sudo mailgate backup
sudo mailgate restore /var/lib/mailgate/backups/mailgate-YYYYMMDDThhmmssZ.tar.gz
```

Default archive includes:

- `config.yml`
- Postfix virtual maps
- SQLite file if used
- DKIM **public** keys

Secrets (JWT, DB password, DKIM private keys) are omitted unless:

```bash
sudo mailgate backup --secrets
```

Archives are mode 0600.

Restore does not blindly extract paths outside the staging directory
(path-traversal guard).

After restore:

```bash
sudo mailgate restart
sudo mailgate doctor
```
