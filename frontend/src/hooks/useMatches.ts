import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useUpcomingMatches(days = 7) {
  return useQuery({
    queryKey: ["matches", "upcoming", days],
    queryFn: () => api.listUpcomingMatches(days),
    refetchInterval: 60_000,
  });
}
