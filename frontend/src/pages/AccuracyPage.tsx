import { useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { KpiCard } from "@/components/accuracy/KpiCard";
import { MatchAccuracyTable } from "@/components/accuracy/MatchAccuracyTable";
import { PerMatchHitsChart } from "@/components/accuracy/PerMatchHitsChart";
import { useAccuracySummary } from "@/hooks/useAccuracySummary";
import type { MatchAccuracyRow } from "@/lib/api";
import { CANONICAL_MODEL } from "@/lib/models";
import { cn } from "@/lib/utils";

function fmtPct(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

function fmtPp(low: number, high: number): string {
  const half = ((high - low) / 2) * 100;
  return `±${half.toFixed(0)}pp`;
}

function brierColor(brier: number): string {
  if (brier < 0.2) return "text-green-400";
  if (brier > 0.3) return "text-red-400";
  return "text-yellow-400";
}

type Filter = "all" | "perfect" | "partial" | "zero";

const MARKETS = ["1x2", "ou", "btts"] as const;

function bucket(row: MatchAccuracyRow): Exclude<Filter, "all"> | null {
  const predicted = MARKETS.filter((m) => row.predictions[m]);
  if (predicted.length === 0) return null;
  const hits = predicted.filter((m) => row.predictions[m]!.hit).length;
  if (hits === predicted.length) return "perfect";
  if (hits === 0) return "zero";
  return "partial";
}

export default function AccuracyPage() {
  const { data, isLoading, isError, error, refetch } = useAccuracySummary(CANONICAL_MODEL);
  const [filter, setFilter] = useState<Filter>("all");

  const filtered = useMemo(() => {
    if (!data) return [];
    if (filter === "all") return data.matches;
    return data.matches.filter((r) => bucket(r) === filter);
  }, [data, filter]);

  const counts = useMemo(() => {
    const c = { perfect: 0, partial: 0, zero: 0 };
    if (!data) return c;
    for (const r of data.matches) {
      const b = bucket(r);
      if (b) c[b]++;
    }
    return c;
  }, [data]);

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-3xl">
        <header>
          <h2 className="text-2xl font-semibold">Acertos</h2>
        </header>
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-60" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="space-y-4 max-w-3xl">
        <h2 className="text-2xl font-semibold">Acertos</h2>
        <Card className="p-4">
          <p className="text-sm text-red-400">
            Erro ao carregar: {error instanceof Error ? error.message : "desconhecido"}
          </p>
          <button
            type="button"
            className="mt-2 text-sm underline text-fg-primary"
            onClick={() => refetch()}
          >
            Tentar novamente
          </button>
        </Card>
      </div>
    );
  }

  if (data.kpis.n_matches_evaluated === 0) {
    return (
      <div className="space-y-4 max-w-3xl">
        <h2 className="text-2xl font-semibold">Acertos</h2>
        <Card className="p-6 text-center">
          <p className="text-sm text-fg-muted">
            Nenhum jogo com resultado disponível pra esse modelo ainda.
          </p>
        </Card>
      </div>
    );
  }

  const m = data.kpis.markets;
  const totalHits = m["1x2"].hits + m.ou.hits + m.btts.hits;
  const totalN = m["1x2"].n + m.ou.n + m.btts.n;
  const overallPct = totalN > 0 ? totalHits / totalN : 0;
  const totalMatches = data.kpis.n_matches_evaluated;

  const chipOptions: Array<{ key: Filter; label: string; count: number }> = [
    { key: "all", label: "Todos", count: totalMatches },
    { key: "perfect", label: "✓ Acertou tudo", count: counts.perfect },
    { key: "partial", label: "~ Parcial", count: counts.partial },
    { key: "zero", label: "✗ Errou tudo", count: counts.zero },
  ];

  return (
    <div className="space-y-6 max-w-3xl">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold">Acertos</h2>
        <p className="text-sm text-fg-muted">
          <span className="text-fg-primary font-medium">{data.model.name}</span> acertou{" "}
          <span className="text-fg-primary font-medium">{fmtPct(overallPct)}</span> dos
          mercados ({totalHits}/{totalN}) em {totalMatches} jogos.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3">
        <KpiCard
          label="1X2"
          value={fmtPct(m["1x2"].rate)}
          subtext={`${fmtPp(m["1x2"].ci_low, m["1x2"].ci_high)} (${m["1x2"].hits}/${m["1x2"].n})`}
        />
        <KpiCard
          label="OU 2.5"
          value={fmtPct(m.ou.rate)}
          subtext={`${fmtPp(m.ou.ci_low, m.ou.ci_high)} (${m.ou.hits}/${m.ou.n})`}
        />
        <KpiCard
          label="BTTS"
          value={fmtPct(m.btts.rate)}
          subtext={`${fmtPp(m.btts.ci_low, m.btts.ci_high)} (${m.btts.hits}/${m.btts.n})`}
        />
        <KpiCard
          label="Brier médio"
          value={data.kpis.brier_overall.toFixed(3)}
          colorClass={brierColor(data.kpis.brier_overall)}
          subtext="< 0.20 = bom, > 0.30 = ruim"
        />
      </div>

      <div className="flex gap-2 flex-wrap">
        {chipOptions.map(({ key, label, count }) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={cn(
              "rounded-full px-3 py-1 text-xs border transition-colors",
              filter === key
                ? "border-fg-primary bg-bg-overlay text-fg-primary"
                : "border-white/10 text-fg-muted hover:bg-bg-overlay/40",
            )}
          >
            {label} <span className="text-fg-subtle">({count})</span>
          </button>
        ))}
      </div>

      <Card className="p-4">
        <h3 className="text-sm font-medium text-fg-muted mb-1">Mercados acertados por jogo</h3>
        <p className="text-xs text-fg-muted mb-3">
          Barra = % dos mercados disponíveis que o modelo acertou nesse jogo (alguns jogos
          têm 2 mercados, outros 3). Verde = 100%, amarelo = 50–99%, laranja = até 50%,
          vermelho = 0%.
        </p>
        <PerMatchHitsChart rows={filtered} />
      </Card>

      <section>
        <h3 className="text-base font-semibold mb-2">
          Jogos <span className="text-sm font-normal text-fg-muted">({filtered.length})</span>
        </h3>
        <MatchAccuracyTable rows={filtered} />
      </section>
    </div>
  );
}
