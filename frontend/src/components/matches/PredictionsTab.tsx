import type { MatchPredictions } from "@/lib/api";

interface Props {
  matchId: string;
  predictions: MatchPredictions | undefined;
  isLoading: boolean;
}

export function PredictionsTab({ predictions, isLoading }: Props) {
  if (isLoading) return <p className="text-fg-muted text-sm">Carregando previsões...</p>;
  if (!predictions || predictions.predictions.length === 0) {
    return <p className="text-fg-muted text-sm">Nenhuma previsão disponível.</p>;
  }
  return (
    <div className="text-fg-muted text-sm">
      {predictions.predictions.length} previsão(ões) — detalhe em breve (Task 12).
    </div>
  );
}
