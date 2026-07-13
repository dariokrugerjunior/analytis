import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useDashboardScores } from "@/hooks/useDashboardScores";
import { createWrapper, mockFetchMap, setApiKey } from "@/test/test-utils";

const originalFetch = globalThis.fetch;

beforeEach(() => {
  setApiKey();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  localStorage.clear();
});

describe("useDashboardScores", () => {
  it("fetches per-game scores for the canonical model", async () => {
    const fetchFn = mockFetchMap([
      {
        url: "/dashboard/scores",
        body: {
          model: { id: "m1", name: "ensemble-v1", family: "ensemble" },
          available_models: [
            { id: "m1", name: "ensemble-v1", family: "ensemble", n_predictions: 3 },
          ],
          aggregate: {
            total_games: 2,
            avg_points: 75,
            exact: 1,
            outcome_only: 1,
            missed: 0,
          },
          games: [
            {
              match_id: "abc",
              home_team: "Brazil",
              away_team: "Argentina",
              kickoff_utc: "2026-06-14T18:00:00Z",
              predicted_score: "2-1",
              actual_score: "2-1",
              outcome_predicted: "home",
              outcome_actual: "home",
              points: 100,
            },
          ],
        },
      },
    ]);

    const { result } = renderHook(() => useDashboardScores("ensemble-v1"), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.aggregate.total_games).toBe(2);
    expect(result.current.data?.games[0]?.points).toBe(100);
    // the model must be threaded into the query string
    const url = fetchFn.mock.calls[0]?.[0] as string;
    expect(url).toContain("model=ensemble-v1");
  });
});
