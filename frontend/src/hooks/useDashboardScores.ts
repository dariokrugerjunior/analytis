import { useQuery } from "@tanstack/react-query";
import { fetchDashboardScores, type DashboardScores } from "@/lib/api";

export function useDashboardScores(model?: string) {
  return useQuery<DashboardScores>({
    queryKey: ["dashboard", "scores", model ?? "default"],
    queryFn: () => fetchDashboardScores(model),
    staleTime: 60_000,
  });
}
