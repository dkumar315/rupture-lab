import { describe, expect, it } from "vitest";

import type { PhaseResult } from "@/lib/api/schemas";
import {
  faultRate,
  formatDateTime,
  formatLatency,
  formatMetricName,
  formatPercent,
  formatRelativeTime,
  successRate,
} from "@/lib/format";

const phase: PhaseResult = {
  phase: "baseline",
  request_count: 4,
  successful_requests: 3,
  failed_requests: 1,
  transport_errors: 0,
  faulted_requests: 1,
  status_codes: { "200": 3, "503": 1 },
  average_latency_ms: 10,
  p95_latency_ms: 20,
  measurements: [],
};

describe("format helpers", () => {
  it("formats latency across millisecond and second ranges", () => {
    expect(formatLatency(4.25)).toBe("4.3 ms");
    expect(formatLatency(125)).toBe("125 ms");
    expect(formatLatency(1_250)).toBe("1.25 s");
  });

  it("formats absolute timestamps", () => {
    expect(formatDateTime("2026-09-11T06:00:00Z")).toContain("2026");
  });

  it("formats percentages and metric labels", () => {
    expect(formatPercent(0.875)).toBe("88%");
    expect(formatMetricName("p95_latency_ms")).toBe("P95 latency");
    expect(formatMetricName("custom_metric")).toBe("custom metric");
  });

  it("calculates success and fault rates including empty phases", () => {
    expect(successRate(phase)).toBe(0.75);
    expect(faultRate(phase)).toBe(0.25);
    expect(successRate({ ...phase, request_count: 0 })).toBe(0);
    expect(faultRate({ ...phase, request_count: 0 })).toBe(0);
  });

  it("formats relative times at second, minute, hour and day scales", () => {
    const now = new Date("2026-09-11T06:00:00Z").getTime();
    expect(formatRelativeTime("2026-09-11T05:59:30Z", now)).toContain(
      "30 seconds ago",
    );
    expect(formatRelativeTime("2026-09-11T05:55:00Z", now)).toContain(
      "5 minutes ago",
    );
    expect(formatRelativeTime("2026-09-11T03:00:00Z", now)).toContain(
      "3 hours ago",
    );
    expect(formatRelativeTime("2026-09-09T06:00:00Z", now)).toContain(
      "2 days ago",
    );
  });
});
