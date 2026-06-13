import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { createWrapper } from "@/test/test-utils";
import MatchDetailPage from "@/pages/MatchDetailPage";

vi.mock("@/hooks/useMatchPredictions", () => ({
  useMatchPredictions: vi.fn(),
}));

vi.mock("@/hooks/useMatchOdds", () => ({
  useMatchOdds: vi.fn(),
}));

vi.mock("@/hooks/useMatchValueBets", () => ({
  useMatchValueBets: vi.fn(),
}));

import { useMatchPredictions } from "@/hooks/useMatchPredictions";
import { useMatchOdds } from "@/hooks/useMatchOdds";
import { useMatchValueBets } from "@/hooks/useMatchValueBets";

const mockedPredictions = vi.mocked(useMatchPredictions);
const mockedOdds = vi.mocked(useMatchOdds);
const mockedValueBets = vi.mocked(useMatchValueBets);

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
  mockedOdds.mockReset();
  mockedValueBets.mockReset();
});

describe("MatchDetailPage", () => {
  it("renders tab list and loading state for predictions", () => {
    mockedPredictions.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useMatchPredictions>);
    mockedOdds.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useMatchOdds>);
    mockedValueBets.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useMatchValueBets>);

    renderPage();
    expect(screen.getByText(/voltar/i)).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /previsões/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /odds/i })).toBeInTheDocument();
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
    mockedOdds.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useMatchOdds>);
    mockedValueBets.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useMatchValueBets>);

    renderPage();
    expect(
      screen.getByText(/nenhuma previsão disponível/i),
    ).toBeInTheDocument();
  });
});
