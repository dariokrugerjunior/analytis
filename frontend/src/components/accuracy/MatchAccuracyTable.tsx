import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import type { MatchAccuracyRow, Phase } from "@/lib/api";
import { cn } from "@/lib/utils";

const PHASE_LABELS: Record<Phase, string> = {
  group: "Grupo",
  round_of_16: "Oitavas",
  quarterfinal: "Quartas",
  semifinal: "Semi",
  final: "Final",
};

interface Props {
  rows: MatchAccuracyRow[];
}

export function MatchAccuracyTable({ rows }: Props) {
  const navigate = useNavigate();

  if (rows.length === 0) {
    return <p className="text-sm text-fg-muted">Sem jogos avaliados ainda.</p>;
  }

  return (
    <div className="space-y-2">
      {rows.map((row) => (
        <Card
          key={row.match_id}
          className="p-3 cursor-pointer hover:bg-bg-overlay/40 transition-colors"
          onClick={() => navigate(`/matches/${row.match_id}`)}
        >
          <div className="flex justify-between items-center text-xs text-fg-muted mb-1">
            <span>{new Date(row.kickoff_utc).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })}</span>
            <span>{PHASE_LABELS[row.phase]}</span>
          </div>
          <div className="flex justify-between items-baseline mb-2">
            <span className="text-sm text-fg-primary">{row.home_team} vs {row.away_team}</span>
            <span className="text-sm font-semibold text-fg-primary">{row.home_goals}-{row.away_goals}</span>
          </div>
          <div className="flex gap-3 text-xs">
            {(["1x2", "ou", "btts"] as const).map((mkt) => {
              const p = row.predictions[mkt];
              if (!p) return null;
              return (
                <span
                  key={mkt}
                  className={cn(
                    "inline-flex items-center gap-1",
                    p.hit ? "text-green-400" : "text-red-400",
                  )}
                >
                  {p.hit ? "✓" : "✗"} {mkt.toUpperCase()}: {p.predicted} ({Math.round(p.predicted_prob * 100)}%)
                </span>
              );
            })}
          </div>
        </Card>
      ))}
    </div>
  );
}
