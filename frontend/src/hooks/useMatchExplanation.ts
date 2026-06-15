import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";

export function useMatchExplanation(matchId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["match-explanation", matchId],
    queryFn: () => api.getMatchExplanation(matchId!),
    enabled: enabled && !!matchId,
    staleTime: 1000 * 60 * 30,
    retry: (failureCount, error) => {
      if (
        error instanceof ApiError &&
        [404, 422, 503].includes(error.status)
      ) {
        return false;
      }
      return failureCount < 1;
    },
  });
}
