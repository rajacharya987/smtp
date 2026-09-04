"use client";

import { Shell } from "@/components/Shell";

export default function SecuritySettingsPage() {
  return (
    <Shell>
      <h1 className="mb-4 text-3xl font-semibold">Security settings</h1>
      <div className="panel max-w-2xl space-y-3 p-6 text-sm text-mist-300">
        <p>Dashboard cookies are HttpOnly, SameSite=Lax, and HTTPS-only in production.</p>
        <p>Passwords are hashed with Argon2. There is no default administrator password.</p>
        <p>Mutating API calls require a CSRF token and a matching Origin.</p>
        <p>Login attempts are throttled. The API is rate-limited.</p>
        <p>PostgreSQL and the FastAPI port are bound to localhost. Caddy is the only public HTTP(S) surface besides SMTP.</p>
        <p>TOTP 2FA is reserved for a later release.</p>
      </div>
    </Shell>
  );
}
