"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";

type Net = {
  network: {
    local_ipv4?: string | null;
    public_ipv4?: string | null;
    interface?: string | null;
    gateway?: string | null;
    behind_nat?: boolean;
    possibly_cgnat?: boolean;
    notes?: string[];
    warning?: string | null;
  };
  firewall: { router_forwarding: string[]; nftables: string };
  dynamic_ip_warning: string | null;
  port25_warning: string;
};

export default function NetworkSettingsPage() {
  const [data, setData] = useState<Net | null>(null);

  useEffect(() => {
    api<Net>("/api/settings/network").then(setData);
  }, []);

  if (!data) {
    return (
      <Shell>
        <p className="text-mist-500">Loading…</p>
      </Shell>
    );
  }

  const n = data.network;
  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-semibold">Network</h1>
      <div className="panel mb-4 p-6 font-mono text-sm">
        <div>Local IP: {n.local_ipv4 || "unknown"}</div>
        <div>Public IPv4: {n.public_ipv4 || "unknown"}</div>
        <div>Interface: {n.interface || "unknown"}</div>
        <div>Gateway: {n.gateway || "unknown"}</div>
      </div>
      {n.local_ipv4 && n.public_ipv4 && n.local_ipv4 !== n.public_ipv4 && (
        <div className="mb-4 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm">
          Local IP is not the public IP. This host is behind NAT.
        </div>
      )}
      {data.dynamic_ip_warning && (
        <div className="mb-4 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm">{data.dynamic_ip_warning}</div>
      )}
      <div className="panel mb-4 p-6 text-sm">
        <h2 className="mb-2 font-medium">Port 25</h2>
        <p className="text-mist-300">{data.port25_warning}</p>
      </div>
      <div className="panel mb-4 p-6 text-sm">
        <h2 className="mb-2 font-medium">Router forwarding</h2>
        <ul className="list-disc pl-5 text-mist-300">
          {data.firewall.router_forwarding.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>
      <pre className="panel overflow-auto p-4 font-mono text-xs">{data.firewall.nftables}</pre>
    </Shell>
  );
}
