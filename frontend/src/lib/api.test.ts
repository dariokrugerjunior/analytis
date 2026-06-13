import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

const originalFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn() as unknown as typeof fetch;
  localStorage.clear();
});

afterAll(() => {
  globalThis.fetch = originalFetch;
});

function mockResponse(body: unknown, init: ResponseInit = { status: 200 }) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
}

describe("api.listUpcomingMatches", () => {
  it("calls /v1/matches?upcoming=true&days=N with auth header", async () => {
    localStorage.setItem("analytis_api_key", "test-key");
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({ items: [] }),
    );
    await api.listUpcomingMatches(3);
    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]!;
    expect(call[0]).toBe("/v1/matches?upcoming=true&days=3");
    const init = call[1] as RequestInit;
    expect((init.headers as Record<string, string>)["X-API-Key"]).toBe("test-key");
  });
});

describe("api error handling", () => {
  it("throws ApiError with status on non-2xx", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({ detail: "nope" }, { status: 401 }),
    );
    await expect(api.listUpcomingMatches(1)).rejects.toMatchObject({
      status: 401,
      message: "nope",
    });
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({ detail: "nope" }, { status: 401 }),
    );
    await expect(api.listUpcomingMatches(1)).rejects.toBeInstanceOf(ApiError);
  });
});
