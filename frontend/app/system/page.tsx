"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";

type Doctor = {
  overall_text: string;
  overall: string;
  checks: { group: string; name: string; level: string; message: string }[];
  port25_warning: string;
  home_server_warning: string;
};

export default function SystemPage() {
  const [doctor, setDoctor] = useState<Doctor | null>(null);

  useEffect(() => {
    api<Doctor>("/api/system/doctor").then(setDoctor);
  }, []);

  return (
    <Shell>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-semibold">System</h1>
        <Link className="btn-ghost" href="/system/services/">
          Services
        </Link>
      </div>
      {doctor && (
        <>
          <div className="panel mb-6 p-6">
            <div className="text-xs uppercase tracking-widest text-mist-500">Overall</div>
            <div className="mt-1 text-2xl font-semibold">{doctor.overall_text}</div>
          </div>
          <div className="space-y-2">
            {doctor.checks.map((check, i) => (
              <div key={i} className="panel flex items-start justify-between gap-4 p-4">
                <div>
                  <div className="text-xs uppercase tracking-widest text-mist-500">{check.group}</div>
                  <div className="font-medium">{check.name}</div>
                  <div className="text-sm text-mist-300">{check.message}</div>
                </div>
                <StatusBadge value={check.level} />
              </div>
            ))}
          </div>
          <div className="mt-6 space-y-3 text-sm text-mist-300">
            <p>{doctor.port25_warning}</p>
            <p>{doctor.home_server_warning}</p>
          </div>
        </>
      )}
    </Shell>
  );
}
