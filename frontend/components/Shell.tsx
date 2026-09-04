"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/domains/", label: "Domains" },
  { href: "/forwarders/", label: "Forwarders" },
  { href: "/mail-queue/", label: "Mail Queue" },
  { href: "/logs/", label: "Logs" },
  { href: "/dns/", label: "DNS" },
  { href: "/security/", label: "Security" },
  { href: "/settings/", label: "Settings" },
];

const BOTTOM = [
  { href: "/system/", label: "System" },
  { href: "/help/", label: "Help" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && !user) router.replace("/login/");
  }, [loading, user, router]);

  async function logout() {
    await api("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    router.replace("/login/");
  }

  if (loading || !user) {
    return (
      <div className="grid min-h-screen place-items-center text-mist-500">
        Checking session…
      </div>
    );
  }

  return (
    <div className="min-h-screen grid-bg lg:grid lg:grid-cols-[240px_1fr]">
      <aside className="border-b border-white/10 bg-ink-900/90 p-4 lg:border-b-0 lg:border-r">
        <div className="mb-8 flex items-center gap-3 px-2">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-teal/15 font-mono text-sm text-teal">
            MG
          </div>
          <div>
            <div className="text-sm font-semibold tracking-wide">MailGate</div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-mist-500">Mail gateway</div>
          </div>
        </div>
        <nav className="space-y-1">
          {NAV.map((item) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link key={item.href} href={item.href} className={`nav-link ${active ? "active" : ""}`}>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="my-6 h-px bg-white/10" />
        <nav className="space-y-1">
          {BOTTOM.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-link ${pathname.startsWith(item.href) ? "active" : ""}`}
            >
              {item.label}
            </Link>
          ))}
          <button onClick={logout} className="nav-link w-full text-left">
            Logout
          </button>
        </nav>
        <div className="mt-8 px-3 text-xs text-mist-500">Signed in as {user.username}</div>
      </aside>
      <main className="min-h-screen p-6 lg:p-10">{children}</main>
    </div>
  );
}
