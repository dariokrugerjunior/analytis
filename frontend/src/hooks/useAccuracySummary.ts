import { useQuery } from "@tanstack/react-query";
import { fetchAccuracySummary, type AccuracySummary } from "@/lib/api";

export function useAccuracySummary(model?: string) {
  return useQuery<AccuracySummary>({
    queryKey: ["accuracy", "summary", model ?? "default"],
    queryFn: () => fetchAccuracySummary(model),
    staleTime: 60_000,
  });
}
