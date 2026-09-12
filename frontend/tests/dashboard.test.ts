import { describe, expect, it } from "vitest";

import type { ExperimentSummary } from "@/lib/api/schemas";
import { computeDashboardStats } from "@/lib/dashboard";

function summary(
  id: string,
  contractPassed: boolean | null,
): ExperimentSummary {
  return {
    experiment_id: id,
    name: "Products",
    started_at: "2026-09-11T06:00:00Z",
    completed_at: "2026-09-11T06:00:01Z",
    method: "GET",
    path: "/demo/products",
    requests_per_phase: 2,
    interval_ms: 0,
    contract_passed: contractPassed,
  };
}

describe("computeDashboardStats", () => {
  it("returns an empty state", () => {
    expect(computeDashboardStats([])).toEqual({
      recentRuns: 0,
      evaluatedRuns: 0,
      passedRuns: 0,
      passRate: null,
      latest: null,
    });
  });

  it("calculates contract pass rate and preserves newest run", () => {
    const runs = [
      summary("11111111-1111-4111-8111-111111111111", true),
      summary("22222222-2222-4222-8222-222222222222", false),
      summary("33333333-3333-4333-8333-333333333333", null),
    ];

    const stats = computeDashboardStats(runs);
    expect(stats.recentRuns).toBe(3);
    expect(stats.evaluatedRuns).toBe(2);
    expect(stats.passedRuns).toBe(1);
    expect(stats.passRate).toBe(0.5);
    expect(stats.latest).toBe(runs[0]);
  });
});
