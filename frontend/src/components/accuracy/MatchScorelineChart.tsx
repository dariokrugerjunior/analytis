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

function barColor(credit: number): string {
  if (credit === 1.0) return "#4ade80"; // green-400
  if (credit === 0.5) return "#facc15"; // yellow-400
  return "#f87171";                      // red-400
}

function shortLabel(home: string, away: string): string {
  // 4-letter codes for compact x-axis labels
  const code = (s: string) => s.slice(0, 4).toUpperCase();
  return `${code(home)} × ${code(away)}`;
}

export function MatchScorelineChart({ rows }: Props) {
  // Only rows where scoreline_credit is set (DC model + teams in model)
  const data = rows
    .filter((r) => r.scoreline_credit !== null)
    .sort((a, b) => new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime())
    .map((r) => ({
      label: shortLabel(r.home_team, r.away_team),
      credit_pct: Math.round((r.scoreline_credit ?? 0) * 100),
      actual: `${r.home_goals}-${r.away_goals}`,
      predicted: `${r.scoreline_predicted_home ?? "?"}-${r.scoreline_predicted_away ?? "?"}`,
      home: r.home_team,
      away: r.away_team,
    }));

  if (data.length === 0) {
    return (
      <p className="text-sm text-fg-muted">
        Sem jogos com placar previsto pra esse modelo ainda.
      </p>
    );
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
          angle={-30}
          textAnchor="end"
          height={50}
        />
        <YAxis
          domain={[0, 100]}
          stroke="rgba(255,255,255,0.5)"
          fontSize={11}
          tickFormatter={(v) => `${v}%`}
          ticks={[0, 50, 100]}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "rgb(15, 23, 42)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 8,
          }}
          labelStyle={{ color: "rgba(255,255,255,0.85)" }}
          formatter={(_v: number, _name: string, item: { payload?: typeof data[number] }) => {
            const p = item.payload;
            if (!p) return ["", ""];
            return [
              `${p.credit_pct}% (predito ${p.predicted}, real ${p.actual})`,
              `${p.home} vs ${p.away}`,
            ];
          }}
        />
        <Bar dataKey="credit_pct" radius={[4, 4, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={barColor(d.credit_pct / 100)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
