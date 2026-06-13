import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useMatchValueBets } from "@/hooks/useMatchValueBets";
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

describe("useMatchValueBets", () => {
  it("is idle when matchId is undefined", () => {
    mockFetchMap([]);
    const { result } = renderHook(() => useMatchValueBets(undefined), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });

  it("returns value bets list", async () => {
    mockFetchMap([
      {
        url: "/matches/m9/value-bets",
        body: {
          items: [
            {
              id: "b1",
              match_id: "m9",
              model_version_id: "v1",
              market: "1x2",
              outcome: "home",
              bookmaker: "bet365",
              our_prob: 0.55,
              market_prob: 0.5,
              decimal_odds: 2.0,
              edge: 0.05,
              kelly_fraction: 0.1,
              suggested_stake_units: 1,
              found_at: "2025-01-01T00:00:00Z",
              closing_decimal_odds: null,
              closing_clv: null,
            },
          ],
        },
      },
    ]);

    const { result } = renderHook(() => useMatchValueBets("m9"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items).toHaveLength(1);
    expect(result.current.data?.items[0]?.id).toBe("b1");
  });
});
