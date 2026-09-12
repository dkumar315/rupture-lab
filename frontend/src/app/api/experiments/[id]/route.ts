import { NextResponse } from "next/server";

import { ApiError, getExperiment } from "@/lib/api/client";

interface ExperimentRouteProps {
  params: Promise<{ id: string }>;
}

export async function GET(_: Request, { params }: ExperimentRouteProps) {
  const { id } = await params;

  try {
    return NextResponse.json(await getExperiment(id));
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.message },
        { status: error.status },
      );
    }

    return NextResponse.json(
      { detail: "Unable to load experiment" },
      { status: 500 },
    );
  }
}
