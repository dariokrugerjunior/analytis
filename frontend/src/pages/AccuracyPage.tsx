import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { KpiCard } from "@/components/accuracy/KpiCard";
import { MatchAccuracyTable } from "@/components/accuracy/MatchAccuracyTable";
import { ModelSelector } from "@/components/accuracy/ModelSelector";
import { PerMatchHitsChart } from "@/components/accuracy/PerMatchHitsChart";
import { useAccuracySummary } from "@/hooks/useAccuracySummary";

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

export default function AccuracyPage() {
  const [model, setModel] = useState<string | undefined>(undefined);
  const { data, isLoading, isError, error, refetch } = useAccuracySummary(model);

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
        <ModelSelector
          models={data.available_models}
          selected={data.model.name}
          onChange={setModel}
        />
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

  return (
    <div className="space-y-6 max-w-3xl">
      <header className="space-y-3">
        <h2 className="text-2xl font-semibold">Acertos</h2>
        <div className="flex items-center gap-3">
          <ModelSelector
            models={data.available_models}
            selected={data.model.name}
            onChange={setModel}
          />
          <span className="text-sm text-fg-muted">
            {data.kpis.n_matches_evaluated} jogos avaliados
          </span>
        </div>
        <p className="text-sm text-fg-muted">
          <span className="text-fg-primary font-medium">{data.model.name}</span> acertou{" "}
          <span className="text-fg-primary font-medium">{fmtPct(overallPct)}</span> dos
          mercados ({totalHits}/{totalN}).
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

      <Card className="p-4">
        <h3 className="text-sm font-medium text-fg-muted mb-1">Mercados acertados por jogo</h3>
        <p className="text-xs text-fg-muted mb-3">
          Barra = quantos mercados (de 3) o modelo acertou. Verde = 3/3, amarelo = 2/3,
          laranja = 1/3, vermelho = 0/3.
        </p>
        <PerMatchHitsChart rows={data.matches} />
      </Card>

      <section>
        <h3 className="text-base font-semibold mb-2">Jogos</h3>
        <MatchAccuracyTable rows={data.matches} />
      </section>
    </div>
  );
}
