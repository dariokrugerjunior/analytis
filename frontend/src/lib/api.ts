const BASE = "/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
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
  auto_scored?: boolean;
  auto_score_model?: string | null;
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

export interface ClvTimelinePoint {
  date: string; // ISO YYYY-MM-DD
  cumulative_clv: number;
  n_bets_cumulative: number;
}

export interface ClvTimelineResponse {
  model_version: string;
  points: ClvTimelinePoint[];
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

export interface ScorelineItem {
  home: number;
  away: number;
  prob: number;
}

export interface ScorelineGrid {
  match_id: string;
  home_team: string;
  away_team: string;
  model_version: string;
  max_goals: number;
  lambda_home: number;
  lambda_away: number;
  grid: number[][];
  top_scorelines: ScorelineItem[];
  most_likely: ScorelineItem;
}

// ----- Endpoints -----
export const api = {
  listUpcomingMatches: (days = 7) =>
    request<MatchesList>(`/matches?upcoming=true&days=${days}`),
  listMatchesInWindow: (kickoffFrom: Date, kickoffTo: Date) =>
    request<MatchesList>(
      `/matches?kickoff_from=${encodeURIComponent(kickoffFrom.toISOString())}` +
        `&kickoff_to=${encodeURIComponent(kickoffTo.toISOString())}`,
    ),
  getMatchPredictions: (matchId: string) =>
    request<MatchPredictions>(`/matches/${matchId}/predictions`),
  getMatchOdds: (matchId: string) => request<OddsResponse>(`/matches/${matchId}/odds`),
  getMatchValueBets: (matchId: string) =>
    request<ValueBetsList>(`/matches/${matchId}/value-bets`),
  getClvSummary: () => request<ClvSummaryList>(`/bets/clv-summary`),
  getClvTimeline: (model: string) =>
    request<ClvTimelineResponse>(`/bets/clv-timeline?model=${encodeURIComponent(model)}`),
  getScorelineGrid: (matchId: string, maxGoals = 6, top = 8) =>
    request<ScorelineGrid>(
      `/matches/${matchId}/scoreline-grid?max_goals=${maxGoals}&top=${top}`,
    ),
};

// ----- Accuracy dashboard -----
export type Phase = "group" | "round_of_16" | "quarterfinal" | "semifinal" | "final";

export interface ModelRef {
  id: string;
  name: string;
  family: string;
}

export interface ModelOption extends ModelRef {
  n_predictions: number;
}

export interface MarketKpi {
  hits: number;
  n: number;
  rate: number;
  ci_low: number;
  ci_high: number;
  brier_avg: number;
}

export interface ScorelineKpi {
  exact: number;
  partial: number;
  miss: number;
  n: number;
  score_pct: number;
}

export interface AccuracyKpis {
  n_matches_evaluated: number;
  markets: { "1x2": MarketKpi; ou: MarketKpi; btts: MarketKpi };
  brier_overall: number;
  scoreline: ScorelineKpi | null;
}

export interface TimeseriesPoint {
  phase: Phase;
  n: number;
  cumulative: { "1x2": number; ou: number; btts: number };
}

export interface MatchPredictionDetail {
  predicted: string;
  predicted_prob: number;
  actual: string;
  hit: boolean;
  brier: number;
}

export interface MatchAccuracyRow {
  match_id: string;
  kickoff_utc: string;
  home_team: string;
  away_team: string;
  home_goals: number;
  away_goals: number;
  phase: Phase;
  predictions: {
    "1x2"?: MatchPredictionDetail;
    ou?: MatchPredictionDetail;
    btts?: MatchPredictionDetail;
  };
  scoreline_credit: number | null;        // 1.0 exact, 0.5 partial, 0.0 miss, null if non-DC model
  scoreline_predicted_home: number | null;
  scoreline_predicted_away: number | null;
}

export interface AccuracySummary {
  model: ModelRef;
  available_models: ModelOption[];
  kpis: AccuracyKpis;
  timeseries: TimeseriesPoint[];
  matches: MatchAccuracyRow[];
}

export function fetchAccuracySummary(model?: string): Promise<AccuracySummary> {
  const qs = model ? `?model=${encodeURIComponent(model)}` : "";
  return request<AccuracySummary>(`/accuracy/summary${qs}`);
}

// ----- Dashboard (per-game score) -----
export type Outcome = "home" | "draw" | "away";

export interface DashboardGame {
  match_id: string;
  home_team: string;
  away_team: string;
  kickoff_utc: string;
  predicted_score: string; // e.g. "2-1"
  actual_score: string; // e.g. "2-1"
  outcome_predicted: Outcome;
  outcome_actual: Outcome;
  points: 0 | 50 | 100;
}

export interface DashboardAggregate {
  total_games: number;
  avg_points: number;
  exact: number; // games worth 100
  outcome_only: number; // games worth 50
  missed: number; // games worth 0
}

export interface DashboardScores {
  model: ModelRef;
  available_models: ModelOption[];
  aggregate: DashboardAggregate;
  games: DashboardGame[];
}

export function fetchDashboardScores(model?: string): Promise<DashboardScores> {
  const qs = model ? `?model=${encodeURIComponent(model)}` : "";
  return request<DashboardScores>(`/dashboard/scores${qs}`);
}
