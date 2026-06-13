import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useMatchPredictions(matchId: string | undefined) {
  return useQuery({
    queryKey: ["match-predictions", matchId],
    queryFn: () => api.getMatchPredictions(matchId!),
    enabled: !!matchId,
  });
}
