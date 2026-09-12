"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FlaskConical, LayoutDashboard } from "lucide-react";

const navigation = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/experiments/new", label: "New experiment", icon: FlaskConical },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }

  return pathname === href;
}

export function DesktopNavigation() {
  const pathname = usePathname();

  return (
    <nav className="mt-9 space-y-1" aria-label="Primary navigation">
      {navigation.map(({ href, label, icon: Icon }) => {
        const active = isActive(pathname, href);

        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
              active
                ? "bg-white/5 text-zinc-100"
                : "text-zinc-400 hover:bg-white/[0.035] hover:text-zinc-100"
            }`}
          >
            <Icon
              className={`h-4 w-4 transition ${
                active
                  ? "text-emerald-400"
                  : "text-zinc-500 group-hover:text-emerald-400"
              }`}
            />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

export function MobileNavigation() {
  const pathname = usePathname();
  const onBuilder = pathname === "/experiments/new";

  return onBuilder ? (
    <Link
      href="/"
      className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.035] px-3 py-1.5 text-xs font-semibold text-zinc-300"
    >
      <LayoutDashboard className="h-3.5 w-3.5" />
      Overview
    </Link>
  ) : (
    <Link
      href="/experiments/new"
      className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-400/25 bg-emerald-400/8 px-3 py-1.5 text-xs font-semibold text-emerald-300"
    >
      <FlaskConical className="h-3.5 w-3.5" />
      New experiment
    </Link>
  );
}
