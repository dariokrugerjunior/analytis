import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";

export function useScorelineGrid(matchId: string | undefined, maxGoals = 6, top = 8) {
  return useQuery({
    queryKey: ["scoreline-grid", matchId, maxGoals, top],
    queryFn: () => api.getScorelineGrid(matchId!, maxGoals, top),
    enabled: !!matchId,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && (error.status === 404 || error.status === 422)) {
        return false;
      }
      return failureCount < 2;
    },
  });
}
