"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api, isApiError } from "@/lib/api";

type Domain = {
  id: number;
  name: string;
  hostname: string | null;
  enabled: boolean;
  verified: boolean;
  alias_count: number;
  catch_all_enabled: boolean;
};

export default function DomainsPage() {
  const [rows, setRows] = useState<Domain[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<Domain[]>("/api/domains").then(setRows).catch((err) => setError(err.detail));
  }

  useEffect(() => {
    load();
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api("/api/domains", { method: "POST", body: JSON.stringify({ name }) });
      setName("");
      load();
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Failed");
    }
  }

  return (
    <Shell>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-semibold">Domains</h1>
      </div>
      <form onSubmit={onSubmit} className="panel mb-6 flex flex-wrap gap-3 p-4">
        <input className="input max-w-sm" placeholder="example.com" value={name} onChange={(e) => setName(e.target.value)} />
        <button className="btn-primary">+ Add Domain</button>
      </form>
      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}
      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-left text-xs uppercase tracking-widest text-mist-500">
            <tr>
              <th className="px-4 py-3">Domain</th>
              <th>Hostname</th>
              <th>Verified</th>
              <th>Enabled</th>
              <th>Aliases</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t border-white/5">
                <td className="px-4 py-3">
                  <Link className="text-teal hover:underline" href={`/domains/view/?id=${row.id}`}>
                    {row.name}
                  </Link>
                </td>
                <td className="font-mono text-mist-300">{row.hostname}</td>
                <td>
                  <StatusBadge value={row.verified ? "ok" : "warning"} />
                </td>
                <td>
                  <StatusBadge value={row.enabled ? "online" : "offline"} />
                </td>
                <td>{row.alias_count}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-mist-500">
                  No domains yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
