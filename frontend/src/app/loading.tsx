const metricSkeletons = ["runs", "contracts", "latency", "status"] as const;

export default function Loading() {
  return (
    <div className="animate-pulse space-y-8">
      <div className="space-y-3 border-b border-white/6 pb-7">
        <div className="h-3 w-28 rounded bg-zinc-900" />
        <div className="h-10 w-80 max-w-full rounded-lg bg-zinc-900" />
        <div className="h-4 w-[540px] max-w-full rounded bg-zinc-900" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metricSkeletons.map((metric) => (
          <div
            key={metric}
            className="h-32 rounded-2xl border border-white/5 bg-white/[0.02]"
          />
        ))}
      </div>
      <div className="h-96 rounded-2xl border border-white/5 bg-white/[0.02]" />
    </div>
  );
}
