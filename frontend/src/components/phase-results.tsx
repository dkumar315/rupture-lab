import type { PhaseResult } from "@/lib/api/schemas";
import {
  faultRate,
  formatLatency,
  formatPercent,
  successRate,
} from "@/lib/format";

const phaseLabels = {
  baseline: "Baseline",
  fault: "Fault applied",
  recovery: "Recovery",
} as const;

const phaseAccent = {
  baseline: "bg-blue-400",
  fault: "bg-amber-400",
  recovery: "bg-emerald-400",
} as const;

export function PhaseResults({ phases }: { phases: PhaseResult[] }) {
  const maxLatency = Math.max(
    ...phases.map((phase) => phase.p95_latency_ms),
    1,
  );

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {phases.map((phase) => {
        const success = successRate(phase);
        const fault = faultRate(phase);
        const latencyWidth =
          phase.p95_latency_ms === 0
            ? 0
            : Math.max((phase.p95_latency_ms / maxLatency) * 100, 4);

        return (
          <article
            key={phase.phase}
            className="rounded-2xl border border-white/6 bg-white/[0.02] p-5"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span
                  className={`h-2 w-2 rounded-full ${phaseAccent[phase.phase]}`}
                />
                <h3 className="text-sm font-semibold text-zinc-200">
                  {phaseLabels[phase.phase]}
                </h3>
              </div>
              <span className="font-mono text-[10px] text-zinc-700">
                {phase.request_count} req
              </span>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4">
              <div>
                <p className="text-[10px] font-semibold tracking-wide text-zinc-500 uppercase">
                  Success
                </p>
                <p className="mt-1 text-xl font-semibold tracking-tight text-zinc-100">
                  {formatPercent(success)}
                </p>
              </div>
              <div>
                <p className="text-[10px] font-semibold tracking-wide text-zinc-500 uppercase">
                  Faulted
                </p>
                <p className="mt-1 text-xl font-semibold tracking-tight text-zinc-100">
                  {formatPercent(fault)}
                </p>
              </div>
            </div>

            <div className="mt-6">
              <div className="flex items-end justify-between gap-3">
                <p className="text-[10px] font-semibold tracking-wide text-zinc-500 uppercase">
                  P95 latency
                </p>
                <span className="font-mono text-xs text-zinc-400">
                  {formatLatency(phase.p95_latency_ms)}
                </span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-zinc-900">
                <div
                  className={`${phaseAccent[phase.phase]} h-full rounded-full opacity-70`}
                  style={{ width: `${latencyWidth}%` }}
                />
              </div>
            </div>

            <div className="mt-5 flex items-center justify-between border-t border-white/5 pt-4 text-[11px] text-zinc-500">
              <span>{phase.transport_errors} transport errors</span>
              <span>{formatLatency(phase.average_latency_ms)} avg</span>
            </div>
          </article>
        );
      })}
    </div>
  );
}
