import { createServer } from "node:http";

const seededId = "11111111-1111-4111-8111-111111111111";
const createdId = "22222222-2222-4222-8222-222222222222";

function spec(name = "Checkout resilience") {
  return {
    name,
    method: "GET",
    path: "/demo/products",
    requests_per_phase: 2,
    interval_ms: 50,
    headers: {},
    body: null,
    fault: {
      enabled: true,
      path_prefix: "/demo/products",
      methods: ["GET"],
      probability: 1,
      latency_ms: 0,
      error_status: 503,
      timeout_ms: null,
      malformed_json: false,
    },
    contract: {
      name: `${name} contract`,
      baseline: { min_success_rate: 1 },
      fault: { min_fault_rate: 1 },
      recovery: { min_success_rate: 1 },
    },
  };
}

function phases() {
  return [
    phase("baseline", 2, 0, 12.5, 200, true),
    phase("fault", 0, 2, 4.2, 503, false, "http-error"),
    phase("recovery", 2, 0, 9.1, 200, true),
  ];
}

function phase(
  name,
  successful,
  faulted,
  latency,
  statusCode,
  success,
  fault = null,
) {
  return {
    phase: name,
    request_count: 2,
    successful_requests: successful,
    failed_requests: 2 - successful,
    transport_errors: 0,
    faulted_requests: faulted,
    status_codes: { [String(statusCode)]: 2 },
    average_latency_ms: latency,
    p95_latency_ms: latency,
    measurements: [1, 2].map(() => ({
      status_code: statusCode,
      duration_ms: latency,
      successful: success,
      fault,
      error: null,
    })),
  };
}

function result(id, name) {
  return {
    experiment_id: id,
    name,
    started_at: "2026-09-11T06:00:00+00:00",
    spec: spec(name),
    phases: phases(),
    contract_evaluation: {
      contract_name: `${name} contract`,
      passed: true,
      checks: [
        {
          phase: "baseline",
          metric: "success_rate",
          operator: ">=",
          expected: 1,
          observed: 1,
          passed: true,
        },
        {
          phase: "fault",
          metric: "fault_rate",
          operator: ">=",
          expected: 1,
          observed: 1,
          passed: true,
        },
        {
          phase: "recovery",
          metric: "success_rate",
          operator: ">=",
          expected: 1,
          observed: 1,
          passed: true,
        },
      ],
    },
  };
}

function json(response, status = 200) {
  return {
    status,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(response),
  };
}

const server = createServer((request, response) => {
  let outgoing;

  if (request.url === "/health") {
    outgoing = json({ status: "ok" });
  } else if (
    request.method === "GET" &&
    request.url?.startsWith("/experiments?")
  ) {
    outgoing = json([
      {
        experiment_id: seededId,
        name: "Checkout resilience",
        started_at: "2026-09-11T06:00:00+00:00",
        completed_at: "2026-09-11T06:00:01+00:00",
        method: "GET",
        path: "/demo/products",
        requests_per_phase: 2,
        interval_ms: 50,
        contract_passed: true,
      },
    ]);
  } else if (
    request.method === "GET" &&
    request.url === `/experiments/${seededId}`
  ) {
    outgoing = json(result(seededId, "Checkout resilience"));
  } else if (
    request.method === "GET" &&
    request.url === `/experiments/${createdId}`
  ) {
    outgoing = json(result(createdId, "Search API recovery"));
  } else if (request.method === "POST" && request.url === "/experiments/run") {
    outgoing = json(result(createdId, "Search API recovery"));
  } else {
    outgoing = json({ detail: "Not found" }, 404);
  }

  response.writeHead(outgoing.status, outgoing.headers);
  response.end(outgoing.body);
});

server.listen(18000, "127.0.0.1", () => {
  console.log("RuptureLab mock backend listening on http://127.0.0.1:18000");
});
