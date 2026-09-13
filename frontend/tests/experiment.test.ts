import { describe, expect, it } from "vitest";

import {
  buildExperimentSpec,
  defaultExperimentFormValues,
  type ExperimentFormValues,
} from "@/lib/experiment";

function values(
  overrides: Partial<ExperimentFormValues> = {},
): ExperimentFormValues {
  return { ...defaultExperimentFormValues, ...overrides };
}

describe("buildExperimentSpec", () => {
  it("builds the default HTTP error experiment", () => {
    const spec = buildExperimentSpec(values());
    expect(spec.fault.error_status).toBe(503);
    expect(spec.fault.timeout_ms).toBeNull();
    expect(spec.contract?.recovery?.min_success_rate).toBe(1);
  });

  it("builds timeout, malformed JSON and latency-only faults", () => {
    expect(
      buildExperimentSpec(values({ faultOutcome: "timeout" })).fault.timeout_ms,
    ).toBe(1_000);
    expect(
      buildExperimentSpec(values({ faultOutcome: "malformed-json" })).fault
        .malformed_json,
    ).toBe(true);
    expect(
      buildExperimentSpec(values({ faultOutcome: "none", latencyMs: 250 }))
        .fault.error_status,
    ).toBeNull();
  });

  it("normalizes the fault prefix when the request target has a query", () => {
    const spec = buildExperimentSpec(
      values({ path: "/demo/%70roducts?tag=one&tag=two" }),
    );

    expect(spec.path).toBe("/demo/%70roducts?tag=one&tag=two");
    expect(spec.fault.path_prefix).toBe("/demo/products");
  });

  it("parses optional headers and request bodies", () => {
    const spec = buildExperimentSpec(
      values({
        headersJson: '{"X-Test":"yes"}',
        bodyJson: '{"sku":"keyboard"}',
      }),
    );
    expect(spec.headers).toEqual({ "X-Test": "yes" });
    expect(spec.body).toEqual({ sku: "keyboard" });
  });

  it("omits the resilience contract when disabled", () => {
    expect(
      buildExperimentSpec(values({ contractEnabled: false })).contract,
    ).toBeNull();
  });

  it("rejects a fault profile with no disruption", () => {
    expect(() =>
      buildExperimentSpec(values({ faultOutcome: "none", latencyMs: 0 })),
    ).toThrow("Configure latency or a fault outcome");
  });

  it("rejects malformed or incorrectly shaped JSON inputs", () => {
    expect(() => buildExperimentSpec(values({ headersJson: "{" }))).toThrow(
      "Headers must be valid JSON",
    );
    expect(() =>
      buildExperimentSpec(values({ headersJson: '{"X-Test":1}' })),
    ).toThrow("Headers must be a JSON object with valid values");
    expect(() => buildExperimentSpec(values({ bodyJson: "[]" }))).toThrow(
      "Request body must be a JSON object with valid values",
    );
  });

  it("caps generated contract names at the backend limit", () => {
    const spec = buildExperimentSpec(values({ name: "x".repeat(120) }));
    expect(spec.contract?.name).toHaveLength(120);
  });
});
