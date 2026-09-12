import { describe, expect, it } from "vitest";

import type {
  ExperimentEvent,
  ExperimentResult,
  PhaseResult,
  RequestMeasurement,
} from "@/lib/api/schemas";
import { applyExperimentEvent, createLiveExperimentState } from "@/lib/live";
import {
  buildExperimentSpec,
  defaultExperimentFormValues,
} from "@/lib/experiment";

const experimentId = "11111111-1111-4111-8111-111111111111";
const occurredAt = "2026-09-12T03:00:00Z";

function measurement(
  overrides: Partial<RequestMeasurement> = {},
): RequestMeasurement {
  return {
    status_code: 200,
    duration_ms: 8,
    successful: true,
    fault: null,
    error: null,
    ...overrides,
  };
}

function phaseResult(): PhaseResult {
  return {
    phase: "baseline",
    request_count: 2,
    successful_requests: 2,
    failed_requests: 0,
    transport_errors: 0,
    faulted_requests: 0,
    status_codes: { "200": 2 },
    average_latency_ms: 7,
    p95_latency_ms: 8,
    measurements: [measurement(), measurement({ duration_ms: 6 })],
  };
}

function result(): ExperimentResult {
  return {
    experiment_id: experimentId,
    name: "Live run",
    started_at: occurredAt,
    spec: buildExperimentSpec(defaultExperimentFormValues),
    phases: [phaseResult()],
    contract_evaluation: null,
  };
}

function event(
  value: { type: ExperimentEvent["type"] } & Record<string, unknown>,
): ExperimentEvent {
  return {
    sequence: 1,
    experiment_id: experimentId,
    occurred_at: occurredAt,
    ...value,
  } as ExperimentEvent;
}

describe("live experiment reducer", () => {
  it("initializes and starts all phase totals", () => {
    const initial = createLiveExperimentState();
    const started = applyExperimentEvent(
      initial,
      event({
        type: "experiment.started",
        name: "Live run",
        requests_per_phase: 2,
      }),
    );

    expect(initial.status).toBe("connecting");
    expect(started.status).toBe("running");
    expect(started.name).toBe("Live run");
    expect(
      Object.values(started.phases).map((phase) => phase.totalRequests),
    ).toEqual([2, 2, 2]);
  });

  it("tracks phase starts and successful, faulted and transport observations", () => {
    let state = createLiveExperimentState();
    state = applyExperimentEvent(
      state,
      event({ type: "phase.started", phase: "fault", requests_per_phase: 3 }),
    );
    state = applyExperimentEvent(
      state,
      event({
        type: "request.completed",
        phase: "fault",
        request_number: 1,
        requests_per_phase: 3,
        measurement: measurement({
          status_code: 503,
          successful: false,
          fault: "http-error",
        }),
      }),
    );
    state = applyExperimentEvent(
      state,
      event({
        type: "request.completed",
        phase: "fault",
        request_number: 2,
        requests_per_phase: 3,
        measurement: measurement({
          status_code: null,
          successful: false,
          error: "ConnectError",
        }),
      }),
    );
    state = applyExperimentEvent(
      state,
      event({
        type: "request.completed",
        phase: "fault",
        request_number: 3,
        requests_per_phase: 3,
        measurement: measurement(),
      }),
    );

    expect(state.phases.fault).toMatchObject({
      status: "running",
      completedRequests: 3,
      successfulRequests: 1,
      faultedRequests: 1,
      transportErrors: 1,
      latestLatencyMs: 8,
    });
    expect(state.recentRequests.map((item) => item.outcome)).toEqual([
      "http-error",
      "ConnectError",
      "success",
    ]);
  });

  it("labels unsuccessful requests without a fault or transport error as failed", () => {
    const state = applyExperimentEvent(
      createLiveExperimentState(),
      event({
        type: "request.completed",
        phase: "baseline",
        request_number: 1,
        requests_per_phase: 1,
        measurement: measurement({ successful: false }),
      }),
    );

    expect(state.recentRequests).toEqual([
      expect.objectContaining({
        outcome: "failed",
      }),
    ]);
  });

  it("keeps only the eight most recent observations", () => {
    let state = createLiveExperimentState();

    for (let index = 1; index <= 9; index += 1) {
      state = applyExperimentEvent(
        state,
        event({
          type: "request.completed",
          phase: "baseline",
          request_number: index,
          requests_per_phase: 9,
          measurement: measurement({ duration_ms: index }),
        }),
      );
    }

    expect(state.recentRequests).toHaveLength(8);
    expect(state.recentRequests[0]?.requestNumber).toBe(2);
    expect(state.recentRequests[7]?.requestNumber).toBe(9);
  });

  it("completes phases, contracts and the experiment", () => {
    let state = createLiveExperimentState();
    const phase = phaseResult();
    state = applyExperimentEvent(
      state,
      event({
        type: "phase.completed",
        phase: "baseline",
        phase_result: phase,
      }),
    );
    state = applyExperimentEvent(
      state,
      event({
        type: "contract.evaluated",
        contract_evaluation: {
          contract_name: "Live contract",
          passed: true,
          checks: [],
        },
      }),
    );
    const completedResult = result();
    state = applyExperimentEvent(
      state,
      event({ type: "experiment.completed", result: completedResult }),
    );

    expect(state.phases.baseline).toMatchObject({
      status: "completed",
      completedRequests: 2,
      successfulRequests: 2,
      latestLatencyMs: 8,
      result: phase,
    });
    expect(state.contractEvaluation?.passed).toBe(true);
    expect(state.status).toBe("completed");
    expect(state.result).toEqual(completedResult);
  });

  it("records terminal failures", () => {
    const state = applyExperimentEvent(
      createLiveExperimentState(),
      event({ type: "experiment.failed", message: "proxy unavailable" }),
    );

    expect(state.status).toBe("failed");
    expect(state.error).toBe("proxy unavailable");
  });
});
