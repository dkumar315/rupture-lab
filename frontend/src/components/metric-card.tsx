export function MetricCard({
  label,
  value,
  detail,
  accent = false,
}: {
  label: string;
  value: string;
  detail: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-white/6 bg-white/[0.025] p-5 shadow-[0_18px_50px_rgba(0,0,0,0.18)]">
      <p className="text-xs font-medium text-zinc-500">{label}</p>
      <div
        className={`mt-3 text-2xl font-semibold tracking-[-0.03em] ${accent ? "text-emerald-300" : "text-zinc-100"}`}
      >
        {value}
      </div>
      <p className="mt-1.5 text-xs leading-5 text-zinc-500">{detail}</p>
    </div>
  );
}
