import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useMatchCardSummaries } from "@/hooks/useMatchCardSummary";
import { type Match } from "@/lib/api";
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

function fakeMatch(id: string): Match {
  return {
    id,
    home_team: `H${id}`,
    away_team: `A${id}`,
    kickoff_utc: "2025-01-01T12:00:00Z",
    status: "scheduled",
    home_goals: null,
    away_goals: null,
    is_home_neutral: false,
  };
}

describe("useMatchCardSummaries", () => {
  it("returns empty map for empty match list", () => {
    mockFetchMap([]);
    const { result } = renderHook(() => useMatchCardSummaries([]), {
      wrapper: createWrapper(),
    });
    expect(result.current.size).toBe(0);
  });

  it("aggregates probs and value bets count per match", async () => {
    mockFetchMap([
      {
        url: "/matches/m1/predictions",
        body: {
          match_id: "m1",
          home_goals: null,
          away_goals: null,
          status: "scheduled",
          kickoff_utc: "2025-01-01T12:00:00Z",
          predictions: [
            {
              market: "1x2",
              outcome: "home",
              prob: 0.5,
              ci_low: 0.4,
              ci_high: 0.6,
              model_version: "ensemble-v1",
              created_at: "2025-01-01T00:00:00Z",
            },
            {
              market: "1x2",
              outcome: "draw",
              prob: 0.3,
              ci_low: 0.2,
              ci_high: 0.4,
              model_version: "ensemble-v1",
              created_at: "2025-01-01T00:00:00Z",
            },
            {
              market: "1x2",
              outcome: "away",
              prob: 0.2,
              ci_low: 0.1,
              ci_high: 0.3,
              model_version: "ensemble-v1",
              created_at: "2025-01-01T00:00:00Z",
            },
          ],
        },
      },
      {
        url: "/matches/m1/value-bets",
        body: {
          items: [
            {
              id: "b1",
              match_id: "m1",
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

    const matches = [fakeMatch("m1")];
    const { result } = renderHook(() => useMatchCardSummaries(matches), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      const s = result.current.get("m1");
      expect(s?.probs).toBeDefined();
      expect(s?.valueBetsCount).toBe(1);
    });
    const s = result.current.get("m1");
    expect(s?.probs?.home).toBeCloseTo(0.5);
    expect(s?.probs?.draw).toBeCloseTo(0.3);
    expect(s?.probs?.away).toBeCloseTo(0.2);
  });
});
