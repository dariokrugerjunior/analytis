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

const MARKETS = ["1x2", "ou", "btts"] as const;

interface Props {
  rows: MatchAccuracyRow[];
}

function scoreBadgeClass(hits: number, total: number): string {
  if (total === 0) return "bg-white/5 text-fg-muted";
  const ratio = hits / total;
  if (ratio === 1) return "bg-green-500/15 text-green-300";
  if (ratio >= 0.5) return "bg-yellow-500/15 text-yellow-300";
  if (ratio > 0) return "bg-orange-500/15 text-orange-300";
  return "bg-red-500/15 text-red-300";
}

export function MatchAccuracyTable({ rows }: Props) {
  const navigate = useNavigate();

  if (rows.length === 0) {
    return <p className="text-sm text-fg-muted">Sem jogos avaliados ainda.</p>;
  }

  const sorted = rows
    .slice()
    .sort((a, b) => new Date(b.kickoff_utc).getTime() - new Date(a.kickoff_utc).getTime());

  return (
    <div className="space-y-2">
      {sorted.map((row) => {
        const predicted = MARKETS.filter((m) => row.predictions[m]);
        const hits = predicted.filter((m) => row.predictions[m]!.hit).length;
        const total = predicted.length;
        const scoreline =
          row.scoreline_predicted_home !== null && row.scoreline_predicted_away !== null
            ? `${row.scoreline_predicted_home}-${row.scoreline_predicted_away}`
            : null;

        return (
          <Card
            key={row.match_id}
            className="p-3 cursor-pointer hover:bg-bg-overlay/40 transition-colors"
            onClick={() => navigate(`/matches/${row.match_id}`)}
          >
            <div className="flex justify-between items-center text-xs text-fg-muted mb-1">
              <span>
                {new Date(row.kickoff_utc).toLocaleDateString("pt-BR", {
                  day: "2-digit",
                  month: "2-digit",
                })}
              </span>
              <span>{PHASE_LABELS[row.phase]}</span>
            </div>
            <div className="flex justify-between items-baseline mb-2 gap-3">
              <span className="text-sm text-fg-primary truncate">
                {row.home_team} vs {row.away_team}
              </span>
              <div className="flex items-baseline gap-2 shrink-0">
                {scoreline && (
                  <span className="text-xs text-fg-muted font-mono">
                    prev {scoreline} →
                  </span>
                )}
                <span className="text-sm font-semibold text-fg-primary">
                  {row.home_goals}-{row.away_goals}
                </span>
                <span
                  className={cn(
                    "rounded-md px-2 py-0.5 text-xs font-medium",
                    scoreBadgeClass(hits, total),
                  )}
                >
                  {hits}/{total}
                </span>
              </div>
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
              {predicted.map((mkt) => {
                const p = row.predictions[mkt]!;
                return (
                  <span
                    key={mkt}
                    className={cn(
                      "inline-flex items-center gap-1",
                      p.hit ? "text-green-400" : "text-red-400",
                    )}
                  >
                    {p.hit ? "✓" : "✗"} {mkt.toUpperCase()}: {p.predicted} (
                    {Math.round(p.predicted_prob * 100)}%)
                  </span>
                );
              })}
            </div>
          </Card>
        );
      })}
    </div>
  );
}
