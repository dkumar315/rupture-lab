import { Check, Minus, X } from "lucide-react";

export function ContractStatus({ value }: { value: boolean | null }) {
  if (value === null) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-zinc-700/60 bg-zinc-800/40 px-2.5 py-1 text-xs font-medium text-zinc-400">
        <Minus className="h-3 w-3" /> Not evaluated
      </span>
    );
  }

  return value ? (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/8 px-2.5 py-1 text-xs font-medium text-emerald-300">
      <Check className="h-3 w-3" /> Passed
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-400/20 bg-rose-400/8 px-2.5 py-1 text-xs font-medium text-rose-300">
      <X className="h-3 w-3" /> Failed
    </span>
  );
}
