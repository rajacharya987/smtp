"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";

type Domain = { id: number; name: string };
type DnsInfo = {
  domain: string;
  hostname: string;
  public_ip: string | null;
  records: { type: string; name: string; value: string; priority?: number | null; purpose?: string }[];
  ptr_note: string;
};
type Report = {
  verified: boolean;
  checks: { check: string; status: string; message: string; expected?: string; actual?: string }[];
};

export default function DnsPage() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [info, setInfo] = useState<DnsInfo | null>(null);
  const [report, setReport] = useState<Report | null>(null);

  useEffect(() => {
    api<Domain[]>("/api/domains").then((list) => {
      setDomains(list);
      if (list[0]) setSelected(list[0].name);
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    api<DnsInfo>(`/api/dns/${selected}`).then(setInfo);
  }, [selected]);

  async function check() {
    if (!selected) return;
    setReport(await api<Report>(`/api/dns/${selected}/check`, { method: "POST" }));
  }

  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-semibold">DNS status</h1>
      <div className="mb-4 max-w-sm">
        <label className="label">Domain</label>
        <select className="input" value={selected} onChange={(e) => setSelected(e.target.value)}>
          {domains.map((d) => (
            <option key={d.id}>{d.name}</option>
          ))}
        </select>
      </div>
      {info && (
        <div className="panel mb-6 p-6">
          <p className="mb-4 text-sm text-mist-300">
            Hostname <span className="font-mono text-teal">{info.hostname}</span> should resolve to{" "}
            <span className="font-mono">{info.public_ip || "YOUR_PUBLIC_IP"}</span>
          </p>
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-widest text-mist-500">
              <tr>
                <th className="py-2">Type</th>
                <th>Name</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {info.records.map((rec, i) => (
                <tr key={i} className="border-t border-white/5 font-mono">
                  <td className="py-2">{rec.type}</td>
                  <td>{rec.name}</td>
                  <td>
                    {rec.priority ? `${rec.priority} ` : ""}
                    {rec.value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-4 text-xs text-mist-500">{info.ptr_note}</p>
          <button className="btn-primary mt-4" onClick={check}>
            Verify DNS
          </button>
        </div>
      )}
      {report && (
        <div className="space-y-2">
          {report.checks.map((check) => (
            <div key={check.check} className="panel p-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">{check.check} record</span>
                <StatusBadge value={check.status} />
              </div>
              <p className="mt-1 text-sm text-mist-300">{check.message}</p>
            </div>
          ))}
        </div>
      )}
    </Shell>
  );
}
