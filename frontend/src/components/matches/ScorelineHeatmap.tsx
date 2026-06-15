import { Fragment, useMemo } from "react";
import type { ScorelineGrid } from "@/lib/api";

interface Props {
  data: ScorelineGrid;
}

function fmtPct(v: number, digits = 1) {
  return `${(v * 100).toFixed(digits)}%`;
}

function regionFor(home: number, away: number): "home" | "draw" | "away" {
  if (home > away) return "home";
  if (home < away) return "away";
  return "draw";
}

const regionRgb: Record<"home" | "draw" | "away", string> = {
  home: "16, 185, 129",
  draw: "156, 163, 175",
  away: "239, 68, 68",
};

export function ScorelineHeatmap({ data }: Props) {
  const { grid, home_team, away_team, top_scorelines, most_likely, lambda_home, lambda_away } =
    data;

  const maxProb = useMemo(() => {
    let m = 0;
    for (const row of grid) for (const v of row) if (v > m) m = v;
    return m || 1;
  }, [grid]);

  const size = grid.length;

  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
          Placar exato
        </h3>
        <span className="text-[11px] text-fg-subtle font-mono">
          λ {lambda_home.toFixed(2)} – {lambda_away.toFixed(2)}
        </span>
      </div>

      <div className="rounded-lg border border-white/10 bg-bg-elevated p-3">
        <div className="text-[10px] text-fg-subtle uppercase tracking-wide mb-2 text-center">
          {away_team} →
        </div>
        <div
          className="grid gap-1"
          style={{ gridTemplateColumns: `auto repeat(${size}, minmax(0, 1fr))` }}
        >
          <div />
          {Array.from({ length: size }, (_, j) => (
            <div
              key={`col-${j}`}
              className="text-[10px] font-mono text-fg-muted text-center"
            >
              {j}
            </div>
          ))}

          {grid.map((row, i) => (
            <Fragment key={`row-${i}`}>
              <div className="text-[10px] font-mono text-fg-muted flex items-center justify-end pr-1">
                {i}
              </div>
              {row.map((p, j) => {
                const region = regionFor(i, j);
                const intensity = Math.min(1, p / maxProb);
                const isPeak = i === most_likely.home && j === most_likely.away;
                const showText = p >= 0.005;
                return (
                  <div
                    key={`cell-${i}-${j}`}
                    className="aspect-square rounded text-[10px] font-mono flex items-center justify-center"
                    style={{
                      backgroundColor: `rgba(${regionRgb[region]}, ${0.08 + 0.72 * intensity})`,
                      outline: isPeak ? "1px solid #fbbf24" : undefined,
                      color: intensity > 0.5 ? "#0f172a" : "#f1f5f9",
                    }}
                    title={`${home_team} ${i} – ${j} ${away_team}: ${fmtPct(p, 2)}`}
                  >
                    {showText ? (p * 100).toFixed(0) : ""}
                  </div>
                );
              })}
            </Fragment>
          ))}
        </div>
        <div className="text-[10px] text-fg-subtle uppercase tracking-wide mt-2 text-center">
          ↑ {home_team}
        </div>
      </div>

      <div className="rounded-lg border border-white/10 bg-bg-elevated p-3 space-y-1.5">
        <div className="flex justify-between items-center mb-1">
          <span className="text-[11px] uppercase tracking-wide text-fg-muted">
            Top placares
          </span>
          <span className="text-[10px] text-fg-subtle">
            mais provável: {most_likely.home}-{most_likely.away}
          </span>
        </div>
        {top_scorelines.map((s, idx) => {
          const region = regionFor(s.home, s.away);
          const topProb = top_scorelines[0]?.prob ?? s.prob;
          const pct = (s.prob / topProb) * 100;
          return (
            <div key={`top-${idx}`} className="space-y-0.5">
              <div className="flex justify-between text-xs">
                <span className="font-mono">
                  {s.home} – {s.away}
                </span>
                <span className="font-mono text-fg-muted">{fmtPct(s.prob)}</span>
              </div>
              <div className="h-1.5 rounded-full bg-bg-overlay overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.max(2, pct)}%`,
                    backgroundColor: `rgb(${regionRgb[region]})`,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-[10px] text-fg-subtle italic">
        Verde = vitória mandante · cinza = empate · vermelho = vitória visitante. Quanto mais
        opaco, maior a probabilidade. Números nas células são % (arredondado).
      </p>
    </section>
  );
}
