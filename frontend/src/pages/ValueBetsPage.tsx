import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQueries } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ValueBetCard } from "@/components/bets/ValueBetCard";
import { useUpcomingMatches } from "@/hooks/useMatches";
import { api, type Match, type ValueBet } from "@/lib/api";

interface BetWithMatch {
  bet: ValueBet;
  match: Match;
}

const MARKET_OPTIONS = [
  { label: "Todos", value: "all" },
  { label: "1X2", value: "1x2" },
  { label: "OU 2.5", value: "over_under_goals" },
  { label: "BTTS", value: "btts" },
] as const;

const EDGE_OPTIONS = [
  { label: "≥ 3%", value: 0.03 },
  { label: "≥ 5%", value: 0.05 },
  { label: "≥ 10%", value: 0.1 },
  { label: "≥ 20%", value: 0.2 },
] as const;

type MarketFilter = (typeof MARKET_OPTIONS)[number]["value"];

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

  // Filter state
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("all");
  const [edgeMin, setEdgeMin] = useState<number>(0.03);
  const [bookmakerFilter, setBookmakerFilter] = useState<string>("all");

  const allBookmakers = useMemo(() => {
    const set = new Set<string>();
    for (const { bet } of allBets) set.add(bet.bookmaker);
    return [...set].sort();
  }, [allBets]);

  const filtered = useMemo(() => {
    return allBets.filter(({ bet }) => {
      if (bet.edge < edgeMin) return false;
      if (marketFilter !== "all" && bet.market !== marketFilter) return false;
      if (bookmakerFilter !== "all" && bet.bookmaker !== bookmakerFilter) return false;
      return true;
    });
  }, [allBets, marketFilter, edgeMin, bookmakerFilter]);

  const isLoadingAny = matchesLoading || queries.some((q) => q.isLoading);

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between gap-2">
        <h2 className="text-xl font-semibold">Value Bets</h2>
        <span className="text-sm text-fg-muted">
          {filtered.length} de {allBets.length}
        </span>
      </header>

      <div className="space-y-2">
        <div className="flex flex-wrap gap-1">
          <span className="text-[11px] uppercase tracking-wide text-fg-muted py-1.5 mr-1">
            Mercado
          </span>
          {MARKET_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              variant={marketFilter === opt.value ? "gradient" : "ghost"}
              size="sm"
              onClick={() => setMarketFilter(opt.value)}
            >
              {opt.label}
            </Button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1">
          <span className="text-[11px] uppercase tracking-wide text-fg-muted py-1.5 mr-1">
            Edge
          </span>
          {EDGE_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              variant={edgeMin === opt.value ? "gradient" : "ghost"}
              size="sm"
              onClick={() => setEdgeMin(opt.value)}
            >
              {opt.label}
            </Button>
          ))}
        </div>
        {allBookmakers.length > 0 && (
          <div className="flex flex-wrap gap-1">
            <span className="text-[11px] uppercase tracking-wide text-fg-muted py-1.5 mr-1">
              Casa
            </span>
            <Button
              variant={bookmakerFilter === "all" ? "gradient" : "ghost"}
              size="sm"
              onClick={() => setBookmakerFilter("all")}
            >
              Todas
            </Button>
            {allBookmakers.map((bm) => (
              <Button
                key={bm}
                variant={bookmakerFilter === bm ? "gradient" : "ghost"}
                size="sm"
                onClick={() => setBookmakerFilter(bm)}
              >
                {bm}
              </Button>
            ))}
          </div>
        )}
      </div>

      {isLoadingAny && filtered.length === 0 && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      )}

      {!isLoadingAny && filtered.length === 0 && (
        <p className="text-fg-muted text-sm py-8 text-center">
          Nenhum value bet bate os filtros atuais.
        </p>
      )}

      <div className="space-y-3">
        {filtered.map(({ bet, match }) => (
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
