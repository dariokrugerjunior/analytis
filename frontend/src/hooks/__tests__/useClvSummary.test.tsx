import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useClvSummary } from "@/hooks/useClvSummary";
import {
  createWrapper,
  mockFetchMap,
  setApiKey,
} from "@/test/test-utils";

const originalFetch = globalThis.fetch;

beforeEach(() => {
  setApiKey();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  localStorage.clear();
});

describe("useClvSummary", () => {
  it("returns aggregated CLV summary", async () => {
    mockFetchMap([
      {
        url: "/bets/clv-summary",
        body: {
          items: [
            {
              model_version: "poisson-v1",
              n_bets: 10,
              n_with_clv: 5,
              mean_clv: 0.02,
              median_edge: 0.05,
            },
          ],
        },
      },
    ]);

    const { result } = renderHook(() => useClvSummary(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items).toHaveLength(1);
    expect(result.current.data?.items[0]?.model_version).toBe("poisson-v1");
  });
});
