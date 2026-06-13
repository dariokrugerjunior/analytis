import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { createWrapper } from "@/test/test-utils";

vi.mock("@/hooks/useClvSummary", () => ({
  useClvSummary: vi.fn(),
}));

vi.mock("@/hooks/useClvTimeline", () => ({
  useClvTimeline: vi.fn(() => ({
    data: undefined,
    isLoading: true,
    isError: false,
  })),
}));

import { useClvSummary } from "@/hooks/useClvSummary";
import ClvSummaryPage from "@/pages/ClvSummaryPage";

const mockedUseClvSummary = vi.mocked(useClvSummary);

function renderPage() {
  const Wrapper = createWrapper();
  return render(
    <Wrapper>
      <MemoryRouter>
        <ClvSummaryPage />
      </MemoryRouter>
    </Wrapper>,
  );
}

beforeEach(() => {
  mockedUseClvSummary.mockReset();
});

describe("ClvSummaryPage", () => {
  it("renders header and loading skeletons", () => {
    mockedUseClvSummary.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useClvSummary>);

    renderPage();
    expect(
      screen.getByRole("heading", { name: /clv summary/i }),
    ).toBeInTheDocument();
  });

  it("renders error message", () => {
    mockedUseClvSummary.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as unknown as ReturnType<typeof useClvSummary>);

    renderPage();
    expect(
      screen.getByText(/não foi possível carregar o resumo de clv/i),
    ).toBeInTheDocument();
  });

  it("renders empty state when there are no items", () => {
    mockedUseClvSummary.mockReturnValue({
      data: { items: [] },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useClvSummary>);

    renderPage();
    expect(
      screen.getByText(/nenhum value bet registrado ainda/i),
    ).toBeInTheDocument();
  });
});
