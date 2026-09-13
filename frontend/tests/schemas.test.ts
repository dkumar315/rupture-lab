import { describe, expect, it } from "vitest";

import {
  experimentEventSchema,
  experimentSummarySchema,
  healthSchema,
  requestTargetSchema,
} from "@/lib/api/schemas";

describe("API schemas", () => {
  it("parses health and experiment summaries", () => {
    expect(healthSchema.parse({ status: "ok" })).toEqual({ status: "ok" });
    expect(
      experimentSummarySchema.parse({
        experiment_id: "11111111-1111-4111-8111-111111111111",
        name: "Products",
        started_at: "2026-09-11T06:00:00Z",
        completed_at: "2026-09-11T06:00:01Z",
        method: "GET",
        path: "/demo/products",
        requests_per_phase: 2,
        interval_ms: 0,
        contract_passed: true,
      }).method,
    ).toBe("GET");
  });

  it("rejects unsafe request targets at the API boundary", () => {
    expect(
      requestTargetSchema.safeParse("//example.com/products").success,
    ).toBe(false);
  });
});

it("validates live experiment events", () => {
  const base = {
    sequence: 1,
    experiment_id: "11111111-1111-4111-8111-111111111111",
    occurred_at: "2026-09-12T03:00:00Z",
  };

  expect(
    experimentEventSchema.parse({
      ...base,
      type: "experiment.started",
      name: "Live run",
      requests_per_phase: 5,
    }).type,
  ).toBe("experiment.started");

  expect(
    experimentEventSchema.safeParse({ ...base, type: "unknown" }).success,
  ).toBe(false);
});
