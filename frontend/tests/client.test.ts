import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getExperiment,
  getHealth,
  listExperiments,
  openExperimentEventStream,
  runExperiment,
  startExperiment,
} from "@/lib/api/client";
import {
  buildExperimentSpec,
  defaultExperimentFormValues,
} from "@/lib/experiment";

const experimentId = "11111111-1111-4111-8111-111111111111";

const result = {
  experiment_id: experimentId,
  name: "Products",
  started_at: "2026-09-11T06:00:00Z",
  spec: buildExperimentSpec(defaultExperimentFormValues),
  phases: [],
  contract_evaluation: null,
};

function response(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  delete process.env.RUPTURELAB_API_URL;
});

describe("API client", () => {
  it("uses the configured API URL and lists experiments", async () => {
    process.env.RUPTURELAB_API_URL = "http://api.test/";
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(response([]));

    await expect(listExperiments(10, 5)).resolves.toEqual([]);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/experiments?limit=10&offset=5",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("reads experiment results and posts new runs", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response(result))
      .mockResolvedValueOnce(response(result));
    await expect(getExperiment(experimentId)).resolves.toEqual(result);
    await expect(runExperiment(result.spec)).resolves.toEqual(result);
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://127.0.0.1:8000/experiments/run",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(result.spec),
      }),
    );
  });

  it("starts experiments and opens resumable event streams", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        response({ experiment_id: experimentId, name: result.name }, 202),
      )
      .mockResolvedValueOnce(
        new Response("data: {}\n\n", {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      )
      .mockResolvedValueOnce(
        new Response("data: {}\n\n", {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      );

    await expect(startExperiment(result.spec)).resolves.toEqual({
      experiment_id: experimentId,
      name: result.name,
    });
    await expect(
      openExperimentEventStream(experimentId),
    ).resolves.toBeInstanceOf(Response);
    const controller = new AbortController();
    await expect(
      openExperimentEventStream(experimentId, "7", controller.signal),
    ).resolves.toBeInstanceOf(Response);

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `http://127.0.0.1:8000/experiments/${experimentId}/events`,
      expect.objectContaining({
        headers: { Accept: "text/event-stream" },
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      `http://127.0.0.1:8000/experiments/${experimentId}/events`,
      expect.objectContaining({
        headers: { Accept: "text/event-stream", "Last-Event-ID": "7" },
        signal: controller.signal,
      }),
    );
  });

  it("normalizes event stream HTTP and network failures", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ detail: "Stream missing" }, 404))
      .mockRejectedValueOnce(new Error("stream disconnected"))
      .mockRejectedValueOnce("offline");

    await expect(openExperimentEventStream(experimentId)).rejects.toMatchObject(
      {
        message: "Stream missing",
        status: 404,
      },
    );
    await expect(openExperimentEventStream(experimentId)).rejects.toMatchObject(
      {
        message: "stream disconnected",
        status: 503,
      },
    );
    await expect(openExperimentEventStream(experimentId)).rejects.toMatchObject(
      {
        message: "RuptureLab API is unavailable",
        status: 503,
      },
    );
  });

  it("reports healthy and unhealthy backend states", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      response({ status: "ok" }),
    );
    await expect(getHealth()).resolves.toBe(true);

    vi.mocked(fetch).mockRejectedValueOnce(new Error("connection refused"));
    await expect(getHealth()).resolves.toBe(false);
  });

  it("surfaces API detail messages and fallback status messages", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ detail: "Experiment busy" }, 409))
      .mockResolvedValueOnce(response({ reason: "bad" }, 500))
      .mockResolvedValueOnce(new Response("not-json", { status: 502 }));

    await expect(getExperiment(experimentId)).rejects.toMatchObject({
      name: "ApiError",
      message: "Experiment busy",
      status: 409,
    });
    await expect(getExperiment(experimentId)).rejects.toThrow(
      "RuptureLab API returned 500",
    );
    await expect(getExperiment(experimentId)).rejects.toThrow(
      "RuptureLab API returned 502",
    );
  });

  it("normalizes network failures into ApiError", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new Error("socket closed"))
      .mockRejectedValueOnce("offline");

    await expect(getExperiment(experimentId)).rejects.toMatchObject({
      name: "ApiError",
      message: "socket closed",
      status: 503,
    });
    await expect(getExperiment(experimentId)).rejects.toMatchObject({
      name: "ApiError",
      message: "RuptureLab API is unavailable",
      status: 503,
    });
  });
});
