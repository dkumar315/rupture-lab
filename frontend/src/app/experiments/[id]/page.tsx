import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Clock3, Hash, Route, type LucideIcon } from "lucide-react";

import { ContractPanel } from "@/components/contract-panel";
import { MeasurementTable } from "@/components/measurement-table";
import { PageHeader } from "@/components/page-header";
import { PhaseResults } from "@/components/phase-results";
import { ApiError, getExperiment } from "@/lib/api/client";
import type { ExperimentResult } from "@/lib/api/schemas";
import { formatDateTime } from "@/lib/format";

interface ExperimentPageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({
  params,
}: ExperimentPageProps): Promise<Metadata> {
  const { id } = await params;
  return { title: `Experiment ${id.slice(0, 8)}` };
}

export default async function ExperimentPage({ params }: ExperimentPageProps) {
  const { id } = await params;
  let result: ExperimentResult;

  try {
    result = await getExperiment(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  return (
    <div className="space-y-8">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-500 transition hover:text-zinc-300"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back to overview
      </Link>

      <PageHeader
        eyebrow="Experiment result"
        title={result.name}
        description="Compare phase behavior, inspect the resilience verdict, and trace every measured request from the persisted run."
        action={
          <Link
            href="/experiments/new"
            className="rounded-xl border border-white/8 bg-white/[0.035] px-4 py-2.5 text-sm font-semibold whitespace-nowrap text-zinc-300 transition hover:bg-white/[0.06] hover:text-white"
          >
            Run another
          </Link>
        }
      />

      <section className="grid gap-3 rounded-2xl border border-white/6 bg-white/[0.02] p-4 sm:grid-cols-3 sm:p-5">
        <ResultMeta
          icon={Hash}
          label="Experiment ID"
          value={result.experiment_id}
          mono
        />
        <ResultMeta
          icon={Route}
          label="Target"
          value={`${result.spec.method} ${result.spec.path}`}
          mono
        />
        <ResultMeta
          icon={Clock3}
          label="Started"
          value={formatDateTime(result.started_at)}
        />
      </section>

      <section>
        <div className="mb-3">
          <h2 className="text-sm font-semibold text-zinc-200">
            Phase comparison
          </h2>
          <p className="mt-1 text-xs text-zinc-500">
            Baseline → controlled failure → recovery
          </p>
        </div>
        <PhaseResults phases={result.phases} />
      </section>

      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_420px]">
        <MeasurementTable phases={result.phases} />
        <ContractPanel result={result} />
      </div>
    </div>
  );
}

function ResultMeta({
  icon: Icon,
  label,
  value,
  mono = false,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex min-w-0 items-start gap-3 rounded-xl px-2 py-2">
      <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-700" />
      <div className="min-w-0">
        <p className="text-[10px] font-semibold tracking-wide text-zinc-700 uppercase">
          {label}
        </p>
        <p
          className={`mt-1 truncate text-xs text-zinc-400 ${mono ? "font-mono" : ""}`}
        >
          {value}
        </p>
      </div>
    </div>
  );
}
