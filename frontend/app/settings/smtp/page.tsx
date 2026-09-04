"use client";

import { Shell } from "@/components/Shell";

export default function SmtpSettingsPage() {
  return (
    <Shell>
      <h1 className="mb-4 text-3xl font-semibold">SMTP settings</h1>
      <div className="panel max-w-2xl space-y-3 p-6 text-sm text-mist-300">
        <p>Postfix listens on 0.0.0.0:25 (and IPv6 if enabled). MailGate does not implement SMTP itself.</p>
        <p>Open-relay lock:</p>
        <pre className="overflow-auto rounded-lg bg-ink-950 p-3 font-mono text-xs text-mist-100">
{`mynetworks = 127.0.0.0/8 [::1]/128
relay_domains =
smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination
virtual_alias_domains = hash:/etc/mailgate/postfix/virtual_domains
virtual_alias_maps = hash:/etc/mailgate/postfix/virtual`}
        </pre>
        <p>
          Optional submission ports 587/465 are documented but not opened by the default firewall. Enable them only
          if you later add authenticated submission.
        </p>
      </div>
    </Shell>
  );
}
