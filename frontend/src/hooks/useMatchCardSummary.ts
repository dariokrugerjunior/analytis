import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import {
  api,
  type Match,
  type MatchPredictions,
  type ValueBetsList,
} from "@/lib/api";

export interface MatchSummary {
  probs?: { home: number; draw: number; away: number };
  valueBetsCount: number;
}

export function useMatchCardSummaries(matches: Match[]) {
  const queries = useQueries({
    queries: matches.flatMap((m) => [
      {
        queryKey: ["match-predictions", m.id],
        queryFn: () => api.getMatchPredictions(m.id),
      },
      {
        queryKey: ["match-value-bets", m.id],
        queryFn: () => api.getMatchValueBets(m.id),
      },
    ]),
  });

  return useMemo(() => {
    const summaries = new Map<string, MatchSummary>();
    matches.forEach((m, idx) => {
      const predictionsRes = queries[idx * 2] as
        | { data?: MatchPredictions }
        | undefined;
      const betsRes = queries[idx * 2 + 1] as
        | { data?: ValueBetsList }
        | undefined;
      const oneXTwo = predictionsRes?.data?.predictions.filter(
        (p) => p.market === "1x2",
      );
      const probs =
        oneXTwo && oneXTwo.length >= 3
          ? {
              home: oneXTwo.find((p) => p.outcome === "home")?.prob ?? 0,
              draw: oneXTwo.find((p) => p.outcome === "draw")?.prob ?? 0,
              away: oneXTwo.find((p) => p.outcome === "away")?.prob ?? 0,
            }
          : undefined;
      const summary: MatchSummary = {
        valueBetsCount: betsRes?.data?.items.length ?? 0,
      };
      if (probs) summary.probs = probs;
      summaries.set(m.id, summary);
    });
    return summaries;
  }, [matches, queries]);
}
