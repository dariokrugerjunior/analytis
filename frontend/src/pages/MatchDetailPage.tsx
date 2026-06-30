import { Link, useParams } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useMatchPredictions } from "@/hooks/useMatchPredictions";
import { PredictionsTab } from "@/components/matches/PredictionsTab";

function formatTime(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MatchDetailPage() {
  const { matchId } = useParams();
  const predictions = useMatchPredictions(matchId);

  const homeTeam = predictions.data ? matchId : null;

  return (
    <div className="space-y-4">
      <div className="sticky top-0 -mx-4 px-4 pb-3 pt-2 bg-bg-base/90 backdrop-blur z-10 border-b border-white/10">
        <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
          <Link to="/">
            <ChevronLeft className="h-4 w-4" />
            Voltar
          </Link>
        </Button>
        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-col">
            <span className="text-[11px] uppercase tracking-wide text-fg-muted">
              {predictions.data?.kickoff_utc && formatTime(predictions.data.kickoff_utc)}
            </span>
            <span className="text-base font-semibold">Match {homeTeam}</span>
          </div>
          {predictions.data?.status === "live" && <Badge variant="live">LIVE</Badge>}
          {predictions.data?.status === "finished" && (
            <Badge variant="success">FINAL</Badge>
          )}
        </div>
      </div>

      <PredictionsTab
        matchId={matchId!}
        predictions={predictions.data}
        isLoading={predictions.isLoading}
      />
    </div>
  );
}
