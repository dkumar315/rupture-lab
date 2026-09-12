import type { ExperimentSummary } from "@/lib/api/schemas";

export interface DashboardStats {
  recentRuns: number;
  evaluatedRuns: number;
  passedRuns: number;
  passRate: number | null;
  latest: ExperimentSummary | null;
}

export function computeDashboardStats(
  experiments: ExperimentSummary[],
): DashboardStats {
  const evaluated = experiments.filter(
    (experiment) => experiment.contract_passed !== null,
  );
  const passed = evaluated.filter(
    (experiment) => experiment.contract_passed === true,
  );

  return {
    recentRuns: experiments.length,
    evaluatedRuns: evaluated.length,
    passedRuns: passed.length,
    passRate: evaluated.length === 0 ? null : passed.length / evaluated.length,
    latest: experiments[0] ?? null,
  };
}
