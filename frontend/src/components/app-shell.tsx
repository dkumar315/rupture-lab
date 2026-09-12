import Link from "next/link";
import { Activity } from "lucide-react";

import {
  DesktopNavigation,
  MobileNavigation,
} from "@/components/app-navigation";
import { BrandMark } from "@/components/brand-mark";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--surface-0)] text-zinc-100">
      <div className="pointer-events-none fixed inset-0 z-0 bg-[radial-gradient(circle_at_15%_-10%,rgba(52,211,153,0.08),transparent_28%),radial-gradient(circle_at_85%_5%,rgba(59,130,246,0.06),transparent_24%)]" />

      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-white/6 bg-zinc-950/80 px-4 py-5 backdrop-blur-xl lg:block">
        <Link href="/" className="flex items-center gap-3 px-2">
          <BrandMark />
          <div>
            <div className="text-sm font-semibold tracking-tight text-white">
              RuptureLab
            </div>
            <div className="text-xs text-zinc-500">resilience workbench</div>
          </div>
        </Link>

        <DesktopNavigation />

        <div className="absolute right-4 bottom-5 left-4 rounded-xl border border-white/6 bg-white/[0.025] p-3">
          <div className="flex items-center gap-2 text-xs font-medium text-zinc-300">
            <Activity className="h-3.5 w-3.5 text-emerald-400" />
            Local control plane
          </div>
          <p className="mt-1.5 text-xs leading-5 text-zinc-500">
            API :8000 · proxy :8080 · durable experiment history.
          </p>
        </div>
      </aside>

      <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-white/6 bg-zinc-950/75 px-5 backdrop-blur-xl lg:hidden">
        <Link href="/" className="flex items-center gap-2.5">
          <BrandMark className="h-7 w-7" />
          <span className="text-sm font-semibold">RuptureLab</span>
        </Link>

        <MobileNavigation />
      </header>

      <main className="relative z-10 lg:pl-64">
        <div className="mx-auto w-full max-w-[1500px] px-5 py-8 sm:px-8 lg:px-10 lg:py-10">
          {children}
        </div>
      </main>
    </div>
  );
}
