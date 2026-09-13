const phaseSkeletons = ["baseline", "fault", "recovery"] as const;

export default function ExperimentLoading() {
  return (
    <div className="animate-pulse space-y-8">
      <div className="h-4 w-28 rounded bg-zinc-900" />

      <div className="space-y-3 border-b border-white/6 pb-7">
        <div className="h-3 w-32 rounded bg-zinc-900" />
        <div className="h-10 w-96 max-w-full rounded-lg bg-zinc-900" />
        <div className="h-4 w-[620px] max-w-full rounded bg-zinc-900" />
      </div>

      <div className="h-24 rounded-2xl border border-white/5 bg-white/[0.02]" />

      <div className="grid gap-4 lg:grid-cols-3">
        {phaseSkeletons.map((phase) => (
          <div
            key={phase}
            className="h-56 rounded-2xl border border-white/5 bg-white/[0.02]"
          />
        ))}
      </div>

      <div className="h-96 rounded-2xl border border-white/5 bg-white/[0.02]" />
    </div>
  );
}
