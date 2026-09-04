"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, isApiError } from "@/lib/api";

const STEPS = [
  "Welcome",
  "System Check",
  "Network",
  "Hostname",
  "Domain",
  "DNS",
  "SMTP",
  "Security",
  "Administrator",
  "Finish",
];

type SetupStatus = {
  needs_setup: boolean;
  os: { distro: string; arch_linux: boolean; linux: boolean };
  packages: Record<string, boolean>;
  network: {
    local_ipv4?: string | null;
    public_ipv4?: string | null;
    interface?: string | null;
    gateway?: string | null;
    behind_nat?: boolean;
    possibly_cgnat?: boolean;
    warning?: string | null;
  };
};

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [hostname, setHostname] = useState("mail.example.com");
  const [domain, setDomain] = useState("example.com");
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [local, setLocal] = useState("hello");
  const [dest, setDest] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<SetupStatus>("/api/setup/status").then((data) => {
      setStatus(data);
      if (!data.needs_setup) router.replace("/");
    });
  }, [router]);

  const progress = Math.round(((step + 1) / STEPS.length) * 100);

  async function finish(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api("/api/setup", {
        method: "POST",
        body: JSON.stringify({
          hostname,
          domain,
          admin_username: username,
          admin_password: password,
          first_local_part: local || null,
          first_destination: dest || null,
        }),
      });
      router.replace("/");
    } catch (err) {
      setError(isApiError(err) ? String(err.detail) : "Setup failed");
    }
  }

  return (
    <div className="mx-auto min-h-screen max-w-2xl p-8 grid-bg">
      <div className="mb-6 text-xs uppercase tracking-[0.25em] text-teal">MailGate setup</div>
      <h1 className="text-3xl font-semibold">{STEPS[step]}</h1>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
        <div className="h-full bg-teal" style={{ width: `${progress}%` }} />
      </div>
      <p className="mt-2 text-xs text-mist-500">{progress}%</p>

      <div className="panel mt-8 p-6 text-sm text-mist-300">
        {step === 0 && (
          <p>This computer will be used as a public mail server. A laptop on home internet may have NAT, CGNAT, a dynamic IP, and an ISP that blocks port 25.</p>
        )}
        {step === 1 && status && (
          <ul className="space-y-1">
            <li>{status.os.linux ? "✓" : "✗"} Linux — {status.os.distro}</li>
            <li>{status.os.arch_linux ? "✓" : "⚠"} Arch Linux is the primary target</li>
            {Object.entries(status.packages).map(([k, v]) => (
              <li key={k}>
                {v ? "✓" : "✗"} {k}
              </li>
            ))}
          </ul>
        )}
        {step === 2 && status && (
          <div className="font-mono">
            <div>Local IP: {status.network.local_ipv4}</div>
            <div>Public IPv4: {status.network.public_ipv4}</div>
            <div>Interface: {status.network.interface}</div>
            <div>Gateway: {status.network.gateway}</div>
            {status.network.warning && <p className="mt-3 font-sans text-amber-200">{status.network.warning}</p>}
            {status.network.possibly_cgnat && <p className="mt-3 font-sans text-red-300">CGNAT detected. Inbound SMTP will not work.</p>}
          </div>
        )}
        {step === 3 && (
          <div>
            <label className="label">Mail hostname</label>
            <input className="input" value={hostname} onChange={(e) => setHostname(e.target.value)} />
          </div>
        )}
        {step === 4 && (
          <div>
            <label className="label">Domain</label>
            <input className="input" value={domain} onChange={(e) => setDomain(e.target.value)} />
          </div>
        )}
        {step === 5 && (
          <pre className="font-mono text-xs">
{`A    mail    ${status?.network.public_ipv4 || "YOUR_PUBLIC_IP"}
MX   @       10 ${hostname}`}
          </pre>
        )}
        {step === 6 && (
          <p>
            Postfix receives mail on port 25. It is not an open relay. Only verified MailGate domains with forwarding
            rules are accepted. Destination Gmail addresses are not inbound recipients.
          </p>
        )}
        {step === 7 && (
          <p>
            Create a strong administrator password. There is no default. Sessions expire. Cookies are HttpOnly.
            The API is not exposed publicly — Caddy proxies /api on the dashboard hostname only.
          </p>
        )}
        {step === 8 && (
          <form className="space-y-3" onSubmit={finish}>
            <div>
              <label className="label">Username</label>
              <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <div>
              <label className="label">Password</label>
              <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <div>
              <label className="label">First alias (optional)</label>
              <input className="input" value={local} onChange={(e) => setLocal(e.target.value)} />
            </div>
            <div>
              <label className="label">Forward to (optional)</label>
              <input className="input" value={dest} onChange={(e) => setDest(e.target.value)} placeholder="mygmail@gmail.com" />
            </div>
            {error && <p className="text-red-300">{error}</p>}
            <button className="btn-primary">Create administrator</button>
          </form>
        )}
        {step === 9 && <p>Setup is complete after you create the administrator. Then verify DNS with mailgate doctor.</p>}
      </div>

      <div className="mt-6 flex justify-between">
        <button className="btn-ghost" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
          Back
        </button>
        {step < 8 && (
          <button className="btn-primary" onClick={() => setStep((s) => s + 1)}>
            Continue
          </button>
        )}
      </div>
    </div>
  );
}
