import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useMatchPredictions } from "@/hooks/useMatchPredictions";
import { PredictionsTab } from "@/components/matches/PredictionsTab";
import { CANONICAL_MODEL } from "@/lib/models";

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

  // The API returns every model's predictions for this match; keep only the
  // canonical model so the user sees one consistent set of probabilities.
  const filteredData = useMemo(() => {
    if (!predictions.data) return undefined;
    return {
      ...predictions.data,
      predictions: predictions.data.predictions.filter(
        (p) => p.model_version === CANONICAL_MODEL,
      ),
    };
  }, [predictions.data]);

  const homeTeam = filteredData ? matchId : null;

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
              {filteredData?.kickoff_utc && formatTime(filteredData.kickoff_utc)}
            </span>
            <span className="text-base font-semibold">Match {homeTeam}</span>
          </div>
          {filteredData?.status === "live" && <Badge variant="live">LIVE</Badge>}
          {filteredData?.status === "finished" && (
            <Badge variant="success">FINAL</Badge>
          )}
        </div>
      </div>

      <PredictionsTab
        matchId={matchId!}
        predictions={filteredData}
        isLoading={predictions.isLoading}
      />
    </div>
  );
}
