import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  createWrapper,
  mockFetchMap,
  setApiKey,
} from "@/test/test-utils";

vi.mock("@/hooks/useMatches", () => ({
  useUpcomingMatches: vi.fn(),
}));

import { useUpcomingMatches } from "@/hooks/useMatches";
import ValueBetsPage from "@/pages/ValueBetsPage";

const mockedUseUpcomingMatches = vi.mocked(useUpcomingMatches);

const originalFetch = globalThis.fetch;

function renderPage() {
  const Wrapper = createWrapper();
  return render(
    <Wrapper>
      <MemoryRouter>
        <ValueBetsPage />
      </MemoryRouter>
    </Wrapper>,
  );
}

beforeEach(() => {
  setApiKey();
  mockedUseUpcomingMatches.mockReset();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  localStorage.clear();
});

describe("ValueBetsPage", () => {
  it("renders header and loading skeletons", () => {
    mockedUseUpcomingMatches.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useUpcomingMatches>);
    mockFetchMap([]);

    renderPage();
    expect(
      screen.getByRole("heading", { name: /value bets/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/mercado/i)).toBeInTheDocument();
  });

  it("renders empty state when no matches", () => {
    mockedUseUpcomingMatches.mockReturnValue({
      data: { items: [] },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useUpcomingMatches>);
    mockFetchMap([]);

    renderPage();
    expect(
      screen.getByText(/nenhum value bet bate os filtros atuais/i),
    ).toBeInTheDocument();
  });
});
