"use client";

import { useState } from "react";
import type { Route } from "next";
import { useRouter } from "next/navigation";
import {
  Activity,
  Braces,
  ChevronDown,
  FlaskConical,
  ShieldCheck,
} from "lucide-react";

import { experimentStartSchema, type HttpMethod } from "@/lib/api/schemas";
import {
  buildExperimentSpec,
  defaultExperimentFormValues,
  type ExperimentFormValues,
  type FaultOutcome,
} from "@/lib/experiment";

const methods: HttpMethod[] = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const outcomes: Array<{ value: FaultOutcome; label: string }> = [
  { value: "http-error", label: "HTTP error" },
  { value: "timeout", label: "Timeout" },
  { value: "malformed-json", label: "Malformed JSON" },
  { value: "none", label: "Latency only" },
];

const inputClass =
  "mt-2 w-full rounded-lg border border-white/8 bg-zinc-950/70 px-3 py-2.5 text-sm text-zinc-200 outline-none transition placeholder:text-zinc-700 focus:border-emerald-400/35 focus:ring-2 focus:ring-emerald-400/8";
const labelClass = "text-xs font-medium text-zinc-400";

export function ExperimentForm() {
  const router = useRouter();
  const [values, setValues] = useState<ExperimentFormValues>(
    defaultExperimentFormValues,
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update<K extends keyof ExperimentFormValues>(
    key: K,
    value: ExperimentFormValues[K],
  ) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const spec = buildExperimentSpec(values);
      const response = await fetch("/api/experiments/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(spec),
      });

      const payload: unknown = await response.json();

      if (!response.ok) {
        const detail =
          typeof payload === "object" && payload !== null && "detail" in payload
            ? String(payload.detail)
            : `Experiment failed with status ${response.status}`;
        throw new Error(detail);
      }

      const started = experimentStartSchema.parse(payload);
      router.push(`/experiments/${started.experiment_id}/live` as Route);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to run experiment",
      );
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]"
    >
      <div className="space-y-6">
        <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <div className="rounded-lg border border-blue-400/15 bg-blue-400/7 p-2 text-blue-300">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-zinc-200">
                Request profile
              </h2>
              <p className="mt-1 text-xs leading-5 text-zinc-500">
                Define the endpoint and traffic RuptureLab should replay across
                baseline, fault and recovery phases.
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <label className={`${labelClass} sm:col-span-2`}>
              Experiment name
              <input
                className={inputClass}
                value={values.name}
                maxLength={120}
                required
                onChange={(event) => update("name", event.target.value)}
              />
            </label>

            <label className={labelClass}>
              Method
              <div className="relative">
                <select
                  className={`${inputClass} appearance-none pr-9 font-mono`}
                  value={values.method}
                  onChange={(event) =>
                    update("method", event.target.value as HttpMethod)
                  }
                >
                  {methods.map((method) => (
                    <option key={method}>{method}</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 bottom-3 h-4 w-4 text-zinc-500" />
              </div>
            </label>

            <label className={labelClass}>
              Path
              <input
                className={`${inputClass} font-mono`}
                value={values.path}
                maxLength={2048}
                required
                onChange={(event) => update("path", event.target.value)}
              />
            </label>

            <label className={labelClass}>
              Requests per phase
              <input
                className={inputClass}
                type="number"
                min={1}
                max={100}
                value={values.requestsPerPhase}
                onChange={(event) =>
                  update("requestsPerPhase", Number(event.target.value))
                }
              />
            </label>

            <label className={labelClass}>
              Interval between requests
              <div className="relative">
                <input
                  className={`${inputClass} pr-12`}
                  type="number"
                  min={0}
                  max={5000}
                  value={values.intervalMs}
                  onChange={(event) =>
                    update("intervalMs", Number(event.target.value))
                  }
                />
                <span className="absolute right-3 bottom-3 text-xs text-zinc-500">
                  ms
                </span>
              </div>
            </label>
          </div>

          <details className="mt-6 rounded-xl border border-white/6 bg-zinc-950/35 p-4">
            <summary className="flex cursor-pointer list-none items-center gap-2 text-xs font-medium text-zinc-400">
              <Braces className="h-3.5 w-3.5 text-zinc-500" />
              Request headers and body
            </summary>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <label className={labelClass}>
                Headers JSON
                <textarea
                  className={`${inputClass} min-h-28 resize-y font-mono text-xs leading-5`}
                  value={values.headersJson}
                  placeholder={'{"X-Demo-Mode": "checkout"}'}
                  onChange={(event) =>
                    update("headersJson", event.target.value)
                  }
                />
              </label>
              <label className={labelClass}>
                Request body JSON
                <textarea
                  className={`${inputClass} min-h-28 resize-y font-mono text-xs leading-5`}
                  value={values.bodyJson}
                  placeholder={'{"sku": "keyboard", "quantity": 1}'}
                  onChange={(event) => update("bodyJson", event.target.value)}
                />
              </label>
            </div>
            <p className="mt-4 text-[11px] leading-5 text-zinc-600">
              Completed runs persist request headers and bodies. Use synthetic
              values only; never enter real secrets or credentials.
            </p>
          </details>
        </section>

        <section className="rounded-2xl border border-white/6 bg-white/[0.02] p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <div className="rounded-lg border border-amber-400/15 bg-amber-400/7 p-2 text-amber-300">
              <FlaskConical className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-zinc-200">
                Fault profile
              </h2>
              <p className="mt-1 text-xs leading-5 text-zinc-500">
                Control how traffic is degraded during the fault phase. Latency
                can be combined with one terminal fault.
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <label className={labelClass}>
              Fault outcome
              <div className="relative">
                <select
                  className={`${inputClass} appearance-none pr-9`}
                  value={values.faultOutcome}
                  onChange={(event) =>
                    update("faultOutcome", event.target.value as FaultOutcome)
                  }
                >
                  {outcomes.map((outcome) => (
                    <option key={outcome.value} value={outcome.value}>
                      {outcome.label}
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 bottom-3 h-4 w-4 text-zinc-500" />
              </div>
            </label>

            <label className={labelClass}>
              Injection probability
              <div className="relative">
                <input
                  className={`${inputClass} pr-11`}
                  type="number"
                  min={0}
                  max={100}
                  step={1}
                  value={Math.round(values.probability * 100)}
                  onChange={(event) =>
                    update("probability", Number(event.target.value) / 100)
                  }
                />
                <span className="absolute right-3 bottom-3 text-xs text-zinc-500">
                  %
                </span>
              </div>
            </label>

            <label className={labelClass}>
              Added latency
              <div className="relative">
                <input
                  className={`${inputClass} pr-12`}
                  type="number"
                  min={0}
                  max={30000}
                  value={values.latencyMs}
                  onChange={(event) =>
                    update("latencyMs", Number(event.target.value))
                  }
                />
                <span className="absolute right-3 bottom-3 text-xs text-zinc-500">
                  ms
                </span>
              </div>
            </label>

            {values.faultOutcome === "http-error" && (
              <label className={labelClass}>
                HTTP status
                <input
                  className={inputClass}
                  type="number"
                  min={400}
                  max={599}
                  value={values.errorStatus}
                  onChange={(event) =>
                    update("errorStatus", Number(event.target.value))
                  }
                />
              </label>
            )}

            {values.faultOutcome === "timeout" && (
              <label className={labelClass}>
                Timeout duration
                <div className="relative">
                  <input
                    className={`${inputClass} pr-12`}
                    type="number"
                    min={1}
                    max={30000}
                    value={values.timeoutMs}
                    onChange={(event) =>
                      update("timeoutMs", Number(event.target.value))
                    }
                  />
                  <span className="absolute right-3 bottom-3 text-xs text-zinc-500">
                    ms
                  </span>
                </div>
              </label>
            )}
          </div>
        </section>
      </div>

      <aside className="space-y-6 xl:sticky xl:top-6 xl:self-start">
        <section className="rounded-2xl border border-white/6 bg-white/[0.025] p-5">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <h2 className="text-sm font-semibold text-zinc-200">
                Resilience contract
              </h2>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={values.contractEnabled}
              aria-label="Enable resilience contract"
              onClick={() => update("contractEnabled", !values.contractEnabled)}
              className={`relative h-5 w-9 rounded-full transition ${values.contractEnabled ? "bg-emerald-400/70" : "bg-zinc-800"}`}
            >
              <span
                className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition ${values.contractEnabled ? "left-[18px]" : "left-0.5"}`}
              />
            </button>
          </div>

          <p className="mt-2 text-xs leading-5 text-zinc-500">
            Turn observed behavior into an explicit pass/fail verdict instead of
            inspecting metrics manually.
          </p>

          {values.contractEnabled && (
            <div className="mt-5 space-y-4 border-t border-white/6 pt-5">
              <RateInput
                label="Baseline success ≥"
                value={values.baselineMinSuccessRate}
                onChange={(value) => update("baselineMinSuccessRate", value)}
              />
              <RateInput
                label="Fault rate ≥"
                value={values.faultMinFaultRate}
                onChange={(value) => update("faultMinFaultRate", value)}
              />
              <RateInput
                label="Recovery success ≥"
                value={values.recoveryMinSuccessRate}
                onChange={(value) => update("recoveryMinSuccessRate", value)}
              />
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-emerald-400/10 bg-emerald-400/[0.035] p-5">
          <p className="font-mono text-[10px] font-semibold tracking-[0.15em] text-emerald-400 uppercase">
            Execution plan
          </p>
          <ol className="mt-4 space-y-3">
            {[
              ["01", "Baseline", "Measure healthy behavior"],
              ["02", "Fault", "Apply the configured disruption"],
              ["03", "Recovery", "Clear the fault and verify recovery"],
            ].map(([step, title, detail]) => (
              <li key={step} className="flex gap-3">
                <span className="font-mono text-[10px] text-zinc-700">
                  {step}
                </span>
                <div>
                  <p className="text-xs font-medium text-zinc-300">{title}</p>
                  <p className="mt-0.5 text-[11px] text-zinc-500">{detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {error && (
          <div
            role="alert"
            className="rounded-xl border border-rose-400/20 bg-rose-400/7 px-4 py-3 text-xs leading-5 text-rose-300"
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-sm font-semibold text-zinc-950 shadow-[0_14px_35px_rgba(52,211,153,0.13)] transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <FlaskConical className="h-4 w-4" />
          {submitting ? "Running experiment…" : "Run resilience experiment"}
        </button>
      </aside>
    </form>
  );
}

function RateInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-4 text-xs text-zinc-500">
      <span>{label}</span>
      <div className="relative w-24">
        <input
          className="w-full rounded-lg border border-white/8 bg-zinc-950/70 py-2 pr-8 pl-2 text-right text-xs text-zinc-200 outline-none focus:border-emerald-400/35"
          type="number"
          min={0}
          max={100}
          value={Math.round(value * 100)}
          onChange={(event) => onChange(Number(event.target.value) / 100)}
        />
        <span className="absolute top-2 right-2 text-xs text-zinc-700">%</span>
      </div>
    </label>
  );
}
