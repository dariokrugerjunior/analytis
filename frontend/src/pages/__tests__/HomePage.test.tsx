import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { createWrapper } from "@/test/test-utils";
import HomePage from "@/pages/HomePage";

vi.mock("@/hooks/useMatches", () => ({
  useUpcomingMatches: vi.fn(),
  useMatchesInWindow: vi.fn(),
}));

vi.mock("@/hooks/useMatchCardSummary", () => ({
  useMatchCardSummaries: vi.fn(() => new Map()),
}));

import { useMatchesInWindow, useUpcomingMatches } from "@/hooks/useMatches";

const mockedUseUpcomingMatches = vi.mocked(useUpcomingMatches);
const mockedUseMatchesInWindow = vi.mocked(useMatchesInWindow);

function setActiveQuery(
  state: { data: unknown; isLoading: boolean; isError: boolean },
) {
  mockedUseMatchesInWindow.mockReturnValue(
    state as unknown as ReturnType<typeof useMatchesInWindow>,
  );
  mockedUseUpcomingMatches.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useUpcomingMatches>);
}

function renderPage() {
  const Wrapper = createWrapper();
  return render(
    <Wrapper>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </Wrapper>,
  );
}

beforeEach(() => {
  mockedUseUpcomingMatches.mockReset();
  mockedUseMatchesInWindow.mockReset();
});

describe("HomePage", () => {
  it("renders header and loading state", () => {
    setActiveQuery({ data: undefined, isLoading: true, isError: false });

    renderPage();
    expect(
      screen.getByRole("heading", { name: /jogos/i }),
    ).toBeInTheDocument();
  });

  it("renders empty state when there are no matches", () => {
    setActiveQuery({ data: { items: [] }, isLoading: false, isError: false });

    renderPage();
    expect(
      screen.getByText(/nenhum jogo nesse intervalo/i),
    ).toBeInTheDocument();
  });

  it("renders error state", () => {
    setActiveQuery({ data: undefined, isLoading: false, isError: true });

    renderPage();
    expect(
      screen.getByText(/não foi possível carregar os jogos/i),
    ).toBeInTheDocument();
  });
});
