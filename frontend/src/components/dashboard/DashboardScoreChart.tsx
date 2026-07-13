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
import type { DashboardGame } from "@/lib/api";

interface Props {
  games: DashboardGame[];
}

// Three categorical tiers. Redundantly encoded by bar height + labels + legend,
// so colour is never the sole channel (CVD-safe). Matches the app's chart tokens.
const TIER = {
  100: { color: "#4ade80", label: "Placar exato (100)" },
  50: { color: "#facc15", label: "Resultado certo (50)" },
  0: { color: "#f87171", label: "Errou (0)" },
} as const;

function tierColor(points: number): string {
  if (points >= 100) return TIER[100].color;
  if (points >= 50) return TIER[50].color;
  return TIER[0].color;
}

function shortLabel(home: string, away: string): string {
  const code = (s: string) => s.slice(0, 3).toUpperCase();
  return `${code(home)}×${code(away)}`;
}

interface ChartRow {
  label: string;
  points: number;
  home: string;
  away: string;
  predicted_score: string;
  actual_score: string;
}

export function DashboardScoreChart({ games }: Props) {
  const data: ChartRow[] = games
    .slice()
    .sort((a, b) => new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime())
    .map((g) => ({
      label: shortLabel(g.home_team, g.away_team),
      points: g.points,
      home: g.home_team,
      away: g.away_team,
      predicted_score: g.predicted_score,
      actual_score: g.actual_score,
    }));

  if (data.length === 0) {
    return <p className="text-sm text-fg-muted">Sem jogos avaliados ainda.</p>;
  }

  return (
    <div>
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
            tickFormatter={(v) => `${v}`}
          />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const first = payload[0];
              if (!first) return null;
              const p = first.payload as ChartRow;
              return (
                <div className="rounded-md border border-white/10 bg-slate-900 px-3 py-2 text-xs">
                  <div className="font-medium text-fg-primary">
                    {p.home} × {p.away}
                  </div>
                  <div className="text-fg-muted mt-1">
                    Previsto {p.predicted_score} · Real {p.actual_score}
                  </div>
                  <div className="mt-1 font-semibold" style={{ color: tierColor(p.points) }}>
                    {p.points} pontos
                  </div>
                </div>
              );
            }}
          />
          <Bar
            dataKey="points"
            radius={[4, 4, 0, 0]}
            background={{ fill: "rgba(255,255,255,0.05)", radius: 4 }}
          >
            {data.map((d, i) => (
              <Cell key={i} fill={tierColor(d.points)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1" aria-label="Legenda">
        {([100, 50, 0] as const).map((tier) => (
          <li key={tier} className="flex items-center gap-1.5 text-xs text-fg-muted">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: TIER[tier].color }}
              aria-hidden="true"
            />
            {TIER[tier].label}
          </li>
        ))}
      </ul>
    </div>
  );
}
