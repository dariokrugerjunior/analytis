import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useUpcomingMatches } from "@/hooks/useMatches";
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

describe("useUpcomingMatches", () => {
  it("loads upcoming matches", async () => {
    mockFetchMap([
      {
        url: "/matches?upcoming=true&days=3",
        body: {
          items: [
            {
              id: "m1",
              home_team: "A",
              away_team: "B",
              kickoff_utc: "2025-01-01T12:00:00Z",
              status: "scheduled",
              home_goals: null,
              away_goals: null,
              is_home_neutral: false,
            },
          ],
        },
      },
    ]);

    const { result } = renderHook(() => useUpcomingMatches(3), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items).toHaveLength(1);
    expect(result.current.data?.items[0]?.id).toBe("m1");
  });
});
