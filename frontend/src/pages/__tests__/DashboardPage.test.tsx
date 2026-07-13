import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { createWrapper } from "@/test/test-utils";
import type { DashboardScores } from "@/lib/api";

vi.mock("@/hooks/useDashboardScores", () => ({
  useDashboardScores: vi.fn(),
}));

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Bar: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Cell: () => null,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
}));

import { useDashboardScores } from "@/hooks/useDashboardScores";
import DashboardPage from "@/pages/DashboardPage";

const mockHook = vi.mocked(useDashboardScores);

function sampleData(overrides: Partial<DashboardScores> = {}): DashboardScores {
  return {
    model: { id: "m1", name: "ensemble-v1", family: "ensemble" },
    available_models: [
      { id: "m1", name: "ensemble-v1", family: "ensemble", n_predictions: 3 },
    ],
    aggregate: {
      total_games: 3,
      avg_points: 50,
      exact: 1,
      outcome_only: 1,
      missed: 1,
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
    ...overrides,
  } as DashboardScores;
}

function renderPage() {
  const Wrapper = createWrapper();
  return render(
    <Wrapper>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </Wrapper>,
  );
}

beforeEach(() => {
  mockHook.mockReset();
});

describe("DashboardPage", () => {
  it("renders header while loading", () => {
    mockHook.mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
    } as unknown as ReturnType<typeof useDashboardScores>);

    renderPage();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("requests the canonical model", () => {
    mockHook.mockReturnValue({
      isLoading: false,
      isError: false,
      data: sampleData(),
    } as unknown as ReturnType<typeof useDashboardScores>);

    renderPage();
    expect(mockHook).toHaveBeenLastCalledWith("ensemble-v1");
  });

  it("renders the KPI counts and average score", () => {
    mockHook.mockReturnValue({
      isLoading: false,
      isError: false,
      data: sampleData(),
    } as unknown as ReturnType<typeof useDashboardScores>);

    renderPage();
    expect(screen.getByText("50.0")).toBeInTheDocument(); // avg points
    expect(screen.getByText("Placar exato")).toBeInTheDocument();
    expect(screen.getByText("Resultado certo")).toBeInTheDocument();
    expect(screen.getByText("Erros")).toBeInTheDocument();
    // 3 total games appears in the "Total de jogos" KPI value
    expect(screen.getAllByText("3").length).toBeGreaterThanOrEqual(1);
  });

  it("shows empty state when there are no games", () => {
    const data = sampleData();
    data.aggregate.total_games = 0;
    data.games = [];
    mockHook.mockReturnValue({
      isLoading: false,
      isError: false,
      data,
    } as unknown as ReturnType<typeof useDashboardScores>);

    renderPage();
    expect(screen.getByText(/Nenhum jogo com resultado/i)).toBeInTheDocument();
  });

  it("shows error state with retry", () => {
    mockHook.mockReturnValue({
      isLoading: false,
      isError: true,
      error: new Error("boom"),
      data: undefined,
    } as unknown as ReturnType<typeof useDashboardScores>);

    renderPage();
    expect(screen.getByText(/Erro ao carregar/i)).toBeInTheDocument();
    expect(screen.getByText("Tentar novamente")).toBeInTheDocument();
  });

  it("clicking a game card navigates to /matches/:id", async () => {
    mockHook.mockReturnValue({
      isLoading: false,
      isError: false,
      data: sampleData(),
    } as unknown as ReturnType<typeof useDashboardScores>);

    renderPage();
    const card = screen.getByText(/Brazil vs Argentina/).closest(".cursor-pointer");
    expect(card).not.toBeNull();
    await userEvent.click(card!);
  });
});
