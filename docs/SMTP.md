# SMTP

Postfix listens on `0.0.0.0:25` (and IPv6 when enabled).

MailGate generates:

- `/etc/mailgate/postfix/virtual_domains`
- `/etc/mailgate/postfix/virtual`

then runs `postmap` and `postfix reload` through a no-argument helper.
User input never enters a shell.

## Forwarding

Virtual aliases rewrite a local recipient to one or more destinations:

```text
hello@example.com    mygmail@gmail.com
```

One-to-many:

```text
hello@example.com    user1@gmail.com,user2@outlook.com
```

Catch-all:

```text
@example.com         inbox@gmail.com
```

Catch-all attracts spam. The dashboard warns before enabling it.

## Not an open relay

```text
mynetworks = 127.0.0.0/8 [::1]/128
relay_domains =
smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination
```

`RCPT TO:<victim@gmail.com>` from the internet is rejected. Gmail is a
forwarding *destination*, not a domain MailGate receives for.

## Queue

Postfix owns the queue. If Gmail is down, mail defers and retries with
Postfix backoff. The dashboard lists `postqueue` JSON and can retry or
delete a message.

```bash
mailgate logs
```

## TLS

Inbound: `smtpd_tls_security_level = may` (STARTTLS offered).

Dashboard: Caddy terminates HTTPS for `mail.example.com` and renews the
certificate.

## SRS / DKIM on forwards

Forwarding can fail SPF at Gmail because the envelope sender is still the
original author. Sender Rewriting Scheme (postsrsd) and DKIM signing of
forwarded mail are the next hardening step. The MVP ships DKIM key
generation and DNS records; enable postsrsd when you need it.

## Optional Rspamd

```text
Internet → Postfix → Rspamd → forward
```

Toggle in Settings. Not required for the first working forwarder.
