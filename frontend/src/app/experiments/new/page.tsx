import type { Metadata } from "next";

import { ExperimentForm } from "@/components/experiment-form";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "New experiment",
};

export default function NewExperimentPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Experiment builder"
        title="Design the failure before it happens."
        description="Choose the traffic pattern, inject one controlled disruption, and define the contract that recovery must satisfy."
      />
      <ExperimentForm />
    </div>
  );
}
