import { NextResponse } from "next/server";

import { ApiError, startExperiment } from "@/lib/api/client";
import { experimentSpecSchema } from "@/lib/api/schemas";

export async function POST(request: Request) {
  let payload: unknown;

  try {
    payload = await request.json();
  } catch {
    return NextResponse.json(
      { detail: "Invalid JSON request body" },
      { status: 400 },
    );
  }

  const parsed = experimentSpecSchema.safeParse(payload);
  if (!parsed.success) {
    return NextResponse.json(
      { detail: "Invalid experiment configuration" },
      { status: 400 },
    );
  }

  try {
    return NextResponse.json(await startExperiment(parsed.data), {
      status: 202,
    });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.message },
        { status: error.status },
      );
    }

    return NextResponse.json(
      { detail: "Unable to start experiment" },
      { status: 500 },
    );
  }
}
