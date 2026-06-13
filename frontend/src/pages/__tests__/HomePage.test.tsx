import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { createWrapper } from "@/test/test-utils";
import HomePage from "@/pages/HomePage";

vi.mock("@/hooks/useMatches", () => ({
  useUpcomingMatches: vi.fn(),
}));

vi.mock("@/hooks/useMatchCardSummary", () => ({
  useMatchCardSummaries: vi.fn(() => new Map()),
}));

import { useUpcomingMatches } from "@/hooks/useMatches";

const mockedUseUpcomingMatches = vi.mocked(useUpcomingMatches);

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
});

describe("HomePage", () => {
  it("renders header and loading state", () => {
    mockedUseUpcomingMatches.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useUpcomingMatches>);

    renderPage();
    expect(
      screen.getByRole("heading", { name: /jogos/i }),
    ).toBeInTheDocument();
  });

  it("renders empty state when there are no matches", () => {
    mockedUseUpcomingMatches.mockReturnValue({
      data: { items: [] },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useUpcomingMatches>);

    renderPage();
    expect(
      screen.getByText(/nenhum jogo nesse intervalo/i),
    ).toBeInTheDocument();
  });

  it("renders error state", () => {
    mockedUseUpcomingMatches.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as unknown as ReturnType<typeof useUpcomingMatches>);

    renderPage();
    expect(
      screen.getByText(/não foi possível carregar os jogos/i),
    ).toBeInTheDocument();
  });
});
