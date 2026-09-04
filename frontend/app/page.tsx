"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";

type Status = {
  smtp: string;
  dashboard: string;
  hostname: string;
  public_ip: string | null;
  smtp_port: number;
  domains: number;
  forwarders: number;
  queued_mail: number;
  failed_mail: number;
  network: {
    behind_nat?: boolean;
    possibly_cgnat?: boolean;
    possibly_dynamic?: boolean;
    local_ipv4?: string | null;
    warning?: string | null;
  };
};

type Forwarder = {
  address: string;
  destinations: { email: string }[];
};

export default function DashboardPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [forwarders, setForwarders] = useState<Forwarder[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api<Status>("/api/system/status"), api<Forwarder[]>("/api/forwarders")])
      .then(([s, f]) => {
        setStatus(s);
        setForwarders(f);
      })
      .catch((err) => setError(err.detail || "Failed to load"));
  }, []);

  return (
    <Shell>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-mist-500">MailGate</p>
          <h1 className="text-3xl font-semibold">SMTP gateway</h1>
        </div>
        {status && <StatusBadge value={status.smtp} />}
      </div>

      {error && <p className="mb-4 text-red-300">{error}</p>}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Stat label="SMTP status" value={status?.smtp?.toUpperCase() || "…"} />
        <Stat label="Public IP" value={status?.public_ip || "unknown"} mono />
        <Stat label="SMTP port" value={String(status?.smtp_port ?? 25)} />
        <Stat label="Hostname" value={status?.hostname || "…"} mono />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-4">
        <Stat label="Domains" value={String(status?.domains ?? "…")} />
        <Stat label="Forwarders" value={String(status?.forwarders ?? "…")} />
        <Stat label="Queued mail" value={String(status?.queued_mail ?? "…")} />
        <Stat label="Failed mail" value={String(status?.failed_mail ?? "…")} />
      </div>

      {status?.network?.possibly_cgnat && (
        <Alert title="CGNAT detected">
          Inbound connections will not reach this laptop. A real public IP (typically a VPS) is required.
        </Alert>
      )}
      {status?.network?.behind_nat && !status.network.possibly_cgnat && (
        <Alert title="Behind NAT">
          Forward TCP 25, 80, and 443 to {status.network.local_ipv4}. MailGate will not change your router.
        </Alert>
      )}
      {status?.network?.possibly_dynamic && (
        <Alert title="Dynamic IP">
          Your public IP may be dynamic. For reliable mail hosting, a static public IP is recommended.
        </Alert>
      )}

      <div className="mt-8 panel p-6">
        <h2 className="mb-4 text-sm uppercase tracking-widest text-mist-500">Forwarding</h2>
        <div className="space-y-3">
          {forwarders.length === 0 && <p className="text-sm text-mist-500">No forwarders yet.</p>}
          {forwarders.map((item) => (
            <div key={item.address} className="rounded-xl border border-white/5 bg-ink-950/60 p-4">
              <div className="font-mono text-teal">{item.address}</div>
              <div className="my-1 text-mist-500">↓</div>
              {item.destinations.map((d) => (
                <div key={d.email} className="font-mono text-mist-100">
                  {d.email}
                </div>
              ))}
            </div>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link className="btn-primary" href="/forwarders/">
            Add Forwarder
          </Link>
          <Link className="btn-ghost" href="/dns/">
            Check DNS
          </Link>
          <Link className="btn-ghost" href="/logs/">
            View Logs
          </Link>
          <Link className="btn-ghost" href="/system/">
            System Status
          </Link>
        </div>
      </div>
    </Shell>
  );
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="panel p-5">
      <div className="text-xs uppercase tracking-widest text-mist-500">{label}</div>
      <div className={`mt-2 text-xl ${mono ? "font-mono" : "font-semibold"}`}>{value}</div>
    </div>
  );
}

function Alert({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-4 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">
      <div className="font-medium">{title}</div>
      <div className="mt-1 text-amber-100/80">{children}</div>
    </div>
  );
}
