import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { createWrapper } from "@/test/test-utils";
import MatchDetailPage from "@/pages/MatchDetailPage";

vi.mock("@/hooks/useMatchPredictions", () => ({
  useMatchPredictions: vi.fn(),
}));

import { useMatchPredictions } from "@/hooks/useMatchPredictions";

const mockedPredictions = vi.mocked(useMatchPredictions);

function renderPage(matchId = "m1") {
  const Wrapper = createWrapper();
  return render(
    <Wrapper>
      <MemoryRouter initialEntries={[`/matches/${matchId}`]}>
        <Routes>
          <Route path="/matches/:matchId" element={<MatchDetailPage />} />
        </Routes>
      </MemoryRouter>
    </Wrapper>,
  );
}

beforeEach(() => {
  mockedPredictions.mockReset();
});

describe("MatchDetailPage", () => {
  it("renders the back link and predictions UI", () => {
    mockedPredictions.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useMatchPredictions>);

    renderPage();
    expect(screen.getByText(/voltar/i)).toBeInTheDocument();
  });

  it("does not render Odds or Bets tabs (hidden)", () => {
    mockedPredictions.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useMatchPredictions>);

    renderPage();
    expect(screen.queryByRole("tab", { name: /odds/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /bets/i })).not.toBeInTheDocument();
  });

  it("renders empty predictions message when no predictions", () => {
    mockedPredictions.mockReturnValue({
      data: {
        match_id: "m1",
        home_goals: null,
        away_goals: null,
        status: "scheduled",
        kickoff_utc: "2025-01-01T12:00:00Z",
        predictions: [],
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useMatchPredictions>);

    renderPage();
    expect(
      screen.getByText(/nenhuma previsão disponível/i),
    ).toBeInTheDocument();
  });
});
