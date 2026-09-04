"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, isApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [needsSetup, setNeedsSetup] = useState(false);

  useEffect(() => {
    api<{ needs_setup: boolean }>("/api/setup/status")
      .then((data) => {
        if (data.needs_setup) {
          setNeedsSetup(true);
          router.replace("/setup/");
        }
      })
      .catch(() => undefined);
  }, [router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      router.replace("/");
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center p-6 grid-bg">
      <form onSubmit={onSubmit} className="panel w-full max-w-md p-8">
        <div className="mb-6">
          <div className="mb-3 inline-flex rounded-xl bg-teal/15 px-3 py-1 font-mono text-xs text-teal">MAILGATE</div>
          <h1 className="text-2xl font-semibold">Sign in</h1>
          <p className="mt-1 text-sm text-mist-500">The dashboard is private. There is no default password.</p>
        </div>
        <label className="label">Username</label>
        <input className="input mb-4" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        <label className="label">Password</label>
        <input
          className="input mb-6"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
        {error && <p className="mb-4 text-sm text-red-300">{error}</p>}
        <button className="btn-primary w-full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        {needsSetup && <p className="mt-4 text-center text-sm text-mist-500">First run — redirecting to setup.</p>}
      </form>
    </div>
  );
}
