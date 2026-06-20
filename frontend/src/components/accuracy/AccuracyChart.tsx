import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Phase, TimeseriesPoint } from "@/lib/api";

const PHASE_LABELS: Record<Phase, string> = {
  group: "Grupo",
  round_of_16: "Oitavas",
  quarterfinal: "Quartas",
  semifinal: "Semi",
  final: "Final",
};

interface Props {
  data: TimeseriesPoint[];
}

export function AccuracyChart({ data }: Props) {
  const rows = data.map((p) => ({
    phase: PHASE_LABELS[p.phase],
    n: p.n,
    "1X2": Math.round(p.cumulative["1x2"] * 1000) / 10,
    OU: Math.round(p.cumulative.ou * 1000) / 10,
    BTTS: Math.round(p.cumulative.btts * 1000) / 10,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={rows} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="phase" stroke="rgba(255,255,255,0.5)" fontSize={11} />
        <YAxis domain={[0, 100]} stroke="rgba(255,255,255,0.5)" fontSize={11} tickFormatter={(v) => `${v}%`} />
        <Tooltip
          contentStyle={{ backgroundColor: "rgb(15, 23, 42)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
          labelStyle={{ color: "rgba(255,255,255,0.85)" }}
          formatter={(v: number) => `${v}%`}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="1X2" stroke="#38bdf8" strokeWidth={2} dot={{ r: 3 }} />
        <Line type="monotone" dataKey="OU" stroke="#4ade80" strokeWidth={2} dot={{ r: 3 }} />
        <Line type="monotone" dataKey="BTTS" stroke="#c084fc" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
