import type { ZodType } from "zod";

import {
  experimentResultSchema,
  experimentStartSchema,
  experimentSummaryListSchema,
  healthSchema,
  type ExperimentResult,
  type ExperimentSpec,
  type ExperimentStart,
  type ExperimentSummary,
} from "@/lib/api/schemas";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function backendUrl(path: string): string {
  const baseUrl = process.env.RUPTURELAB_API_URL ?? "http://127.0.0.1:8000";
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

async function readError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    return typeof payload.detail === "string"
      ? payload.detail
      : `RuptureLab API returned ${response.status}`;
  } catch {
    return `RuptureLab API returned ${response.status}`;
  }
}

async function request<T>(
  path: string,
  schema: ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(backendUrl(path), {
      ...init,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
    });
  } catch (error) {
    throw new ApiError(
      error instanceof Error ? error.message : "RuptureLab API is unavailable",
      503,
    );
  }

  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }

  return schema.parse(await response.json());
}

export async function getHealth(): Promise<boolean> {
  try {
    await request("/health", healthSchema);
    return true;
  } catch {
    return false;
  }
}

export function listExperiments(
  limit = 50,
  offset = 0,
): Promise<ExperimentSummary[]> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  return request(`/experiments?${params}`, experimentSummaryListSchema);
}

export function getExperiment(experimentId: string): Promise<ExperimentResult> {
  return request(`/experiments/${experimentId}`, experimentResultSchema);
}

export function runExperiment(spec: ExperimentSpec): Promise<ExperimentResult> {
  return request("/experiments/run", experimentResultSchema, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(spec),
  });
}

export function startExperiment(
  spec: ExperimentSpec,
): Promise<ExperimentStart> {
  return request("/experiments/start", experimentStartSchema, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(spec),
  });
}

export async function openExperimentEventStream(
  experimentId: string,
  lastEventId?: string,
  signal?: AbortSignal,
): Promise<Response> {
  let response: Response;

  try {
    response = await fetch(backendUrl(`/experiments/${experimentId}/events`), {
      cache: "no-store",
      headers: {
        Accept: "text/event-stream",
        ...(lastEventId ? { "Last-Event-ID": lastEventId } : {}),
      },
      ...(signal ? { signal } : {}),
    });
  } catch (error) {
    throw new ApiError(
      error instanceof Error ? error.message : "RuptureLab API is unavailable",
      503,
    );
  }

  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }

  return response;
}
