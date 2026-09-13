import { Check, Minus, X } from "lucide-react";

import type { ExperimentResult } from "@/lib/api/schemas";
import { formatMetricName, formatPercent } from "@/lib/format";

function displayOperator(operator: string): string {
  return operator === ">=" ? "≥" : "≤";
}

function displayValue(metric: string, value: number): string {
  if (metric === "success_rate" || metric === "fault_rate") {
    return formatPercent(value);
  }

  if (metric === "p95_latency_ms") {
    return `${value.toFixed(0)} ms`;
  }

  return String(value);
}

export function ContractPanel({ result }: { result: ExperimentResult }) {
  const evaluation = result.contract_evaluation;

  if (evaluation === null) {
    return (
      <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-300">
          <Minus className="h-4 w-4 text-zinc-500" /> No resilience contract
        </div>
        <p className="mt-2 text-xs leading-5 text-zinc-500">
          This run collected measurements without evaluating explicit resilience
          thresholds.
        </p>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
      <div className="flex flex-col gap-3 border-b border-white/6 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold text-zinc-200">
            {evaluation.contract_name}
          </p>
          <p className="mt-1 text-[11px] text-zinc-500">
            Resilience contract evaluation
          </p>
        </div>
        <span
          className={`inline-flex w-fit items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${evaluation.passed ? "border-emerald-400/20 bg-emerald-400/8 text-emerald-300" : "border-rose-400/20 bg-rose-400/8 text-rose-300"}`}
        >
          {evaluation.passed ? (
            <Check className="h-3 w-3" />
          ) : (
            <X className="h-3 w-3" />
          )}
          {evaluation.passed ? "Contract passed" : "Contract failed"}
        </span>
      </div>

      <div className="divide-y divide-white/5">
        {evaluation.checks.map((check) => (
          <div
            key={`${check.phase}-${check.metric}-${check.operator}`}
            className="grid gap-3 px-5 py-4 sm:grid-cols-[120px_1fr_auto] sm:items-center"
          >
            <span className="w-fit rounded-md border border-white/6 bg-zinc-950 px-2 py-1 font-mono text-[10px] text-zinc-500 uppercase">
              {check.phase}
            </span>
            <div>
              <p className="text-xs font-medium text-zinc-300">
                {formatMetricName(check.metric)}
              </p>
              <p className="mt-1 text-[11px] text-zinc-500">
                Expected {displayOperator(check.operator)}{" "}
                {displayValue(check.metric, check.expected)} · observed{" "}
                {displayValue(check.metric, check.observed)}
              </p>
            </div>
            {check.passed ? (
              <Check className="h-4 w-4 text-emerald-400" />
            ) : (
              <X className="h-4 w-4 text-rose-400" />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
