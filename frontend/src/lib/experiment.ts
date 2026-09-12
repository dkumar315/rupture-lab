import { z } from "zod";

import {
  experimentSpecSchema,
  type ExperimentSpec,
  type HttpMethod,
} from "@/lib/api/schemas";

export type FaultOutcome = "none" | "http-error" | "timeout" | "malformed-json";

export interface ExperimentFormValues {
  name: string;
  method: HttpMethod;
  path: string;
  requestsPerPhase: number;
  intervalMs: number;
  headersJson: string;
  bodyJson: string;
  probability: number;
  latencyMs: number;
  faultOutcome: FaultOutcome;
  errorStatus: number;
  timeoutMs: number;
  contractEnabled: boolean;
  baselineMinSuccessRate: number;
  faultMinFaultRate: number;
  recoveryMinSuccessRate: number;
}

export const defaultExperimentFormValues: ExperimentFormValues = {
  name: "Product API resilience",
  method: "GET",
  path: "/demo/products",
  requestsPerPhase: 5,
  intervalMs: 100,
  headersJson: "",
  bodyJson: "",
  probability: 1,
  latencyMs: 0,
  faultOutcome: "http-error",
  errorStatus: 503,
  timeoutMs: 1_000,
  contractEnabled: true,
  baselineMinSuccessRate: 1,
  faultMinFaultRate: 1,
  recoveryMinSuccessRate: 1,
};

const headersSchema = z.record(z.string(), z.string());
const bodySchema = z.record(z.string(), z.unknown());

function parseJsonObject<T>(
  value: string,
  label: string,
  schema: z.ZodType<T>,
): T | undefined {
  if (value.trim() === "") {
    return undefined;
  }

  let parsed: unknown;

  try {
    parsed = JSON.parse(value);
  } catch {
    throw new Error(`${label} must be valid JSON`);
  }

  const result = schema.safeParse(parsed);
  if (!result.success) {
    throw new Error(`${label} must be a JSON object with valid values`);
  }

  return result.data;
}

export function buildExperimentSpec(
  values: ExperimentFormValues,
): ExperimentSpec {
  if (values.latencyMs === 0 && values.faultOutcome === "none") {
    throw new Error(
      "Configure latency or a fault outcome before running the experiment",
    );
  }

  const headers =
    parseJsonObject(values.headersJson, "Headers", headersSchema) ?? {};
  const body =
    parseJsonObject(values.bodyJson, "Request body", bodySchema) ?? null;

  const fault = {
    enabled: true,
    path_prefix: values.path,
    methods: [values.method],
    probability: values.probability,
    latency_ms: values.latencyMs,
    error_status:
      values.faultOutcome === "http-error" ? values.errorStatus : null,
    timeout_ms: values.faultOutcome === "timeout" ? values.timeoutMs : null,
    malformed_json: values.faultOutcome === "malformed-json",
  };

  const contract = values.contractEnabled
    ? {
        name: `${values.name} contract`.slice(0, 120),
        baseline: { min_success_rate: values.baselineMinSuccessRate },
        fault: { min_fault_rate: values.faultMinFaultRate },
        recovery: { min_success_rate: values.recoveryMinSuccessRate },
      }
    : null;

  return experimentSpecSchema.parse({
    name: values.name,
    method: values.method,
    path: values.path,
    requests_per_phase: values.requestsPerPhase,
    interval_ms: values.intervalMs,
    headers,
    body,
    fault,
    contract,
  });
}
