import { NextResponse } from "next/server";

import { ApiError, openExperimentEventStream } from "@/lib/api/client";

interface ExperimentEventsRouteProps {
  params: Promise<{ id: string }>;
}

export async function GET(
  request: Request,
  { params }: ExperimentEventsRouteProps,
) {
  const { id } = await params;
  const lastEventId = request.headers.get("Last-Event-ID") ?? undefined;

  try {
    const response = await openExperimentEventStream(
      id,
      lastEventId,
      request.signal,
    );

    return new Response(response.body, {
      status: response.status,
      headers: {
        "Cache-Control": "no-cache, no-transform",
        "Content-Type": "text/event-stream",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.message },
        { status: error.status },
      );
    }

    return NextResponse.json(
      { detail: "Unable to open experiment event stream" },
      { status: 500 },
    );
  }
}
