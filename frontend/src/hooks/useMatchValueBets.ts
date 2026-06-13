import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useMatchValueBets(matchId: string | undefined) {
  return useQuery({
    queryKey: ["match-value-bets", matchId],
    queryFn: () => api.getMatchValueBets(matchId!),
    enabled: !!matchId,
    refetchInterval: 60_000,
  });
}
