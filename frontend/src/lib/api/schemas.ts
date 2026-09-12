import { z } from "zod";

export const httpMethodSchema = z.enum([
  "GET",
  "POST",
  "PUT",
  "PATCH",
  "DELETE",
  "OPTIONS",
  "HEAD",
]);

export const phaseNameSchema = z.enum(["baseline", "fault", "recovery"]);

export const faultProfileSchema = z.object({
  enabled: z.boolean(),
  path_prefix: z.string(),
  methods: z.array(httpMethodSchema),
  probability: z.number(),
  latency_ms: z.number(),
  error_status: z.number().nullable(),
  timeout_ms: z.number().nullable(),
  malformed_json: z.boolean(),
});

export const phaseContractSchema = z.object({
  min_success_rate: z.number().nullable().optional(),
  max_p95_latency_ms: z.number().nullable().optional(),
  max_transport_errors: z.number().nullable().optional(),
  min_fault_rate: z.number().nullable().optional(),
});

export const resilienceContractSchema = z.object({
  name: z.string(),
  baseline: phaseContractSchema.nullable().optional(),
  fault: phaseContractSchema.nullable().optional(),
  recovery: phaseContractSchema.nullable().optional(),
});

export const experimentSpecSchema = z.object({
  name: z.string(),
  method: httpMethodSchema,
  path: z.string(),
  requests_per_phase: z.number(),
  interval_ms: z.number(),
  headers: z.record(z.string(), z.string()),
  body: z.record(z.string(), z.unknown()).nullable(),
  fault: faultProfileSchema,
  contract: resilienceContractSchema.nullable(),
});

export const requestMeasurementSchema = z.object({
  status_code: z.number().nullable(),
  duration_ms: z.number(),
  successful: z.boolean(),
  fault: z.string().nullable(),
  error: z.string().nullable(),
});

export const phaseResultSchema = z.object({
  phase: phaseNameSchema,
  request_count: z.number(),
  successful_requests: z.number(),
  failed_requests: z.number(),
  transport_errors: z.number(),
  faulted_requests: z.number(),
  status_codes: z.record(z.string(), z.number()),
  average_latency_ms: z.number(),
  p95_latency_ms: z.number(),
  measurements: z.array(requestMeasurementSchema),
});

export const contractCheckSchema = z.object({
  phase: phaseNameSchema,
  metric: z.enum([
    "success_rate",
    "p95_latency_ms",
    "transport_errors",
    "fault_rate",
  ]),
  operator: z.enum([">=", "<="]),
  expected: z.number(),
  observed: z.number(),
  passed: z.boolean(),
});

export const contractEvaluationSchema = z.object({
  contract_name: z.string(),
  passed: z.boolean(),
  checks: z.array(contractCheckSchema),
});

export const experimentResultSchema = z.object({
  experiment_id: z.string().uuid(),
  name: z.string(),
  started_at: z.string(),
  spec: experimentSpecSchema,
  phases: z.array(phaseResultSchema),
  contract_evaluation: contractEvaluationSchema.nullable(),
});

export const experimentStartSchema = z.object({
  experiment_id: z.string().uuid(),
  name: z.string(),
});

const experimentEventBase = {
  sequence: z.number().int().positive(),
  experiment_id: z.string().uuid(),
  occurred_at: z.string(),
};

export const experimentEventSchema = z.discriminatedUnion("type", [
  z.object({
    ...experimentEventBase,
    type: z.literal("experiment.started"),
    name: z.string(),
    requests_per_phase: z.number().int().positive(),
  }),
  z.object({
    ...experimentEventBase,
    type: z.literal("phase.started"),
    phase: phaseNameSchema,
    requests_per_phase: z.number().int().positive(),
  }),
  z.object({
    ...experimentEventBase,
    type: z.literal("request.completed"),
    phase: phaseNameSchema,
    request_number: z.number().int().positive(),
    requests_per_phase: z.number().int().positive(),
    measurement: requestMeasurementSchema,
  }),
  z.object({
    ...experimentEventBase,
    type: z.literal("phase.completed"),
    phase: phaseNameSchema,
    phase_result: phaseResultSchema,
  }),
  z.object({
    ...experimentEventBase,
    type: z.literal("contract.evaluated"),
    contract_evaluation: contractEvaluationSchema,
  }),
  z.object({
    ...experimentEventBase,
    type: z.literal("experiment.completed"),
    result: experimentResultSchema,
  }),
  z.object({
    ...experimentEventBase,
    type: z.literal("experiment.failed"),
    message: z.string(),
  }),
]);

export const experimentSummarySchema = z.object({
  experiment_id: z.string().uuid(),
  name: z.string(),
  started_at: z.string(),
  completed_at: z.string(),
  method: httpMethodSchema,
  path: z.string(),
  requests_per_phase: z.number(),
  interval_ms: z.number(),
  contract_passed: z.boolean().nullable(),
});

export const experimentSummaryListSchema = z.array(experimentSummarySchema);
export const healthSchema = z.object({ status: z.literal("ok") });

export type HttpMethod = z.infer<typeof httpMethodSchema>;
export type PhaseName = z.infer<typeof phaseNameSchema>;
export type FaultProfile = z.infer<typeof faultProfileSchema>;
export type ResilienceContract = z.infer<typeof resilienceContractSchema>;
export type ExperimentSpec = z.infer<typeof experimentSpecSchema>;
export type RequestMeasurement = z.infer<typeof requestMeasurementSchema>;
export type PhaseResult = z.infer<typeof phaseResultSchema>;
export type ExperimentResult = z.infer<typeof experimentResultSchema>;
export type ExperimentSummary = z.infer<typeof experimentSummarySchema>;
export type ExperimentStart = z.infer<typeof experimentStartSchema>;
export type ExperimentEvent = z.infer<typeof experimentEventSchema>;
export type ContractCheck = z.infer<typeof contractCheckSchema>;
export type ContractEvaluation = z.infer<typeof contractEvaluationSchema>;
