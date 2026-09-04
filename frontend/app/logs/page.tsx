"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";

const FILTERS = ["all", "accepted", "rejected", "forwarded", "delivered", "deferred", "failed", "spam"];

type EventRow = {
  id: number;
  timestamp: string;
  event_type: string;
  sender?: string;
  recipient?: string;
  destination?: string;
  response?: string;
};

export default function LogsPage() {
  const [filter, setFilter] = useState("all");
  const [rows, setRows] = useState<EventRow[]>([]);

  useEffect(() => {
    api<EventRow[]>(`/api/logs?status=${filter}`).then(setRows).catch(() => setRows([]));
  }, [filter]);

  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-semibold">Logs</h1>
      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((item) => (
          <button
            key={item}
            className={filter === item ? "btn-primary" : "btn-ghost"}
            onClick={() => setFilter(item)}
          >
            {item}
          </button>
        ))}
      </div>
      <div className="space-y-2">
        {rows.map((row) => (
          <div key={row.id} className="panel p-4 font-mono text-sm">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-mist-500">{row.timestamp}</span>
              <StatusBadge value={row.event_type} />
            </div>
            <div>From: {row.sender || "—"}</div>
            <div>To: {row.recipient || "—"}</div>
            {row.destination && <div>→ {row.destination}</div>}
            {row.response && <div className="text-mist-500">{row.response}</div>}
          </div>
        ))}
        {rows.length === 0 && <p className="text-mist-500">No events stored yet. The worker records Postfix metadata, not message bodies.</p>}
      </div>
    </Shell>
  );
}
