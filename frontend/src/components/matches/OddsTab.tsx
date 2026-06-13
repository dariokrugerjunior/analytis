import { Trophy } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { OddsResponse } from "@/lib/api";

interface Props {
  matchId: string;
  odds: OddsResponse | undefined;
  isLoading: boolean;
}

const MARKET_LABELS: Record<string, string> = {
  "1x2": "Resultado (1X2)",
  over_under_goals: "Total de gols",
  btts: "Ambos marcam",
};

const OUTCOME_LABELS: Record<string, string> = {
  home: "Vitória mandante",
  draw: "Empate",
  away: "Vitória visitante",
  "over_2.5": "Over 2.5",
  "under_2.5": "Under 2.5",
  yes: "Sim",
  no: "Não",
};

interface QuoteGroup {
  market: string;
  outcome: string;
  bookmakers: { bookmaker: string; decimal_odds: number }[];
  best: { decimal_odds: number; bookmaker: string } | undefined;
}

function group(odds: OddsResponse): QuoteGroup[] {
  const map = new Map<string, QuoteGroup>();
  for (const q of odds.quotes) {
    const key = `${q.market}:${q.outcome}`;
    let g = map.get(key);
    if (!g) {
      g = {
        market: q.market,
        outcome: q.outcome,
        bookmakers: [],
        best: odds.best_per_outcome?.[key],
      };
      map.set(key, g);
    }
    g.bookmakers.push({ bookmaker: q.bookmaker, decimal_odds: q.decimal_odds });
  }
  // sort by best descending odds per group
  for (const g of map.values()) {
    g.bookmakers.sort((a, b) => b.decimal_odds - a.decimal_odds);
  }
  return [...map.values()].sort((a, b) => {
    const order = ["1x2", "over_under_goals", "btts"];
    return order.indexOf(a.market) - order.indexOf(b.market);
  });
}

export function OddsTab({ odds, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-40" />
        <Skeleton className="h-32" />
      </div>
    );
  }
  if (!odds || odds.quotes.length === 0) {
    return (
      <p className="text-fg-muted text-sm py-8 text-center">
        Nenhuma odd disponível. Rode <code>analytis odds fetch</code> primeiro.
      </p>
    );
  }

  const groups = group(odds);

  // group-by-market for layout
  const byMarket = new Map<string, QuoteGroup[]>();
  for (const g of groups) {
    const list = byMarket.get(g.market) ?? [];
    list.push(g);
    byMarket.set(g.market, list);
  }

  return (
    <div className="space-y-6 pb-6">
      {[...byMarket.entries()].map(([market, items]) => (
        <section key={market} className="space-y-3">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-fg-muted">
            {MARKET_LABELS[market] ?? market}
          </h3>
          <div className="space-y-4">
            {items.map((g) => (
              <div
                key={`${g.market}:${g.outcome}`}
                className="rounded-lg border border-white/10 bg-bg-elevated overflow-hidden"
              >
                <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                  <span className="font-medium">
                    {OUTCOME_LABELS[g.outcome] ?? g.outcome}
                  </span>
                  {g.best && (
                    <Badge variant="success" className="inline-flex items-center gap-1">
                      <Trophy className="h-3 w-3" />
                      Melhor: {g.best.decimal_odds.toFixed(2)} ({g.best.bookmaker})
                    </Badge>
                  )}
                </div>
                <ul className="divide-y divide-white/5">
                  {g.bookmakers.map((bm) => {
                    const isBest =
                      g.best?.bookmaker === bm.bookmaker &&
                      g.best?.decimal_odds === bm.decimal_odds;
                    return (
                      <li
                        key={`${g.market}:${g.outcome}:${bm.bookmaker}`}
                        className={cn(
                          "flex items-center justify-between px-4 py-2 text-sm",
                          isBest ? "bg-brand-primary/10" : "",
                        )}
                      >
                        <span className={cn(isBest ? "text-brand-primary font-medium" : "")}>
                          {bm.bookmaker}
                        </span>
                        <span className="font-mono">
                          {bm.decimal_odds.toFixed(2)}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
