"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api, isApiError } from "@/lib/api";

type Domain = {
  id: number;
  name: string;
  hostname: string | null;
  enabled: boolean;
  verified: boolean;
  catch_all_enabled: boolean;
  catch_all_destination: string | null;
};

type DnsReport = {
  verified: boolean;
  checks: { check: string; status: string; message: string; expected?: string }[];
};

export default function DomainViewPage() {
  const router = useRouter();
  const [domain, setDomain] = useState<Domain | null>(null);
  const [dns, setDns] = useState<DnsReport | null>(null);
  const [catchAll, setCatchAll] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [id, setId] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setId(params.get("id"));
  }, []);

  function load(domainId: string) {
    api<Domain>(`/api/domains/${domainId}`).then((d) => {
      setDomain(d);
      setCatchAll(d.catch_all_destination || "");
    });
  }

  useEffect(() => {
    if (id) load(id);
  }, [id]);

  async function verify() {
    if (!id) return;
    setError(null);
    try {
      const report = await api<DnsReport>(`/api/domains/${id}/verify`, { method: "POST" });
      setDns(report);
      load(id);
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Verify failed");
    }
  }

  async function saveCatchAll(enabled: boolean) {
    if (!domain) return;
    setError(null);
    try {
      await api(`/api/domains/${domain.id}`, {
        method: "PATCH",
        body: JSON.stringify({ catch_all_enabled: enabled, catch_all_destination: catchAll || null }),
      });
      load(String(domain.id));
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Save failed");
    }
  }

  async function remove() {
    if (!domain || !confirm(`Delete ${domain.name}?`)) return;
    await api(`/api/domains/${domain.id}`, { method: "DELETE" });
    router.push("/domains/");
  }

  if (!domain) {
    return (
      <Shell>
        <p className="text-mist-500">Loading…</p>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold">{domain.name}</h1>
          <p className="font-mono text-sm text-mist-500">{domain.hostname}</p>
        </div>
        <div className="flex gap-2">
          <StatusBadge value={domain.verified ? "ok" : "warning"} />
          <StatusBadge value={domain.enabled ? "online" : "offline"} />
        </div>
      </div>
      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}
      <div className="panel mb-6 p-6">
        <h2 className="mb-3 text-sm uppercase tracking-widest text-mist-500">Domain verification</h2>
        <p className="mb-4 text-sm text-mist-300">
          A domain is not activated until A and MX records verify. MailGate will not accept mail for unverified domains.
        </p>
        <button className="btn-primary" onClick={verify}>
          Verify Again
        </button>
        {dns && (
          <div className="mt-4 space-y-2">
            {dns.checks.map((check) => (
              <div key={check.check} className="rounded-lg border border-white/5 p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{check.check}</span>
                  <StatusBadge value={check.status} />
                </div>
                <p className="mt-1 text-mist-300">{check.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="panel mb-6 p-6">
        <h2 className="mb-3 text-sm uppercase tracking-widest text-mist-500">Catch-all</h2>
        <p className="mb-3 text-sm text-amber-200">Warning: catch-all addresses may receive large amounts of unwanted email.</p>
        <label className="label">Forward *@{domain.name} to</label>
        <input className="input mb-3 max-w-md" value={catchAll} onChange={(e) => setCatchAll(e.target.value)} />
        <div className="flex gap-3">
          <button className="btn-primary" onClick={() => saveCatchAll(true)}>
            Enable catch-all
          </button>
          <button className="btn-ghost" onClick={() => saveCatchAll(false)}>
            Disable
          </button>
        </div>
      </div>
      <button className="btn-danger" onClick={remove}>
        Delete domain
      </button>
    </Shell>
  );
}
