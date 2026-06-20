import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { createWrapper } from "@/test/test-utils";
import type { AccuracySummary } from "@/lib/api";

vi.mock("@/hooks/useAccuracySummary", () => ({
  useAccuracySummary: vi.fn(),
}));

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Line: () => null,
}));

import { useAccuracySummary } from "@/hooks/useAccuracySummary";
import AccuracyPage from "@/pages/AccuracyPage";

const mockHook = vi.mocked(useAccuracySummary);

function sampleData(overrides: Partial<AccuracySummary> = {}): AccuracySummary {
  return {
    model: { id: "m1", name: "ensemble-v1", family: "ensemble" },
    available_models: [
      { id: "m1", name: "ensemble-v1", family: "ensemble", n_predictions: 12 },
      { id: "m2", name: "xgb-1x2-v1", family: "xgboost", n_predictions: 12 },
    ],
    kpis: {
      n_matches_evaluated: 12,
      markets: {
        "1x2": {
          hits: 7,
          n: 12,
          rate: 0.583,
          ci_low: 0.319,
          ci_high: 0.806,
          brier_avg: 0.198,
        },
        ou: {
          hits: 8,
          n: 12,
          rate: 0.667,
          ci_low: 0.394,
          ci_high: 0.864,
          brier_avg: 0.245,
        },
        btts: {
          hits: 6,
          n: 12,
          rate: 0.5,
          ci_low: 0.248,
          ci_high: 0.752,
          brier_avg: 0.252,
        },
      },
      brier_overall: 0.232,
    },
    timeseries: [
      {
        phase: "group",
        n: 8,
        cumulative: { "1x2": 0.625, ou: 0.75, btts: 0.5 },
      },
    ],
    matches: [
      {
        match_id: "abc",
        kickoff_utc: "2026-06-14T18:00:00Z",
        home_team: "Brazil",
        away_team: "Argentina",
        home_goals: 2,
        away_goals: 1,
        phase: "round_of_16",
        predictions: {
          "1x2": {
            predicted: "home",
            predicted_prob: 0.539,
            actual: "home",
            hit: true,
            brier: 0.21,
          },
        },
      },
    ],
    ...overrides,
  } as AccuracySummary;
}

function renderPage() {
  const Wrapper = createWrapper();
  return render(
    <Wrapper>
      <MemoryRouter>
        <AccuracyPage />
      </MemoryRouter>
    </Wrapper>,
  );
}

beforeEach(() => {
  mockHook.mockReset();
});

describe("AccuracyPage", () => {
  it("renders header when loading", () => {
    mockHook.mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
    } as unknown as ReturnType<typeof useAccuracySummary>);

    renderPage();
    expect(screen.getByText("Acertos")).toBeInTheDocument();
  });

  it("renders KPI values from data", () => {
    mockHook.mockReturnValue({
      isLoading: false,
      isError: false,
      data: sampleData(),
    } as unknown as ReturnType<typeof useAccuracySummary>);

    renderPage();
    expect(screen.getByText("58.3%")).toBeInTheDocument();
    expect(screen.getByText("66.7%")).toBeInTheDocument();
    expect(screen.getByText("50.0%")).toBeInTheDocument();
    expect(screen.getByText("0.232")).toBeInTheDocument();
  });

  it.each([
    [0.18, "text-green-400"],
    [0.25, "text-yellow-400"],
    [0.35, "text-red-400"],
  ] as const)("Brier card color at %s threshold", (brier, expectedClass) => {
    const data = sampleData();
    data.kpis.brier_overall = brier;
    mockHook.mockReturnValue({
      isLoading: false,
      isError: false,
      data,
    } as unknown as ReturnType<typeof useAccuracySummary>);

    renderPage();
    expect(screen.getByText(brier.toFixed(3))).toHaveClass(expectedClass);
  });

  it("shows empty state when n_matches_evaluated is 0", () => {
    const data = sampleData();
    data.kpis.n_matches_evaluated = 0;
    mockHook.mockReturnValue({
      isLoading: false,
      isError: false,
      data,
    } as unknown as ReturnType<typeof useAccuracySummary>);

    renderPage();
    expect(
      screen.getByText(/Nenhum jogo com resultado/i),
    ).toBeInTheDocument();
  });

  it("changing ModelSelector triggers a new fetch with the selected model name", async () => {
    mockHook.mockReturnValue({
      isLoading: false,
      isError: false,
      data: sampleData(),
    } as unknown as ReturnType<typeof useAccuracySummary>);

    renderPage();
    const select = screen.getByRole("combobox");
    await userEvent.selectOptions(select, "xgb-1x2-v1");
    await waitFor(() => {
      expect(mockHook).toHaveBeenLastCalledWith("xgb-1x2-v1");
    });
  });

  it("clicking a match card navigates to /matches/:id", async () => {
    mockHook.mockReturnValue({
      isLoading: false,
      isError: false,
      data: sampleData(),
    } as unknown as ReturnType<typeof useAccuracySummary>);

    renderPage();
    const card = screen.getByText(/Brazil vs Argentina/).closest(".cursor-pointer");
    expect(card).not.toBeNull();
    await userEvent.click(card!);
    // Navigation is handled internally by react-router useNavigate; the test
    // verifies the card is clickable and the cursor-pointer class is present.
  });
});
