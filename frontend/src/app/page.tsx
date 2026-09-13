import Link from "next/link";
import { ArrowRight, CircleDot, Database, Server } from "lucide-react";

import { ExperimentTable } from "@/components/experiment-table";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { computeDashboardStats } from "@/lib/dashboard";
import { getHealth, listExperiments } from "@/lib/api/client";
import type { ExperimentSummary } from "@/lib/api/schemas";
import { formatPercent, formatRelativeTime } from "@/lib/format";

export default async function DashboardPage() {
  let experiments: ExperimentSummary[] = [];
  let historyAvailable = true;

  try {
    experiments = await listExperiments(50, 0);
  } catch {
    historyAvailable = false;
  }

  const healthy = await getHealth();
  const stats = computeDashboardStats(experiments);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Control surface"
        title="Resilience, measured."
        description="Run controlled API failures, compare baseline and recovery behavior, and keep a durable history of every experiment."
        action={
          <Link
            href="/experiments/new"
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-2.5 text-sm font-semibold whitespace-nowrap text-zinc-950 shadow-[0_14px_35px_rgba(52,211,153,0.12)] transition hover:bg-emerald-300"
          >
            New experiment <ArrowRight className="h-4 w-4" />
          </Link>
        }
      />

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Recent runs"
          value={String(stats.recentRuns)}
          detail="Latest 50 persisted experiments"
        />
        <MetricCard
          label="Contract pass rate"
          value={stats.passRate === null ? "—" : formatPercent(stats.passRate)}
          detail={
            stats.evaluatedRuns === 0
              ? "No contracted runs yet"
              : `${stats.passedRuns} of ${stats.evaluatedRuns} evaluated runs passed`
          }
          accent={stats.passRate === 1}
        />
        <MetricCard
          label="Latest experiment"
          value={
            stats.latest === null
              ? "—"
              : formatRelativeTime(stats.latest.started_at)
          }
          detail={stats.latest?.name ?? "No persisted experiment yet"}
        />
        <MetricCard
          label="Control API"
          value={healthy ? "Connected" : "Unavailable"}
          detail={
            healthy
              ? "Backend health check is responding"
              : "Start the RuptureLab API on port 8000"
          }
          accent={healthy}
        />
      </section>

      <section className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_330px]">
        <div>
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-zinc-200">
                Experiment history
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                Newest persisted runs first
              </p>
            </div>
            {!historyAvailable && (
              <span className="text-xs font-medium text-rose-300">
                History API unavailable
              </span>
            )}
          </div>
          <ExperimentTable experiments={experiments} />
        </div>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-white/6 bg-white/[0.02] p-5">
            <p className="font-mono text-[10px] font-semibold tracking-[0.15em] text-zinc-500 uppercase">
              Architecture
            </p>
            <div className="mt-5 space-y-4">
              <SystemRow
                icon={Server}
                label="Control API"
                value=":8000"
                state={healthy ? "online" : "offline"}
              />
              <SystemRow
                icon={CircleDot}
                label="Fault proxy"
                value=":8080"
                state="configured"
              />
              <SystemRow
                icon={Database}
                label="PostgreSQL"
                value=":5432"
                state="configured"
              />
            </div>
          </div>

          <div className="rounded-2xl border border-blue-400/10 bg-blue-400/[0.03] p-5">
            <p className="text-xs font-semibold text-blue-200">
              What a run proves
            </p>
            <p className="mt-2 text-xs leading-5 text-zinc-500">
              RuptureLab measures healthy behavior, injects a controlled fault,
              clears it, then checks whether the target returns to its declared
              resilience thresholds.
            </p>
          </div>
        </aside>
      </section>
    </div>
  );
}

function SystemRow({
  icon: Icon,
  label,
  value,
  state,
}: {
  icon: typeof Server;
  label: string;
  value: string;
  state: "online" | "offline" | "configured";
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex items-center gap-2.5">
        <Icon className="h-3.5 w-3.5 text-zinc-500" />
        <span className="text-xs text-zinc-400">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] text-zinc-700">{value}</span>
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            state === "online"
              ? "bg-emerald-400"
              : state === "offline"
                ? "bg-rose-400"
                : "bg-zinc-600"
          }`}
        />
      </div>
    </div>
  );
}
