import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useUpcomingMatches(days = 7, enabled = true) {
  return useQuery({
    queryKey: ["matches", "upcoming", days],
    queryFn: () => api.listUpcomingMatches(days),
    refetchInterval: 60_000,
    enabled,
  });
}

export function useMatchesInWindow(
  kickoffFrom: Date,
  kickoffTo: Date,
  enabled = true,
) {
  return useQuery({
    queryKey: [
      "matches",
      "window",
      kickoffFrom.toISOString(),
      kickoffTo.toISOString(),
    ],
    queryFn: () => api.listMatchesInWindow(kickoffFrom, kickoffTo),
    refetchInterval: 60_000,
    enabled,
  });
}
