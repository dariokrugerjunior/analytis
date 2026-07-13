import type { MatchPredictions } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { useScorelineGrid } from "@/hooks/useScorelineGrid";
import { PredictionGroup } from "./PredictionGroup";
import { ScorelineHeatmap } from "./ScorelineHeatmap";

interface Props {
  matchId: string;
  predictions: MatchPredictions | undefined;
  isLoading: boolean;
}

export function PredictionsTab({ matchId, predictions, isLoading }: Props) {
  const scoreline = useScorelineGrid(matchId);
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

      {scoreline.isLoading && <Skeleton className="h-48" />}
      {scoreline.data && (
        <section className="space-y-2">
          <p className="text-[11px] text-fg-subtle italic">
            Grid de placar derivado do ensemble via ajuste Poisson sobre 1X2 + OU 2.5 —
            marginais coerentes com as barras acima.
          </p>
          <ScorelineHeatmap data={scoreline.data} />
        </section>
      )}
      {scoreline.error && (
        <p className="text-[11px] text-fg-subtle italic">
          Placar exato indisponível para esta partida (falta 1X2 ou OU 2.5 do ensemble).
        </p>
      )}

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
