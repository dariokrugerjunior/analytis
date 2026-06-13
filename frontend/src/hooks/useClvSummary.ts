import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useClvSummary() {
  return useQuery({
    queryKey: ["clv-summary"],
    queryFn: () => api.getClvSummary(),
  });
}
