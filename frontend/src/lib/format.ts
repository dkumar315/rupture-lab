import type { PhaseResult } from "@/lib/api/schemas";

const dateTimeFormatter = new Intl.DateTimeFormat("en-AU", {
  dateStyle: "medium",
  timeStyle: "short",
});

const relativeFormatter = new Intl.RelativeTimeFormat("en", {
  numeric: "auto",
});

export function formatDateTime(value: string): string {
  return dateTimeFormatter.format(new Date(value));
}

export function formatRelativeTime(value: string, now = Date.now()): string {
  const difference = new Date(value).getTime() - now;
  const absolute = Math.abs(difference);

  if (absolute < 60_000) {
    return relativeFormatter.format(Math.round(difference / 1_000), "second");
  }

  if (absolute < 3_600_000) {
    return relativeFormatter.format(Math.round(difference / 60_000), "minute");
  }

  if (absolute < 86_400_000) {
    return relativeFormatter.format(Math.round(difference / 3_600_000), "hour");
  }

  return relativeFormatter.format(Math.round(difference / 86_400_000), "day");
}

export function formatLatency(value: number): string {
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(2)} s`;
  }

  return `${value.toFixed(value < 10 ? 1 : 0)} ms`;
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function successRate(phase: PhaseResult): number {
  if (phase.request_count === 0) {
    return 0;
  }

  return phase.successful_requests / phase.request_count;
}

export function faultRate(phase: PhaseResult): number {
  if (phase.request_count === 0) {
    return 0;
  }

  return phase.faulted_requests / phase.request_count;
}

const metricLabels: Record<string, string> = {
  success_rate: "Success rate",
  p95_latency_ms: "P95 latency",
  transport_errors: "Transport errors",
  fault_rate: "Fault rate",
};

export function formatMetricName(metric: string): string {
  return metricLabels[metric] ?? metric.replaceAll("_", " ");
}
