"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api, isApiError } from "@/lib/api";

type Settings = {
  server: { hostname: string };
  smtp: { max_message_size: string; enable_ipv6: boolean };
  logging: { retain_events_days: number };
  spam: { rspamd_enabled: boolean };
};

export default function SettingsPage() {
  const [hostname, setHostname] = useState("");
  const [size, setSize] = useState("25MB");
  const [days, setDays] = useState(30);
  const [rspamd, setRspamd] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api<Settings>("/api/settings").then((s) => {
      setHostname(s.server.hostname);
      setSize(s.smtp.max_message_size);
      setDays(s.logging.retain_events_days);
      setRspamd(s.spam.rspamd_enabled);
    });
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    try {
      await api("/api/settings", {
        method: "PUT",
        body: JSON.stringify({
          hostname,
          max_message_size: size,
          retain_events_days: days,
          rspamd_enabled: rspamd,
        }),
      });
      setMessage("Saved. Postfix was reloaded if this host has permission.");
    } catch (err) {
      setMessage(isApiError(err) ? err.detail : "Save failed");
    }
  }

  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-semibold">Settings</h1>
      <div className="mb-6 flex flex-wrap gap-3">
        <Link className="btn-ghost" href="/settings/smtp/">
          SMTP
        </Link>
        <Link className="btn-ghost" href="/settings/network/">
          Network
        </Link>
        <Link className="btn-ghost" href="/settings/security/">
          Security
        </Link>
      </div>
      <form onSubmit={onSubmit} className="panel max-w-xl space-y-4 p-6">
        <div>
          <label className="label">Mail hostname</label>
          <input className="input" value={hostname} onChange={(e) => setHostname(e.target.value)} />
        </div>
        <div>
          <label className="label">Max message size</label>
          <input className="input" value={size} onChange={(e) => setSize(e.target.value)} />
        </div>
        <div>
          <label className="label">Log retention (days)</label>
          <input
            className="input"
            type="number"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          />
          <p className="mt-1 text-xs text-mist-500">Message bodies are not stored. Only metadata is kept.</p>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={rspamd} onChange={(e) => setRspamd(e.target.checked)} />
          Enable Rspamd integration (optional)
        </label>
        {message && <p className="text-sm text-teal">{message}</p>}
        <button className="btn-primary">Save</button>
      </form>
    </Shell>
  );
}
