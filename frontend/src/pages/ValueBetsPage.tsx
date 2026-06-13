import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQueries } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { ValueBetCard } from "@/components/bets/ValueBetCard";
import { useUpcomingMatches } from "@/hooks/useMatches";
import { api, type Match, type ValueBet } from "@/lib/api";

interface BetWithMatch {
  bet: ValueBet;
  match: Match;
}

export default function ValueBetsPage() {
  const { data: matchesData, isLoading: matchesLoading } = useUpcomingMatches(7);
  const matches: Match[] = matchesData?.items ?? [];

  const queries = useQueries({
    queries: matches.map((m) => ({
      queryKey: ["match-value-bets", m.id],
      queryFn: () => api.getMatchValueBets(m.id),
    })),
  });

  const allBets = useMemo<BetWithMatch[]>(() => {
    const out: BetWithMatch[] = [];
    matches.forEach((m, idx) => {
      const res = queries[idx];
      const list = res?.data?.items ?? [];
      for (const bet of list) {
        out.push({ bet, match: m });
      }
    });
    out.sort((a, b) => b.bet.edge - a.bet.edge);
    return out;
  }, [matches, queries]);

  const isLoadingAny = matchesLoading || queries.some((q) => q.isLoading);

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between gap-2">
        <h2 className="text-xl font-semibold">Value Bets</h2>
        <span className="text-sm text-fg-muted">
          {allBets.length} oportunidade{allBets.length !== 1 ? "s" : ""}
        </span>
      </header>

      {isLoadingAny && allBets.length === 0 && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      )}

      {!isLoadingAny && allBets.length === 0 && (
        <p className="text-fg-muted text-sm py-8 text-center">
          Nenhum value bet ativo nos jogos da próxima semana.
        </p>
      )}

      <div className="space-y-3">
        {allBets.map(({ bet, match }) => (
          <Link
            key={bet.id}
            to={`/matches/${match.id}?tab=bets`}
            className="block"
          >
            <ValueBetCard
              bet={bet}
              showMatchLink
              matchLabel={`${match.home_team} × ${match.away_team}`}
            />
          </Link>
        ))}
      </div>
    </div>
  );
}
