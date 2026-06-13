import { Link } from "react-router-dom";
import { Gem } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { MarketBars } from "./MarketBars";
import type { Match } from "@/lib/api";

interface Props {
  match: Match;
  probs?: { home: number; draw: number; away: number };
  valueBetsCount?: number;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusBadge(status: Match["status"]) {
  if (status === "live") return <Badge variant="live">LIVE</Badge>;
  if (status === "finished") return <Badge variant="success">FINAL</Badge>;
  if (status === "postponed" || status === "cancelled")
    return <Badge variant="default">{status.toUpperCase()}</Badge>;
  return null;
}

export function MatchCard({ match, probs, valueBetsCount = 0 }: Props) {
  const isFinished = match.status === "finished";
  return (
    <Link to={`/matches/${match.id}`} className="block group">
      <Card className={isFinished ? "opacity-70" : ""}>
        <div className="flex items-center justify-between px-4 pt-3">
          <span className="text-[11px] uppercase tracking-wide text-fg-muted">
            {formatTime(match.kickoff_utc)}
          </span>
          {statusBadge(match.status)}
        </div>
        <div className="px-4 py-3">
          <div className="text-base font-semibold">
            {match.home_team} <span className="text-fg-muted">×</span> {match.away_team}
          </div>
          {match.home_goals !== null && match.away_goals !== null && (
            <div className="mt-1 font-mono text-2xl">
              {match.home_goals} - {match.away_goals}
            </div>
          )}
        </div>
        {probs && (
          <div className="px-4 pb-3">
            <MarketBars {...probs} />
          </div>
        )}
        {valueBetsCount > 0 && (
          <div className="px-4 pb-3">
            <Badge variant="edge" className="inline-flex items-center gap-1">
              <Gem className="h-3 w-3" />
              {valueBetsCount} value bet{valueBetsCount > 1 ? "s" : ""}
            </Badge>
          </div>
        )}
      </Card>
    </Link>
  );
}
