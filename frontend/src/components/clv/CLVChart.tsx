import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/components/ui/card";
import { useClvTimeline } from "@/hooks/useClvTimeline";

interface Props {
  modelVersion: string;
}

export function CLVChart({ modelVersion }: Props) {
  const { data, isLoading, isError } = useClvTimeline(modelVersion);

  if (isLoading) {
    return (
      <Card className="p-4 h-64 flex items-center justify-center text-fg-muted text-sm">
        Carregando timeline...
      </Card>
    );
  }
  if (isError || !data) {
    return (
      <Card className="p-4 h-64 flex items-center justify-center text-fg-muted text-sm">
        Sem dados de CLV para esse modelo.
      </Card>
    );
  }

  if (data.points.length === 0) {
    return (
      <Card className="p-4 h-64 flex items-center justify-center text-fg-muted text-sm">
        Nenhuma aposta com CLV registrado ainda — rode <code>analytis bets track-clv</code> após os jogos.
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <h4 className="text-sm font-medium mb-2">{modelVersion}</h4>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: "#94a3b8" }}
              tickFormatter={(d: string) => d.slice(5)}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#94a3b8" }}
              width={40}
            />
            <Tooltip
              contentStyle={{
                background: "#1e1b4b",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 6,
                fontSize: 12,
              }}
              labelStyle={{ color: "#f1f5f9" }}
            />
            <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="cumulative_clv"
              stroke="#fbbf24"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11px] text-fg-subtle mt-2">
        {data.points.length} ponto(s) ·{" "}
        {data.points[data.points.length - 1]?.n_bets_cumulative} bets com CLV total
      </p>
    </Card>
  );
}
