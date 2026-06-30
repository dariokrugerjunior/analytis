import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MatchAccuracyRow } from "@/lib/api";

interface Props {
  rows: MatchAccuracyRow[];
}

const MARKETS = ["1x2", "ou", "btts"] as const;

function shortLabel(home: string, away: string): string {
  const code = (s: string) => s.slice(0, 3).toUpperCase();
  return `${code(home)}×${code(away)}`;
}

function countHits(row: MatchAccuracyRow): { hits: number; total: number } {
  const predicted = MARKETS.filter((m) => row.predictions[m]);
  const hits = predicted.filter((m) => row.predictions[m]!.hit).length;
  return { hits, total: predicted.length };
}

function barColor(hits: number, total: number): string {
  if (total === 0) return "#6b7280";
  const ratio = hits / total;
  if (ratio === 1) return "#4ade80"; // green-400
  if (ratio >= 0.5) return "#facc15"; // yellow-400
  if (ratio > 0) return "#fb923c"; // orange-400
  return "#f87171"; // red-400
}

interface ChartRow {
  label: string;
  hits: number;
  total: number;
  pct: number;
  home: string;
  away: string;
  score: string;
  details: Array<{ market: string; hit: boolean; predicted: string; prob: number }>;
  scoreline: string | null;
}

export function PerMatchHitsChart({ rows }: Props) {
  const data: ChartRow[] = rows
    .slice()
    .sort((a, b) => new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime())
    .map((r) => {
      const { hits, total } = countHits(r);
      const details = MARKETS.filter((m) => r.predictions[m]).map((m) => {
        const p = r.predictions[m]!;
        return {
          market: m.toUpperCase(),
          hit: p.hit,
          predicted: p.predicted,
          prob: p.predicted_prob,
        };
      });
      const scoreline =
        r.scoreline_predicted_home !== null && r.scoreline_predicted_away !== null
          ? `${r.scoreline_predicted_home}-${r.scoreline_predicted_away}`
          : null;
      const pct = total === 0 ? 0 : Math.round((hits / total) * 100);
      return {
        label: shortLabel(r.home_team, r.away_team),
        hits,
        total,
        pct,
        home: r.home_team,
        away: r.away_team,
        score: `${r.home_goals}-${r.away_goals}`,
        details,
        scoreline,
      };
    });

  if (data.length === 0) {
    return <p className="text-sm text-fg-muted">Sem jogos avaliados ainda.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
        <XAxis
          dataKey="label"
          stroke="rgba(255,255,255,0.5)"
          fontSize={10}
          interval={0}
          angle={-35}
          textAnchor="end"
          height={56}
        />
        <YAxis
          domain={[0, 100]}
          ticks={[0, 50, 100]}
          stroke="rgba(255,255,255,0.5)"
          fontSize={11}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
          contentStyle={{
            backgroundColor: "rgb(15, 23, 42)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: "rgba(255,255,255,0.85)" }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const first = payload[0];
            if (!first) return null;
            const p = first.payload as ChartRow;
            return (
              <div className="rounded-md border border-white/10 bg-slate-900 px-3 py-2 text-xs">
                <div className="font-medium text-fg-primary">
                  {p.home} {p.score} {p.away}
                </div>
                <div className="text-fg-muted mt-1">
                  {p.hits}/{p.total} mercados ({p.pct}%)
                </div>
                <div className="mt-2 space-y-1">
                  {p.details.map((d) => (
                    <div
                      key={d.market}
                      className={d.hit ? "text-green-400" : "text-red-400"}
                    >
                      {d.hit ? "✓" : "✗"} {d.market}: {d.predicted} (
                      {Math.round(d.prob * 100)}%)
                    </div>
                  ))}
                  {p.scoreline && (
                    <div className="text-fg-muted">Placar previsto: {p.scoreline}</div>
                  )}
                </div>
              </div>
            );
          }}
        />
        <Bar dataKey="pct" radius={[4, 4, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={barColor(d.hits, d.total)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
