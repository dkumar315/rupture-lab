import type { Route } from "next";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { ContractStatus } from "@/components/status-pill";
import type { ExperimentSummary } from "@/lib/api/schemas";
import { formatRelativeTime } from "@/lib/format";

function experimentHref(experimentId: string): Route {
  return `/experiments/${experimentId}` as Route;
}

export function ExperimentTable({
  experiments,
}: {
  experiments: ExperimentSummary[];
}) {
  if (experiments.length === 0) {
    return (
      <div className="flex min-h-56 flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.015] px-6 text-center">
        <p className="text-sm font-medium text-zinc-300">No experiments yet</p>
        <p className="mt-1.5 max-w-sm text-xs leading-5 text-zinc-500">
          Your completed resilience runs will appear here with their contract
          verdicts and execution details.
        </p>
        <Link
          href="/experiments/new"
          className="mt-4 text-xs font-semibold text-emerald-400 transition hover:text-emerald-300"
        >
          Configure the first experiment →
        </Link>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-3 xl:hidden">
        {experiments.map((experiment) => (
          <Link
            key={experiment.experiment_id}
            href={experimentHref(experiment.experiment_id)}
            className="block rounded-2xl border border-white/6 bg-white/[0.02] p-4 transition hover:border-white/10 hover:bg-white/[0.03]"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-zinc-200">
                  {experiment.name}
                </p>
                <p className="mt-1 font-mono text-[10px] text-zinc-700">
                  {experiment.experiment_id.slice(0, 8)}
                </p>
              </div>
              <ArrowUpRight className="h-4 w-4 shrink-0 text-zinc-700" />
            </div>

            <div className="mt-4 flex min-w-0 items-center gap-2">
              <span className="rounded-md border border-white/7 bg-zinc-900 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-zinc-500">
                {experiment.method}
              </span>
              <span className="truncate font-mono text-xs text-zinc-400">
                {experiment.path}
              </span>
            </div>

            <div className="mt-4 grid grid-cols-2 items-end gap-3 border-t border-white/5 pt-4">
              <div>
                <p className="text-[10px] font-semibold tracking-wide text-zinc-700 uppercase">
                  Contract
                </p>
                <div className="mt-2">
                  <ContractStatus value={experiment.contract_passed} />
                </div>
              </div>
              <div className="text-right">
                <p className="text-[10px] font-semibold tracking-wide text-zinc-700 uppercase">
                  Run
                </p>
                <p className="mt-2 text-xs text-zinc-400">
                  {experiment.requests_per_phase} × 3 ·{" "}
                  {formatRelativeTime(experiment.started_at)}
                </p>
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="hidden overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02] xl:block">
        <table className="w-full text-left">
          <thead className="border-b border-white/6 bg-white/[0.018]">
            <tr className="text-[11px] font-semibold tracking-wide text-zinc-500 uppercase">
              <th className="px-5 py-3.5">Experiment</th>
              <th className="px-5 py-3.5">Target</th>
              <th className="px-5 py-3.5">Contract</th>
              <th className="px-5 py-3.5">Requests</th>
              <th className="px-5 py-3.5">Started</th>
              <th className="w-12 px-5 py-3.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {experiments.map((experiment) => (
              <tr
                key={experiment.experiment_id}
                className="group transition hover:bg-white/[0.025]"
              >
                <td className="px-5 py-4">
                  <Link
                    href={experimentHref(experiment.experiment_id)}
                    className="font-medium text-zinc-200 transition group-hover:text-white"
                  >
                    {experiment.name}
                  </Link>
                  <div className="mt-1 font-mono text-[10px] text-zinc-700">
                    {experiment.experiment_id.slice(0, 8)}
                  </div>
                </td>
                <td className="px-5 py-4">
                  <span className="mr-2 rounded-md border border-white/7 bg-zinc-900 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-zinc-500">
                    {experiment.method}
                  </span>
                  <span className="font-mono text-xs text-zinc-400">
                    {experiment.path}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <ContractStatus value={experiment.contract_passed} />
                </td>
                <td className="px-5 py-4 text-sm text-zinc-400">
                  {experiment.requests_per_phase} × 3
                </td>
                <td className="px-5 py-4 text-xs text-zinc-500">
                  {formatRelativeTime(experiment.started_at)}
                </td>
                <td className="px-5 py-4">
                  <ArrowUpRight
                    aria-hidden="true"
                    className="h-4 w-4 text-zinc-700 transition group-hover:text-emerald-400"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
