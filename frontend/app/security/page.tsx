"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api, isApiError } from "@/lib/api";

type Domain = { id: number; name: string; dkim_selector: string; dmarc_policy: string };
type Dkim = { dns_name: string; txt: string | null; selector: string; private_key_present: boolean; note: string };

export default function SecurityPage() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [selected, setSelected] = useState<Domain | null>(null);
  const [dkim, setDkim] = useState<Dkim | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Domain[]>("/api/domains").then((list) => {
      setDomains(list);
      setSelected(list[0] || null);
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    api<Dkim>(`/api/settings/dkim/${selected.name}?selector=${selected.dkim_selector}`).then(setDkim);
  }, [selected]);

  async function generate() {
    if (!selected) return;
    setError(null);
    try {
      setDkim(await api<Dkim>(`/api/settings/dkim/${selected.name}?selector=${selected.dkim_selector}`, { method: "POST" }));
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Failed");
    }
  }

  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-semibold">Security</h1>
      <div className="panel mb-6 p-6">
        <h2 className="mb-2 font-medium">Open relay protection</h2>
        <p className="text-sm text-mist-300">
          MailGate only accepts recipients on verified local domains that match an alias or catch-all.
          An internet sender mailing victim@gmail.com is rejected. Destination mailboxes are where mail is
          forwarded <em>to</em>, never addresses MailGate receives <em>for</em>.
        </p>
      </div>
      <div className="mb-4 max-w-sm">
        <label className="label">Domain</label>
        <select
          className="input"
          value={selected?.name || ""}
          onChange={(e) => setSelected(domains.find((d) => d.name === e.target.value) || null)}
        >
          {domains.map((d) => (
            <option key={d.id}>{d.name}</option>
          ))}
        </select>
      </div>
      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}
      {selected && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="panel p-6">
            <h2 className="mb-2 font-medium">SPF</h2>
            <p className="mb-2 text-sm text-mist-500">TXT @</p>
            <pre className="overflow-auto rounded-lg bg-ink-950 p-3 font-mono text-xs">
              v=spf1 mx a:{selected.name.startsWith("mail.") ? selected.name : `mail.${selected.name}`} ~all
            </pre>
          </div>
          <div className="panel p-6">
            <h2 className="mb-2 font-medium">DMARC</h2>
            <p className="mb-2 text-sm text-mist-500">TXT _dmarc.{selected.name} — default p=none</p>
            <pre className="overflow-auto rounded-lg bg-ink-950 p-3 font-mono text-xs">
              v=DMARC1; p={selected.dmarc_policy}; rua=mailto:dmarc@{selected.name}
            </pre>
          </div>
          <div className="panel p-6 lg:col-span-2">
            <h2 className="mb-2 font-medium">DKIM</h2>
            <p className="mb-3 text-sm text-mist-300">
              Selector: <span className="font-mono">{selected.dkim_selector}</span>. Private keys are never shown.
            </p>
            <button className="btn-primary mb-4" onClick={generate}>
              Generate DKIM key
            </button>
            {dkim && (
              <div className="space-y-2 font-mono text-xs">
                <div>DNS name: {dkim.dns_name}</div>
                <div>Private key on disk: {dkim.private_key_present ? "yes" : "no"}</div>
                {dkim.txt && <pre className="overflow-auto rounded-lg bg-ink-950 p-3">{dkim.txt}</pre>}
                <p className="font-sans text-mist-500">{dkim.note}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </Shell>
  );
}
