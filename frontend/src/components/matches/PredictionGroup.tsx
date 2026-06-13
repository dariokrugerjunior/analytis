import { cn } from "@/lib/utils";
import type { Prediction } from "@/lib/api";

interface OutcomeRow {
  label: string;
  outcome: string;
  colorClass: string;
}

interface Props {
  title: string;
  predictions: Prediction[];
  outcomes: OutcomeRow[];
}

function fmtPct(v: number) {
  return `${(v * 100).toFixed(1)}%`;
}

export function PredictionGroup({ title, predictions, outcomes }: Props) {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
        {title}
      </h3>
      <div className="space-y-2 rounded-lg border border-white/10 bg-bg-elevated p-4">
        {outcomes.map(({ label, outcome, colorClass }) => {
          const pred = predictions.find((p) => p.outcome === outcome);
          const prob = pred?.prob ?? 0;
          return (
            <div key={outcome} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span>{label}</span>
                <span className="font-mono text-fg-muted">{fmtPct(prob)}</span>
              </div>
              <div className="h-3 rounded-full bg-bg-overlay overflow-hidden">
                <div
                  className={cn("h-full rounded-full", colorClass)}
                  style={{ width: `${Math.max(2, prob * 100)}%` }}
                />
              </div>
              {pred && (
                <div className="text-[10px] text-fg-subtle font-mono">
                  CI {fmtPct(pred.ci_low)} – {fmtPct(pred.ci_high)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
