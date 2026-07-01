import { useState } from "react";
import type { MatchPredictions } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useMatchExplanation } from "@/hooks/useMatchExplanation";
import { PredictionGroup } from "./PredictionGroup";

interface Props {
  matchId: string;
  predictions: MatchPredictions | undefined;
  isLoading: boolean;
}

export function PredictionsTab({ matchId, predictions, isLoading }: Props) {
  const [explainOn, setExplainOn] = useState(false);
  const explanation = useMatchExplanation(matchId, explainOn);
  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-32" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
    );
  }
  if (!predictions || predictions.predictions.length === 0) {
    return (
      <p className="text-fg-muted text-sm py-8 text-center">
        Nenhuma previsão disponível. Rode <code>analytis score</code> primeiro.
      </p>
    );
  }

  const all = predictions.predictions;
  const oneXTwo = all.filter((p) => p.market === "1x2");
  const ou = all.filter((p) => p.market === "over_under_goals");
  const btts = all.filter((p) => p.market === "btts");

  return (
    <div className="space-y-6 pb-6">
      {oneXTwo.length > 0 && (
        <PredictionGroup
          title="Resultado (1X2)"
          predictions={oneXTwo}
          outcomes={[
            { label: "Vitória mandante", outcome: "home", colorClass: "gradient-home" },
            { label: "Empate", outcome: "draw", colorClass: "bg-outcome-draw" },
            { label: "Vitória visitante", outcome: "away", colorClass: "gradient-away" },
          ]}
        />
      )}
      {ou.length > 0 && (
        <PredictionGroup
          title="Total de gols (linha 2.5)"
          predictions={ou}
          outcomes={[
            { label: "Over 2.5", outcome: "over_2.5", colorClass: "gradient-home" },
            { label: "Under 2.5", outcome: "under_2.5", colorClass: "bg-outcome-draw" },
          ]}
        />
      )}
      {btts.length > 0 && (
        <PredictionGroup
          title="Ambos marcam"
          predictions={btts}
          outcomes={[
            { label: "Sim", outcome: "yes", colorClass: "gradient-home" },
            { label: "Não", outcome: "no", colorClass: "bg-outcome-draw" },
          ]}
        />
      )}
      <section className="space-y-2">
        <div className="flex items-baseline justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
            Análise por IA
          </h3>
          {explanation.data && (
            <span className="text-[11px] text-fg-subtle font-mono">
              {explanation.data.model_used}
            </span>
          )}
        </div>
        {!explainOn && !explanation.data && (
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={() => setExplainOn(true)}
          >
            💡 Explicar previsões
          </Button>
        )}
        {explanation.isLoading && (
          <div className="space-y-2 rounded-lg border border-white/10 bg-bg-elevated p-4">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-4/5" />
            <Skeleton className="h-3 w-3/5" />
          </div>
        )}
        {explanation.data && (
          <div className="rounded-lg border border-white/10 bg-bg-elevated p-4 text-sm leading-relaxed whitespace-pre-wrap">
            {explanation.data.explanation}
          </div>
        )}
        {explanation.error && (
          <div className="rounded-lg border border-brand-danger/30 bg-bg-elevated p-3 text-xs text-fg-muted">
            {explanation.error.message}
          </div>
        )}
      </section>

      <p className="text-[11px] text-fg-subtle italic flex flex-wrap items-center gap-x-2 gap-y-1">
        <span>
          Modelo: {predictions.predictions[0]?.model_version} · Atualizado em{" "}
          {new Date(predictions.predictions[0]?.created_at ?? "").toLocaleString("pt-BR")}
        </span>
        {predictions.auto_scored && (
          <span
            className="inline-flex items-center gap-1 rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 text-[10px] not-italic font-medium text-amber-200"
            title="Nenhuma previsão pré-computada existia para este jogo. O modelo amplo foi escolhido automaticamente e rodou no momento da requisição."
          >
            ⚡ Geradas sob demanda
          </span>
        )}
      </p>
    </div>
  );
}
