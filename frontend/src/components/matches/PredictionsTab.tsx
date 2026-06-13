import type { MatchPredictions } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { PredictionGroup } from "./PredictionGroup";

interface Props {
  matchId: string;
  predictions: MatchPredictions | undefined;
  isLoading: boolean;
}

export function PredictionsTab({ predictions, isLoading }: Props) {
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
      <p className="text-[11px] text-fg-subtle italic">
        Modelo: {predictions.predictions[0]?.model_version} · Atualizado em{" "}
        {new Date(predictions.predictions[0]?.created_at ?? "").toLocaleString("pt-BR")}
      </p>
      <p className="text-[11px] text-fg-subtle italic border-t border-white/10 pt-3">
        Heatmap de placares exige endpoint adicional (não no MVP).
      </p>
    </div>
  );
}
