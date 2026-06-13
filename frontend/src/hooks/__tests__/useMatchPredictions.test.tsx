import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useMatchPredictions } from "@/hooks/useMatchPredictions";
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

describe("useMatchPredictions", () => {
  it("does not fetch when matchId is undefined", () => {
    mockFetchMap([]);
    const { result } = renderHook(() => useMatchPredictions(undefined), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });

  it("returns predictions for a given match id", async () => {
    mockFetchMap([
      {
        url: "/matches/m42/predictions",
        body: {
          match_id: "m42",
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
              model_version: "v1",
              created_at: "2025-01-01T00:00:00Z",
            },
          ],
        },
      },
    ]);

    const { result } = renderHook(() => useMatchPredictions("m42"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.match_id).toBe("m42");
    expect(result.current.data?.predictions).toHaveLength(1);
  });
});
