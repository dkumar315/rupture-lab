import type { Metadata } from "next";

import { LiveExperiment } from "@/components/live-experiment";

interface LiveExperimentPageProps {
  params: Promise<{ id: string }>;
}

export const metadata: Metadata = {
  title: "Live experiment",
};

export default async function LiveExperimentPage({
  params,
}: LiveExperimentPageProps) {
  const { id } = await params;
  return <LiveExperiment experimentId={id} />;
}
