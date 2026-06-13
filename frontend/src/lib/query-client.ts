import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: true,
      retry: (failures, err) => {
        if (err instanceof ApiError && err.status === 401) return false;
        return failures < 2;
      },
    },
  },
});
