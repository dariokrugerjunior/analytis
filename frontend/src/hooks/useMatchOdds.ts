import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useMatchOdds(matchId: string | undefined) {
  return useQuery({
    queryKey: ["match-odds", matchId],
    queryFn: () => api.getMatchOdds(matchId!),
    enabled: !!matchId,
    refetchInterval: 60_000,
  });
}
