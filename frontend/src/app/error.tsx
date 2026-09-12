"use client";

import { AlertTriangle } from "lucide-react";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ reset }: ErrorPageProps) {
  return (
    <div className="flex min-h-[65vh] items-center justify-center">
      <div className="max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-amber-400/15 bg-amber-400/7">
          <AlertTriangle className="h-5 w-5 text-amber-300" />
        </div>
        <h1 className="mt-5 text-xl font-semibold text-zinc-200">
          Unable to load RuptureLab
        </h1>
        <p className="mt-2 text-sm leading-6 text-zinc-500">
          Check that the control API and PostgreSQL are running, then retry this
          request.
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-5 rounded-lg border border-white/8 bg-white/[0.035] px-4 py-2 text-sm font-semibold text-zinc-300 transition hover:bg-white/[0.06]"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
