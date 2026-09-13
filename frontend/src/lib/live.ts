import type {
  ContractEvaluation,
  ExperimentEvent,
  ExperimentResult,
  PhaseName,
  PhaseResult,
} from "@/lib/api/schemas";

export type LiveRunStatus = "connecting" | "running" | "completed" | "failed";
export type LivePhaseStatus = "pending" | "running" | "completed";

export interface LivePhaseProgress {
  status: LivePhaseStatus;
  completedRequests: number;
  totalRequests: number;
  successfulRequests: number;
  faultedRequests: number;
  transportErrors: number;
  latencyMs: number | null;
  result: PhaseResult | null;
}

export interface LiveRequestObservation {
  phase: PhaseName;
  requestNumber: number;
  statusCode: number | null;
  durationMs: number;
  outcome: string;
}

export interface LiveExperimentState {
  status: LiveRunStatus;
  name: string | null;
  phases: Record<PhaseName, LivePhaseProgress>;
  recentRequests: LiveRequestObservation[];
  contractEvaluation: ContractEvaluation | null;
  result: ExperimentResult | null;
  error: string | null;
}

function emptyPhase(): LivePhaseProgress {
  return {
    status: "pending",
    completedRequests: 0,
    totalRequests: 0,
    successfulRequests: 0,
    faultedRequests: 0,
    transportErrors: 0,
    latencyMs: null,
    result: null,
  };
}

export function createLiveExperimentState(): LiveExperimentState {
  return {
    status: "connecting",
    name: null,
    phases: {
      baseline: emptyPhase(),
      fault: emptyPhase(),
      recovery: emptyPhase(),
    },
    recentRequests: [],
    contractEvaluation: null,
    result: null,
    error: null,
  };
}

export function applyExperimentEvent(
  state: LiveExperimentState,
  event: ExperimentEvent,
): LiveExperimentState {
  switch (event.type) {
    case "experiment.started":
      return {
        ...state,
        status: "running",
        name: event.name,
        phases: {
          baseline: {
            ...state.phases.baseline,
            totalRequests: event.requests_per_phase,
          },
          fault: {
            ...state.phases.fault,
            totalRequests: event.requests_per_phase,
          },
          recovery: {
            ...state.phases.recovery,
            totalRequests: event.requests_per_phase,
          },
        },
      };

    case "phase.started":
      return {
        ...state,
        phases: {
          ...state.phases,
          [event.phase]: {
            ...state.phases[event.phase],
            status: "running",
            totalRequests: event.requests_per_phase,
          },
        },
      };

    case "request.completed": {
      const phase = state.phases[event.phase];
      const measurement = event.measurement;
      const outcome =
        measurement.error ??
        measurement.fault ??
        (measurement.successful ? "success" : "failed");
      const observation: LiveRequestObservation = {
        phase: event.phase,
        requestNumber: event.request_number,
        statusCode: measurement.status_code,
        durationMs: measurement.duration_ms,
        outcome,
      };

      return {
        ...state,
        phases: {
          ...state.phases,
          [event.phase]: {
            ...phase,
            completedRequests: event.request_number,
            totalRequests: event.requests_per_phase,
            successfulRequests:
              phase.successfulRequests + (measurement.successful ? 1 : 0),
            faultedRequests:
              phase.faultedRequests + (measurement.fault === null ? 0 : 1),
            transportErrors:
              phase.transportErrors + (measurement.error === null ? 0 : 1),
            latencyMs: measurement.duration_ms,
          },
        },
        recentRequests: [...state.recentRequests, observation].slice(-8),
      };
    }

    case "phase.completed":
      return {
        ...state,
        phases: {
          ...state.phases,
          [event.phase]: {
            status: "completed",
            completedRequests: event.phase_result.request_count,
            totalRequests: event.phase_result.request_count,
            successfulRequests: event.phase_result.successful_requests,
            faultedRequests: event.phase_result.faulted_requests,
            transportErrors: event.phase_result.transport_errors,
            latencyMs: event.phase_result.p95_latency_ms,
            result: event.phase_result,
          },
        },
      };

    case "contract.evaluated":
      return {
        ...state,
        contractEvaluation: event.contract_evaluation,
      };

    case "experiment.completed":
      return {
        ...state,
        status: "completed",
        result: event.result,
      };

    case "experiment.failed":
      return {
        ...state,
        status: "failed",
        error: event.message,
      };
  }
}
