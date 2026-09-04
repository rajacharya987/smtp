"use client";

import { FormEvent, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api, isApiError } from "@/lib/api";

type Domain = { id: number; name: string };
type Forwarder = {
  id: number;
  address: string;
  local_part: string;
  domain_name: string;
  enabled: boolean;
  destinations: { email: string }[];
};

export default function ForwardersPage() {
  const [rows, setRows] = useState<Forwarder[]>([]);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [domain, setDomain] = useState("");
  const [local, setLocal] = useState("");
  const [dest, setDest] = useState("");
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<Forwarder[]>("/api/forwarders").then(setRows);
    api<Domain[]>("/api/domains").then((list) => {
      setDomains(list);
      if (!domain && list[0]) setDomain(list[0].name);
    });
  }

  useEffect(() => {
    load();
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const destinations = dest
        .split(/[, \n]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      await api("/api/forwarders", {
        method: "POST",
        body: JSON.stringify({ domain, local_part: local, destinations }),
      });
      setLocal("");
      setDest("");
      load();
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Failed");
    }
  }

  async function remove(id: number) {
    await api(`/api/forwarders/${id}`, { method: "DELETE" });
    load();
  }

  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-semibold">Forwarding</h1>
      <form onSubmit={onSubmit} className="panel mb-6 grid gap-4 p-5 md:grid-cols-2">
        <div>
          <label className="label">Domain</label>
          <select className="input" value={domain} onChange={(e) => setDomain(e.target.value)}>
            {domains.map((d) => (
              <option key={d.id} value={d.name}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Address</label>
          <input className="input" placeholder="hello" value={local} onChange={(e) => setLocal(e.target.value)} />
        </div>
        <div className="md:col-span-2">
          <label className="label">Forward to (comma-separated for one → many)</label>
          <input
            className="input"
            placeholder="mygmail@gmail.com, other@outlook.com"
            value={dest}
            onChange={(e) => setDest(e.target.value)}
          />
        </div>
        <div>
          <button className="btn-primary">+ Create Forwarder</button>
        </div>
      </form>
      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}
      <div className="space-y-3">
        {rows.map((row) => (
          <div key={row.id} className="panel flex flex-wrap items-center justify-between gap-4 p-5">
            <div>
              <div className="font-mono text-teal">{row.address}</div>
              <div className="text-mist-500">↓</div>
              {row.destinations.map((d) => (
                <div key={d.email} className="font-mono text-sm">
                  {d.email}
                </div>
              ))}
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge value={row.enabled ? "online" : "offline"} />
              <button className="btn-danger" onClick={() => remove(row.id)}>
                Delete
              </button>
            </div>
          </div>
        ))}
        {rows.length === 0 && <p className="text-mist-500">No forwarders yet.</p>}
      </div>
    </Shell>
  );
}
