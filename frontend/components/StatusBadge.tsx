"use client";

const STYLES: Record<string, string> = {
  online: "bg-emerald-400/15 text-emerald-300 ring-emerald-400/30",
  ok: "bg-emerald-400/15 text-emerald-300 ring-emerald-400/30",
  ready: "bg-emerald-400/15 text-emerald-300 ring-emerald-400/30",
  warning: "bg-amber-400/15 text-amber-300 ring-amber-400/30",
  warn: "bg-amber-400/15 text-amber-300 ring-amber-400/30",
  error: "bg-red-400/15 text-red-300 ring-red-400/30",
  fail: "bg-red-400/15 text-red-300 ring-red-400/30",
  failed: "bg-red-400/15 text-red-300 ring-red-400/30",
  offline: "bg-white/10 text-mist-300 ring-white/10",
  rejected: "bg-red-400/15 text-red-300 ring-red-400/30",
  delivered: "bg-emerald-400/15 text-emerald-300 ring-emerald-400/30",
  accepted: "bg-teal/15 text-teal ring-teal/30",
  forwarded: "bg-sky-400/15 text-sky-300 ring-sky-400/30",
  deferred: "bg-amber-400/15 text-amber-300 ring-amber-400/30",
  spam: "bg-fuchsia-400/15 text-fuchsia-300 ring-fuchsia-400/30",
};

export function StatusBadge({ value }: { value: string }) {
  const key = value.toLowerCase();
  const style = STYLES[key] || "bg-white/10 text-mist-300 ring-white/10";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide ring-1 ${style}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {value}
    </span>
  );
}
