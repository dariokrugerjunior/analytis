import { Link, useParams, useSearchParams } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useMatchPredictions } from "@/hooks/useMatchPredictions";
import { useMatchOdds } from "@/hooks/useMatchOdds";
import { useMatchValueBets } from "@/hooks/useMatchValueBets";
import { PredictionsTab } from "@/components/matches/PredictionsTab";
import { OddsTab } from "@/components/matches/OddsTab";
import { ValueBetsTab } from "@/components/matches/ValueBetsTab";

const VALID_TABS = ["predictions", "odds", "bets"] as const;
type TabValue = (typeof VALID_TABS)[number];

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
  const [searchParams, setSearchParams] = useSearchParams();
  const predictions = useMatchPredictions(matchId);
  const odds = useMatchOdds(matchId);
  const valueBets = useMatchValueBets(matchId);

  const tabFromUrl = searchParams.get("tab");
  const activeTab: TabValue =
    tabFromUrl && VALID_TABS.includes(tabFromUrl as TabValue)
      ? (tabFromUrl as TabValue)
      : "predictions";

  const setActiveTab = (next: string) => {
    setSearchParams({ tab: next });
  };

  const homeTeam = predictions.data ? (
    // Prefer using a separate field if backend provides; for now display IDs.
    matchId
  ) : null;

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

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full">
          <TabsTrigger value="predictions" className="flex-1">
            Previsões
          </TabsTrigger>
          <TabsTrigger value="odds" className="flex-1">
            Odds
          </TabsTrigger>
          <TabsTrigger value="bets" className="flex-1">
            💎 Bets
          </TabsTrigger>
        </TabsList>
        <TabsContent value="predictions">
          <PredictionsTab
            matchId={matchId!}
            predictions={predictions.data}
            isLoading={predictions.isLoading}
          />
        </TabsContent>
        <TabsContent value="odds">
          <OddsTab matchId={matchId!} odds={odds.data} isLoading={odds.isLoading} />
        </TabsContent>
        <TabsContent value="bets">
          <ValueBetsTab
            matchId={matchId!}
            valueBets={valueBets.data}
            isLoading={valueBets.isLoading}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
