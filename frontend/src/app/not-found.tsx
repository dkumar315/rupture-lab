import Link from "next/link";
import { SearchX } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-[65vh] items-center justify-center">
      <div className="max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-white/7 bg-white/[0.025]">
          <SearchX className="h-5 w-5 text-zinc-500" />
        </div>
        <h1 className="mt-5 text-xl font-semibold text-zinc-200">
          Experiment not found
        </h1>
        <p className="mt-2 text-sm leading-6 text-zinc-500">
          The persisted experiment ID does not exist or is no longer available.
        </p>
        <Link
          href="/"
          className="mt-5 inline-block text-sm font-semibold text-emerald-400 transition hover:text-emerald-300"
        >
          Return to overview
        </Link>
      </div>
    </div>
  );
}
