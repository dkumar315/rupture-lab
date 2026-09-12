"use client";

import { useEffect, useMemo, useState } from "react";
import type { Route } from "next";
import { useRouter } from "next/navigation";
import {
  Activity,
  Check,
  Circle,
  LoaderCircle,
  RotateCcw,
  TriangleAlert,
} from "lucide-react";

import { experimentEventSchema } from "@/lib/api/schemas";
import {
  applyExperimentEvent,
  createLiveExperimentState,
  type LivePhaseProgress,
} from "@/lib/live";
import { formatLatency } from "@/lib/format";

const phaseMeta = {
  baseline: { label: "Baseline", accent: "text-blue-400", bar: "bg-blue-400" },
  fault: {
    label: "Fault applied",
    accent: "text-amber-400",
    bar: "bg-amber-400",
  },
  recovery: {
    label: "Recovery",
    accent: "text-emerald-400",
    bar: "bg-emerald-400",
  },
} as const;

export function LiveExperiment({ experimentId }: { experimentId: string }) {
  const router = useRouter();
  const [state, setState] = useState(createLiveExperimentState);
  const [connection, setConnection] = useState<
    "connecting" | "live" | "reconnecting"
  >("connecting");

  useEffect(() => {
    const source = new EventSource(`/api/experiments/${experimentId}/events`);
    let fallbackTimer: number | undefined;
    let redirectTimer: number | undefined;

    source.onopen = () => {
      window.clearTimeout(fallbackTimer);
      setConnection("live");
    };

    source.onmessage = (message) => {
      let payload: unknown;

      try {
        payload = JSON.parse(message.data);
      } catch {
        source.close();
        setState((current) => ({
          ...current,
          status: "failed",
          error: "Live event stream returned invalid JSON",
        }));
        return;
      }

      const parsed = experimentEventSchema.safeParse(payload);
      if (!parsed.success) {
        source.close();
        setState((current) => ({
          ...current,
          status: "failed",
          error: "Live event stream returned an invalid event",
        }));
        return;
      }

      const event = parsed.data;
      setState((current) => applyExperimentEvent(current, event));

      if (event.type === "experiment.completed") {
        source.close();
        redirectTimer = window.setTimeout(() => {
          router.replace(`/experiments/${experimentId}` as Route);
        }, 700);
      }

      if (event.type === "experiment.failed") {
        source.close();
      }
    };

    source.onerror = () => {
      setConnection("reconnecting");
      window.clearTimeout(fallbackTimer);
      fallbackTimer = window.setTimeout(async () => {
        try {
          const response = await fetch(`/api/experiments/${experimentId}`, {
            cache: "no-store",
          });
          if (response.ok) {
            source.close();
            router.replace(`/experiments/${experimentId}` as Route);
          }
        } catch {
          // EventSource keeps retrying; the fallback only checks for a persisted result.
        }
      }, 1_500);
    };

    return () => {
      source.close();
      window.clearTimeout(fallbackTimer);
      window.clearTimeout(redirectTimer);
    };
  }, [experimentId, router]);

  const completedRequests = useMemo(
    () =>
      Object.values(state.phases).reduce(
        (total, phase) => total + phase.completedRequests,
        0,
      ),
    [state.phases],
  );
  const totalRequests = useMemo(
    () =>
      Object.values(state.phases).reduce(
        (total, phase) => total + phase.totalRequests,
        0,
      ),
    [state.phases],
  );

  return (
    <div className="space-y-8">
      <header className="border-b border-white/6 pb-8">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <p className="font-mono text-[10px] font-semibold tracking-[0.18em] text-emerald-400 uppercase">
              Live experiment
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              {state.name ?? "Preparing resilience run…"}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-500">
              Watching measured traffic move through baseline, controlled
              failure and recovery.
            </p>
          </div>
          <ConnectionState
            state={connection}
            failed={state.status === "failed"}
          />
        </div>
      </header>

      <section className="grid gap-4 lg:grid-cols-3">
        {(Object.keys(phaseMeta) as Array<keyof typeof phaseMeta>).map(
          (phase) => (
            <LivePhaseCard
              key={phase}
              phase={phase}
              progress={state.phases[phase]}
            />
          ),
        )}
      </section>

      <section className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
          <div className="flex items-center justify-between gap-4 border-b border-white/6 px-5 py-4">
            <div>
              <h2 className="text-sm font-semibold text-zinc-200">
                Live request feed
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                Most recent observations from the active experiment.
              </p>
            </div>
            <span className="font-mono text-[11px] text-zinc-500">
              {completedRequests}/{totalRequests || "—"}
            </span>
          </div>

          {state.recentRequests.length === 0 ? (
            <div className="flex min-h-56 items-center justify-center px-6 text-center text-sm text-zinc-500">
              Waiting for the first measured request…
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {state.recentRequests.map((request) => (
                <div
                  key={`${request.phase}-${request.requestNumber}`}
                  className="grid grid-cols-[100px_1fr_auto] items-center gap-4 px-5 py-3 text-xs"
                >
                  <span className="font-mono text-[10px] text-zinc-500 uppercase">
                    {request.phase} {request.requestNumber}
                  </span>
                  <span className="text-zinc-400">
                    {request.statusCode ?? "transport"} · {request.outcome}
                  </span>
                  <span className="font-mono text-zinc-500">
                    {formatLatency(request.durationMs)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-white/6 bg-white/[0.02] p-5">
            <p className="font-mono text-[10px] font-semibold tracking-[0.15em] text-zinc-500 uppercase">
              Run state
            </p>
            <div className="mt-4 flex items-center gap-3">
              {state.status === "failed" ? (
                <TriangleAlert className="h-5 w-5 text-rose-400" />
              ) : state.status === "completed" ? (
                <Check className="h-5 w-5 text-emerald-400" />
              ) : (
                <LoaderCircle className="h-5 w-5 animate-spin text-emerald-400" />
              )}
              <div>
                <p className="text-sm font-medium text-zinc-200">
                  {state.status === "failed"
                    ? "Experiment stopped"
                    : state.status === "completed"
                      ? "Experiment persisted"
                      : "Experiment running"}
                </p>
                <p className="mt-0.5 text-xs text-zinc-500">
                  {state.error ??
                    (state.contractEvaluation
                      ? state.contractEvaluation.passed
                        ? "Resilience contract passed"
                        : "Resilience contract failed"
                      : "Metrics update as requests complete")}
                </p>
              </div>
            </div>
          </div>

          {state.status === "failed" && (
            <button
              type="button"
              onClick={() => router.push("/experiments/new" as Route)}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/8 bg-white/[0.035] px-4 py-3 text-sm font-semibold text-zinc-300 transition hover:bg-white/[0.06] hover:text-white"
            >
              <RotateCcw className="h-4 w-4" /> Configure another run
            </button>
          )}
        </aside>
      </section>
    </div>
  );
}

function LivePhaseCard({
  phase,
  progress,
}: {
  phase: keyof typeof phaseMeta;
  progress: LivePhaseProgress;
}) {
  const meta = phaseMeta[phase];
  const percentage =
    progress.totalRequests === 0
      ? 0
      : Math.round((progress.completedRequests / progress.totalRequests) * 100);

  return (
    <article className="rounded-2xl border border-white/6 bg-white/[0.02] p-5">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          {progress.status === "completed" ? (
            <Check className={`h-4 w-4 ${meta.accent}`} />
          ) : progress.status === "running" ? (
            <Activity className={`h-4 w-4 ${meta.accent}`} />
          ) : (
            <Circle className="h-4 w-4 text-zinc-700" />
          )}
          <h2 className="text-sm font-semibold text-zinc-200">{meta.label}</h2>
        </div>
        <span className="font-mono text-[10px] text-zinc-600 uppercase">
          {progress.status}
        </span>
      </div>

      <div className="mt-6 grid grid-cols-3 gap-3">
        <LiveMetric
          label="Done"
          value={`${progress.completedRequests}/${progress.totalRequests || "—"}`}
        />
        <LiveMetric
          label="Success"
          value={String(progress.successfulRequests)}
        />
        <LiveMetric
          label="Latency"
          value={
            progress.latestLatencyMs === null
              ? "—"
              : formatLatency(progress.latestLatencyMs)
          }
        />
      </div>

      <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-zinc-900">
        <div
          className={`h-full rounded-full transition-all duration-300 ${meta.bar}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="mt-3 flex justify-between text-[11px] text-zinc-600">
        <span>{progress.faultedRequests} faulted</span>
        <span>{progress.transportErrors} transport errors</span>
      </div>
    </article>
  );
}

function LiveMetric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-semibold tracking-wide text-zinc-600 uppercase">
        {label}
      </p>
      <p className="mt-1.5 font-mono text-sm font-semibold text-zinc-200">
        {value}
      </p>
    </div>
  );
}

function ConnectionState({
  state,
  failed,
}: {
  state: "connecting" | "live" | "reconnecting";
  failed: boolean;
}) {
  const label = failed
    ? "Stopped"
    : state === "live"
      ? "Live"
      : state === "reconnecting"
        ? "Reconnecting"
        : "Connecting";

  return (
    <div className="inline-flex w-fit items-center gap-2 rounded-full border border-white/8 bg-white/[0.03] px-3 py-1.5 text-xs font-medium text-zinc-400">
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          failed
            ? "bg-rose-400"
            : state === "live"
              ? "bg-emerald-400"
              : "animate-pulse bg-amber-400"
        }`}
      />
      {label}
    </div>
  );
}
