const BASE = "/v1";

function getApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("analytis_api_key");
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const apiKey = getApiKey();
  const headers: Record<string, string> = {
    "X-API-Key": apiKey ?? "",
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) ?? {}),
  };
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

// ----- Domain types -----
export type MatchStatus = "scheduled" | "live" | "finished" | "postponed" | "cancelled";

export interface Match {
  id: string;
  home_team: string;
  away_team: string;
  kickoff_utc: string;
  status: MatchStatus;
  home_goals: number | null;
  away_goals: number | null;
  is_home_neutral: boolean;
}

export interface MatchesList {
  items: Match[];
}

export interface Prediction {
  market: string;
  outcome: string;
  prob: number;
  ci_low: number;
  ci_high: number;
  model_version: string;
  created_at: string;
}

export interface MatchPredictions {
  match_id: string;
  home_goals: number | null;
  away_goals: number | null;
  status: MatchStatus;
  kickoff_utc: string;
  predictions: Prediction[];
}

export interface OddsQuote {
  bookmaker: string;
  market: string;
  outcome: string;
  decimal_odds: number;
  snapshot_taken_at: string;
}

export interface OddsResponse {
  match_id: string;
  quotes: OddsQuote[];
  best_per_outcome: Record<string, { decimal_odds: number; bookmaker: string }>;
}

export interface ValueBet {
  id: string;
  match_id: string;
  model_version_id: string;
  market: string;
  outcome: string;
  bookmaker: string;
  our_prob: number;
  market_prob: number;
  decimal_odds: number;
  edge: number;
  kelly_fraction: number;
  suggested_stake_units: number;
  found_at: string;
  closing_decimal_odds: number | null;
  closing_clv: number | null;
}

export interface ValueBetsList {
  items: ValueBet[];
}

export interface ClvSummary {
  model_version: string;
  n_bets: number;
  n_with_clv: number;
  mean_clv: number | null;
  median_edge: number | null;
}

export interface ClvSummaryList {
  items: ClvSummary[];
}

// ----- Endpoints -----
export const api = {
  listUpcomingMatches: (days = 7) =>
    request<MatchesList>(`/matches?upcoming=true&days=${days}`),
  getMatchPredictions: (matchId: string) =>
    request<MatchPredictions>(`/matches/${matchId}/predictions`),
  getMatchOdds: (matchId: string) => request<OddsResponse>(`/matches/${matchId}/odds`),
  getMatchValueBets: (matchId: string) =>
    request<ValueBetsList>(`/matches/${matchId}/value-bets`),
  getClvSummary: () => request<ClvSummaryList>(`/bets/clv-summary`),
};
