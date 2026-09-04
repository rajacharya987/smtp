"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api, isApiError } from "@/lib/api";

type Unit = { name: string; running: boolean; active: string; enabled?: string };

export default function ServicesPage() {
  const [rows, setRows] = useState<Unit[]>([]);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<Unit[]>("/api/system/services").then(setRows);
  }

  useEffect(() => {
    load();
  }, []);

  async function act(name: string, action: string) {
    setError(null);
    try {
      await api(`/api/system/services/${name}/${action}`, { method: "POST" });
      load();
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Failed");
    }
  }

  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-semibold">Services</h1>
      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}
      <div className="space-y-3">
        {rows.map((row) => (
          <div key={row.name} className="panel flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <div className="font-mono">{row.name}</div>
              <div className="text-xs text-mist-500">{row.enabled}</div>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge value={row.running ? "online" : "offline"} />
              <button className="btn-ghost" onClick={() => act(row.name, "start")}>
                Start
              </button>
              <button className="btn-ghost" onClick={() => act(row.name, "restart")}>
                Restart
              </button>
              <button className="btn-danger" onClick={() => act(row.name, "stop")}>
                Stop
              </button>
            </div>
          </div>
        ))}
      </div>
      <p className="mt-4 text-xs text-mist-500">
        PostgreSQL is shown for status only. MailGate will not stop it — other software on this machine may need it.
      </p>
    </Shell>
  );
}
