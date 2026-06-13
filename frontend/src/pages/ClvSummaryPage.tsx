import { useMemo } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";
import { StatCard } from "@/components/clv/StatCard";
import { CLVChart } from "@/components/clv/CLVChart";
import { useClvSummary } from "@/hooks/useClvSummary";

function fmtNumber(v: number | null | undefined, digits = 3): string {
  if (v === null || v === undefined) return "—";
  return v.toFixed(digits);
}

function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${(v * 100).toFixed(2)}%`;
}

export default function ClvSummaryPage() {
  const { data, isLoading, isError } = useClvSummary();

  const stats = useMemo(() => {
    if (!data?.items) return { total: 0, meanCLV: null as number | null, meanEdge: null as number | null };
    let total = 0;
    let weightedCLV = 0;
    let weightedEdge = 0;
    let clvBets = 0;
    let edgeBets = 0;
    for (const it of data.items) {
      total += it.n_bets;
      if (it.mean_clv !== null) {
        weightedCLV += it.mean_clv * it.n_with_clv;
        clvBets += it.n_with_clv;
      }
      if (it.median_edge !== null) {
        weightedEdge += it.median_edge * it.n_bets;
        edgeBets += it.n_bets;
      }
    }
    return {
      total,
      meanCLV: clvBets > 0 ? weightedCLV / clvBets : null,
      meanEdge: edgeBets > 0 ? weightedEdge / edgeBets : null,
    };
  }, [data]);

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between gap-2">
        <h2 className="text-xl font-semibold">CLV Summary</h2>
      </header>

      {isLoading && (
        <div className="grid grid-cols-3 gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      )}

      {isError && (
        <p className="text-sm text-brand-danger">
          Não foi possível carregar o resumo de CLV.
        </p>
      )}

      {!isLoading && !isError && (
        <>
          <div className="grid grid-cols-3 gap-3">
            <StatCard label="Total de bets" value={String(stats.total)} />
            <StatCard
              label="CLV médio"
              value={fmtNumber(stats.meanCLV)}
              variant={
                stats.meanCLV === null
                  ? "default"
                  : stats.meanCLV > 0
                  ? "positive"
                  : "negative"
              }
              {...(stats.meanCLV === null
                ? { hint: "Sem bets com closing" }
                : {})}
            />
            <StatCard
              label="Edge mediano"
              value={fmtPct(stats.meanEdge)}
              variant={
                stats.meanEdge === null
                  ? "default"
                  : stats.meanEdge > 0
                  ? "positive"
                  : "negative"
              }
            />
          </div>

          <section className="space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
              Por modelo
            </h3>
            {data && data.items.length === 0 && (
              <p className="text-fg-muted text-sm py-8 text-center">
                Nenhum value bet registrado ainda.
              </p>
            )}
            {data && data.items.length > 0 && (
              <Card className="overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-fg-muted border-b border-white/10">
                      <th className="px-4 py-2 font-medium">Modelo</th>
                      <th className="px-4 py-2 font-medium text-right">Bets</th>
                      <th className="px-4 py-2 font-medium text-right">CLV μ</th>
                      <th className="px-4 py-2 font-medium text-right">Edge md</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((item) => (
                      <tr
                        key={item.model_version}
                        className="border-b border-white/5 last:border-0"
                      >
                        <td className="px-4 py-3 truncate max-w-[140px]">
                          {item.model_version}
                        </td>
                        <td className="px-4 py-3 text-right font-mono">
                          {item.n_bets}
                        </td>
                        <td
                          className={`px-4 py-3 text-right font-mono ${
                            item.mean_clv === null
                              ? "text-fg-subtle"
                              : item.mean_clv > 0
                              ? "text-brand-primary"
                              : "text-brand-danger"
                          }`}
                        >
                          {fmtNumber(item.mean_clv)}
                        </td>
                        <td
                          className={`px-4 py-3 text-right font-mono ${
                            item.median_edge === null
                              ? "text-fg-subtle"
                              : item.median_edge > 0
                              ? "text-brand-primary"
                              : "text-brand-danger"
                          }`}
                        >
                          {fmtPct(item.median_edge)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            )}
          </section>

          {data && data.items.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
                Timeline por modelo
              </h3>
              <div className="space-y-3">
                {data.items
                  .filter((it) => it.n_with_clv > 0)
                  .map((item) => (
                    <CLVChart key={item.model_version} modelVersion={item.model_version} />
                  ))}
                {data.items.every((it) => it.n_with_clv === 0) && (
                  <p className="text-fg-muted text-sm py-4 text-center">
                    Nenhum modelo tem bets com CLV ainda.
                  </p>
                )}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
