"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api, isApiError } from "@/lib/api";

type Item = {
  queue_id: string;
  sender?: string;
  recipient?: string;
  status?: string;
  created?: number;
  size?: number;
  reason?: string;
};

export default function QueuePage() {
  const [rows, setRows] = useState<Item[]>([]);
  const [inspect, setInspect] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api<Item[]>("/api/queue").then(setRows).catch((err) => setError(err.detail));
  }

  useEffect(() => {
    load();
  }, []);

  async function retry(id: string) {
    try {
      await api(`/api/queue/${id}/retry`, { method: "POST" });
      load();
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Retry failed");
    }
  }

  async function remove(id: string) {
    await api(`/api/queue/${id}`, { method: "DELETE" });
    load();
  }

  async function look(id: string) {
    const data = await api<{ headers: string }>(`/api/queue/${id}`);
    setInspect(data.headers);
  }

  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-semibold">Mail Queue</h1>
      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}
      <div className="panel overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-left text-xs uppercase tracking-widest text-mist-500">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th>Sender</th>
              <th>Recipient</th>
              <th>Status</th>
              <th>Size</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.queue_id} className="border-t border-white/5">
                <td className="px-4 py-3 font-mono">{row.queue_id}</td>
                <td className="font-mono">{row.sender}</td>
                <td className="font-mono">{row.recipient}</td>
                <td>
                  <StatusBadge value={row.status || "unknown"} />
                </td>
                <td>{row.size}</td>
                <td className="space-x-2 whitespace-nowrap pr-4">
                  <button className="btn-ghost" onClick={() => retry(row.queue_id)}>
                    Retry
                  </button>
                  <button className="btn-ghost" onClick={() => look(row.queue_id)}>
                    Inspect
                  </button>
                  <button className="btn-danger" onClick={() => remove(row.queue_id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-mist-500">
                  Queue is empty.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {inspect && (
        <pre className="panel mt-4 overflow-auto p-4 font-mono text-xs text-mist-300">{inspect}</pre>
      )}
    </Shell>
  );
}
