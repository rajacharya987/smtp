# Security

This host is a public mail server. Treat every SMTP client as untrusted.

## Open relay

Automated tests fail the suite if arbitrary relay is possible.

Policy module: `mailgate.policy.decide_recipient`.

Postfix lock: empty `relay_domains`, loopback `mynetworks`,
`reject_unauth_destination`.

## Authentication

- Argon2 password hashes
- No default password
- Strong password required at setup
- HttpOnly + SameSite=Lax cookies
- HTTPS-only cookies in production
- CSRF token on mutations
- Origin check
- Login throttling
- API rate limit

## Least privilege

- API binds `127.0.0.1:8000`
- PostgreSQL binds localhost
- systemd hardening on `mailgate-api.service`
- sudoers allows only named helpers, not a shell

## Firewall

Expose 22 (optional), 25, 80, 443.

Never expose:

- 5432 PostgreSQL
- 8000 MailGate API
- DKIM private keys
- `/etc/mailgate/secrets`

## Injection

- Parameterized SQL (SQLAlchemy)
- Postfix maps are data files, not shell strings
- Queue IDs must be alphanumeric
- Service names are an allow-list

## Privacy

Default: do not store message bodies. Logs keep message-id, envelope,
size, status, and the delivery response. Retention is configurable.
