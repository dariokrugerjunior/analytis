import { type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

export function createWrapper(client?: QueryClient) {
  const qc = client ?? createTestQueryClient();
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return Wrapper;
}

export interface MockRoute {
  /** Substring matched against the request URL. */
  url: string;
  /** Response JSON body. */
  body: unknown;
  /** Optional status, defaults to 200. */
  status?: number;
}

/**
 * Replaces `globalThis.fetch` with a mock that returns predetermined JSON for any
 * request whose URL contains one of the given substrings. Unmatched URLs throw.
 */
export function mockFetchMap(routes: MockRoute[]): ReturnType<typeof vi.fn> {
  const fn = vi.fn(async (input: RequestInfo | URL) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    const match = routes.find((r) => url.includes(r.url));
    if (!match) {
      throw new Error(`Unexpected fetch call: ${url}`);
    }
    return new Response(JSON.stringify(match.body), {
      status: match.status ?? 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  globalThis.fetch = fn as unknown as typeof fetch;
  return fn;
}

export function setApiKey(key = "test-key"): void {
  localStorage.setItem("analytis_api_key", key);
}
