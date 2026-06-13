import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useClvTimeline } from "@/hooks/useClvTimeline";
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

describe("useClvTimeline", () => {
  it("does not fetch when model is undefined", () => {
    mockFetchMap([]);
    const { result } = renderHook(() => useClvTimeline(undefined), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });

  it("returns timeline points for a model", async () => {
    mockFetchMap([
      {
        url: "/bets/clv-timeline?model=poisson-v1",
        body: {
          model_version: "poisson-v1",
          points: [
            {
              date: "2025-01-01",
              cumulative_clv: 0.05,
              n_bets_cumulative: 3,
            },
          ],
        },
      },
    ]);

    const { result } = renderHook(() => useClvTimeline("poisson-v1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.model_version).toBe("poisson-v1");
    expect(result.current.data?.points).toHaveLength(1);
  });
});
