import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useClvTimeline(model: string | undefined) {
  return useQuery({
    queryKey: ["clv-timeline", model],
    queryFn: () => api.getClvTimeline(model!),
    enabled: !!model,
  });
}
