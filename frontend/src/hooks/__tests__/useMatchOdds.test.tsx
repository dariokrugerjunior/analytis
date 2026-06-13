import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useMatchOdds } from "@/hooks/useMatchOdds";
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

describe("useMatchOdds", () => {
  it("is idle when matchId is undefined", () => {
    mockFetchMap([]);
    const { result } = renderHook(() => useMatchOdds(undefined), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });

  it("returns odds payload when matchId provided", async () => {
    mockFetchMap([
      {
        url: "/matches/m7/odds",
        body: {
          match_id: "m7",
          quotes: [
            {
              bookmaker: "bet365",
              market: "1x2",
              outcome: "home",
              decimal_odds: 2.1,
              snapshot_taken_at: "2025-01-01T00:00:00Z",
            },
          ],
          best_per_outcome: {
            home: { decimal_odds: 2.1, bookmaker: "bet365" },
          },
        },
      },
    ]);

    const { result } = renderHook(() => useMatchOdds("m7"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.match_id).toBe("m7");
    expect(result.current.data?.quotes).toHaveLength(1);
  });
});
