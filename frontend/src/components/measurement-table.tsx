import type { PhaseResult } from "@/lib/api/schemas";
import { formatLatency } from "@/lib/format";

type MeasurementRow = {
  key: string;
  measurement: PhaseResult["measurements"][number];
  phase: PhaseResult["phase"];
  sequenceNumber: number;
};

function buildRows(phases: PhaseResult[]): MeasurementRow[] {
  return phases.flatMap((phase) => {
    let sequenceNumber = 0;

    return phase.measurements.map((measurement) => {
      sequenceNumber += 1;

      return {
        key: `${phase.phase}-${sequenceNumber}`,
        measurement,
        phase: phase.phase,
        sequenceNumber,
      };
    });
  });
}

export function MeasurementTable({ phases }: { phases: PhaseResult[] }) {
  const rows = buildRows(phases);

  return (
    <section className="overflow-hidden rounded-2xl border border-white/6 bg-white/[0.02]">
      <div className="border-b border-white/6 px-5 py-4">
        <h2 className="text-sm font-semibold text-zinc-200">Request trace</h2>
        <p className="mt-1 text-[11px] text-zinc-500">
          Individual measurements captured across baseline, fault and recovery
          phases.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-left">
          <thead>
            <tr className="border-b border-white/6 text-[10px] font-semibold tracking-wide text-zinc-700 uppercase">
              <th className="px-5 py-3">Phase</th>
              <th className="px-5 py-3">Request</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Latency</th>
              <th className="px-5 py-3">Outcome</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {rows.map(({ key, measurement, phase, sequenceNumber }) => (
              <tr key={key} className="text-xs text-zinc-500">
                <td className="px-5 py-3 font-mono text-[10px] uppercase">
                  {phase}
                </td>
                <td className="px-5 py-3 font-mono">{sequenceNumber}</td>
                <td className="px-5 py-3 font-mono">
                  {measurement.status_code ?? "—"}
                </td>
                <td className="px-5 py-3 font-mono">
                  {formatLatency(measurement.duration_ms)}
                </td>
                <td className="px-5 py-3">
                  {measurement.error ??
                    measurement.fault ??
                    (measurement.successful ? "success" : "failed")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
