# DNS

For domain `example.com` and hostname `mail.example.com`:

## Required

```text
Type: A
Name: mail
Value: YOUR_PUBLIC_IP

Type: MX
Name: @
Priority: 10
Target: mail.example.com
```

Replace `YOUR_PUBLIC_IP` with the address `mailgate doctor` prints. Never assume
it equals the LAN address.

## Recommended

SPF (generated from the real hostname, not a canned string):

```text
Type: TXT
Name: @
Value: v=spf1 mx a:mail.example.com ~all
```

DMARC, start conservative:

```text
Type: TXT
Name: _dmarc
Value: v=DMARC1; p=none; rua=mailto:dmarc@example.com
```

DKIM: generate a key in the dashboard **Security** page, then publish the TXT
at `mail._domainkey.example.com`. The private key stays on disk.

## Reverse DNS

PTR is set by the ISP or VPS, not by your DNS panel and not by MailGate.

If `203.0.113.10` should reverse to `mail.example.com`, ask the provider.

## Verification

```bash
mailgate dns
```

or the dashboard **DNS** page.

A domain is not enabled until A and MX match. That is the activation gate.
