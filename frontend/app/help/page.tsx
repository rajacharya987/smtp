"use client";

import { Shell } from "@/components/Shell";

export default function HelpPage() {
  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-semibold">Help</h1>
      <div className="space-y-4 text-sm text-mist-300">
        <section className="panel p-5">
          <h2 className="mb-2 font-medium text-mist-100">Port 25 is not reachable</h2>
          <ul className="list-disc pl-5">
            <li>ISP blocks SMTP</li>
            <li>Router forwarding missing</li>
            <li>Firewall blocking port 25</li>
            <li>Postfix not running</li>
            <li>Incorrect public IP</li>
          </ul>
          <p className="mt-2">Changing DNS cannot bypass an ISP block.</p>
        </section>
        <section className="panel p-5">
          <h2 className="mb-2 font-medium text-mist-100">MX failure</h2>
          <p>No valid MX record detected. Configure: MX @ → mail.example.com</p>
        </section>
        <section className="panel p-5">
          <h2 className="mb-2 font-medium text-mist-100">DNS mismatch</h2>
          <p>If mail.example.com resolves to a different IP than this machine&apos;s public IP, senders will deliver elsewhere.</p>
        </section>
        <section className="panel p-5">
          <h2 className="mb-2 font-medium text-mist-100">Postfix failure</h2>
          <pre className="mt-2 rounded-lg bg-ink-950 p-3 font-mono text-xs">
{`sudo systemctl status postfix
sudo journalctl -u postfix`}
          </pre>
        </section>
        <section className="panel p-5">
          <h2 className="mb-2 font-medium text-mist-100">Home laptop warning</h2>
          <p>
            Dynamic IP, ISP port restrictions, CGNAT, router NAT, sleep, Wi-Fi changes, and uptime all break inbound
            mail. MailGate will not claim the server is internet-ready until diagnostics pass.
          </p>
        </section>
      </div>
    </Shell>
  );
}
