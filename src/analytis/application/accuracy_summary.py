"""Use case for computing model accuracy on finished matches with predictions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.inference import ModelVersionORM, PredictionORM
from analytis.persistence.orm.matches import MatchORM

Phase = Literal["group", "round_of_16", "quarterfinal", "semifinal", "final"]
PHASES: tuple[Phase, ...] = ("group", "round_of_16", "quarterfinal", "semifinal", "final")


class ModelRef(BaseModel):
    id: UUID
    name: str
    family: str


class ModelOption(ModelRef):
    n_predictions: int


class MarketKpi(BaseModel):
    hits: int
    n: int
    rate: float
    ci_low: float
    ci_high: float
    brier_avg: float


class ScorelineKpi(BaseModel):
    """Partial-credit accuracy over scorelines (only for Dixon-Coles models).

    For each finished match: 1.0 if predicted scoreline == actual, 0.5 if
    predicted outcome (home/draw/away) matches but scoreline doesn't, 0.0 if
    even the outcome is wrong. `score_pct` is the average across all matches.
    """

    exact: int
    partial: int
    miss: int
    n: int
    score_pct: float


class Kpis(BaseModel):
    n_matches_evaluated: int
    markets: dict[str, MarketKpi]  # keys: "1x2", "ou", "btts"
    brier_overall: float
    scoreline: ScorelineKpi | None = None  # populated only for Dixon-Coles models


class TimeseriesPoint(BaseModel):
    phase: Phase
    n: int
    cumulative: dict[str, float]  # keys: "1x2", "ou", "btts"


class MatchPredictionDetail(BaseModel):
    predicted: str
    predicted_prob: float
    actual: str
    hit: bool
    brier: float


class MatchRow(BaseModel):
    match_id: UUID
    kickoff_utc: datetime
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    phase: Phase
    predictions: dict[str, MatchPredictionDetail]  # keys: "1x2", "ou", "btts"
    scoreline_credit: float | None = (
        None  # 1.0 exact, 0.5 partial, 0.0 miss, None if model has no scoreline
    )
    scoreline_predicted_home: int | None = None
    scoreline_predicted_away: int | None = None


class AccuracySummary(BaseModel):
    model: ModelRef
    available_models: list[ModelOption]
    kpis: Kpis
    timeseries: list[TimeseriesPoint]
    matches: list[MatchRow]


@dataclass
class _MatchAggregate:
    """Internal: one finished match with its predictions for one model."""

    match_id: UUID
    kickoff_utc: datetime
    stage: str | None
    home_goals: int
    away_goals: int
    home_team_id: UUID
    away_team_id: UUID
    is_home_neutral: bool
    probs: dict[str, dict[str, float]]
    home_team: str = ""
    away_team: str = ""


@dataclass
class AccuracySummaryParams:
    model_name: str | None


class ModelNotFoundError(Exception):
    """Raised when ?model=<name> doesn't match any model_version with predictions."""


_PHASE_MAP: dict[str, Phase] = {
    "GROUP_STAGE": "group",
    "LAST_16": "round_of_16",
    "QUARTER_FINALS": "quarterfinal",
    "SEMI_FINALS": "semifinal",
    "THIRD_PLACE": "semifinal",
    "FINAL": "final",
}


def normalize_phase(competition_round: str | None) -> Phase:
    """Map Football-Data competition_round string to our canonical Phase."""
    if competition_round is None:
        return "group"
    return _PHASE_MAP.get(competition_round, "group")


def wilson_ci(*, hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% by default).

    Returns (low, high) clipped to [0.0, 1.0]. When n == 0 returns (0.0, 1.0).
    """
    if n <= 0:
        return (0.0, 1.0)
    p = hits / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    low = max(0.0, center - half)
    high = min(1.0, center + half)
    return (low, high)


def actual_1x2(home_goals: int, away_goals: int) -> str:
    """Return actual 1x2 outcome from final scoreline."""
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def actual_ou(home_goals: int, away_goals: int) -> str:
    """Return actual Over/Under outcome from total goals."""
    return "over" if (home_goals + away_goals) > 2.5 else "under"


def actual_btts(home_goals: int, away_goals: int) -> str:
    """Return actual BTTS outcome: both teams scored or not."""
    return "yes" if (home_goals >= 1 and away_goals >= 1) else "no"


def predicted_1x2_top(probs: dict[str, float]) -> tuple[str, float]:
    """Return (top_outcome, top_prob). On a probability tie, the outcome whose
    name comes earlier alphabetically wins."""
    # max with composite key: highest prob wins; on tie, smaller string wins
    # (because we negate via second key — smallest string == "earliest alphabetical").
    # We achieve "smallest string wins" within max() by providing a key that ranks
    # earlier-alphabetical strings as LARGER. Easiest: invert via tuple of negative
    # char codes for the full name.
    return max(probs.items(), key=lambda kv: (kv[1], tuple(-ord(c) for c in kv[0])))


def brier_binary(*, prob: float, outcome: int) -> float:
    """Brier for a single binary prediction. outcome must be 0 or 1."""
    return (prob - outcome) ** 2


def brier_multiclass(*, probs: dict[str, float], actual: str) -> float:
    """Brier multiclass over outcomes. actual is one of probs.keys()."""
    if actual not in probs:
        raise ValueError(f"actual {actual!r} not in probs keys {list(probs)}")
    total = 0.0
    for outcome, p in probs.items():
        y = 1.0 if outcome == actual else 0.0
        total += (p - y) ** 2
    return total / len(probs)


def scoreline_partial_score(
    pred_home: int, pred_away: int, actual_home: int, actual_away: int
) -> float:
    """Return 1.0 if exact scoreline matches, 0.5 if same outcome (home/draw/away)
    but different scoreline, 0.0 if outcome is also wrong."""
    if pred_home == actual_home and pred_away == actual_away:
        return 1.0
    pred_outcome = actual_1x2(pred_home, pred_away)
    actual_outcome = actual_1x2(actual_home, actual_away)
    return 0.5 if pred_outcome == actual_outcome else 0.0


class AccuracySummaryUseCase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def execute(self, params: AccuracySummaryParams) -> AccuracySummary:
        async with self._factory() as session:
            available = await self._list_available_models(session)
            if not available:
                raise ModelNotFoundError("no model has predictions yet")

            model = self._pick_model(available, params.model_name)
            rows = await self._load_match_rows(session, model.id)

            kpis = self._compute_kpis(rows)

            # Compute per-match scoreline credits for DC models (returns {match_id: (credit, pred_h, pred_a)})
            per_match_scoreline: dict[UUID, tuple[float, int, int]] = {}
            if model.family == "dixon-coles":
                model_row = await session.get(ModelVersionORM, model.id)
                if model_row is not None and model_row.artifact_path:
                    per_match_scoreline = self._compute_scoreline_per_match(model_row, rows)
                    if per_match_scoreline:
                        kpis.scoreline = self._aggregate_scoreline_kpi(per_match_scoreline)

            timeseries = self._compute_timeseries(rows)
            matches = self._serialize_matches(rows, per_match_scoreline)

            return AccuracySummary(
                model=ModelRef(id=model.id, name=model.name, family=model.family),
                available_models=available,
                kpis=kpis,
                timeseries=timeseries,
                matches=matches,
            )

    def _compute_scoreline_per_match(
        self, model_row: ModelVersionORM, rows: list[_MatchAggregate]
    ) -> dict[UUID, tuple[float, int, int]]:
        """Load DC params and compute most-likely scoreline per match.
        Returns {match_id: (credit, pred_home, pred_away)} for matches whose
        teams exist in the trained model.
        """
        from pathlib import Path

        from analytis.modeling.dixon_coles import score_matrix
        from analytis.modeling.persistence import load_params

        try:
            dc_params = load_params(Path(model_row.artifact_path or ""))
        except (FileNotFoundError, OSError):
            return {}

        result: dict[UUID, tuple[float, int, int]] = {}
        for r in rows:
            home_name = r.home_team
            away_name = r.away_team
            # Skip silently if either team is not in the trained model.
            if home_name not in dc_params.attack or away_name not in dc_params.attack:
                continue

            # Match the scoreline.py route's neutral-venue handling: HA=0 for neutral.
            ha = 0.0 if r.is_home_neutral else dc_params.home_advantage
            lam_h = math.exp(dc_params.attack[home_name] - dc_params.defense[away_name] + ha)
            lam_a = math.exp(dc_params.attack[away_name] - dc_params.defense[home_name])
            matrix = score_matrix(lam_h, lam_a, dc_params.rho, max_goals=10)

            # argmax over (i, j) to find most-likely scoreline
            best_i, best_j, best_p = 0, 0, -1.0
            for i in range(matrix.shape[0]):
                for j in range(matrix.shape[1]):
                    p = float(matrix[i, j])
                    if p > best_p:
                        best_p = p
                        best_i, best_j = i, j

            credit = scoreline_partial_score(best_i, best_j, r.home_goals, r.away_goals)
            result[r.match_id] = (credit, best_i, best_j)

        return result

    @staticmethod
    def _aggregate_scoreline_kpi(
        per_match: dict[UUID, tuple[float, int, int]],
    ) -> ScorelineKpi:
        """Aggregate per-match scoreline credits into the headline KPI."""
        exact = sum(1 for credit, _, _ in per_match.values() if credit == 1.0)
        partial = sum(1 for credit, _, _ in per_match.values() if credit == 0.5)
        miss = sum(1 for credit, _, _ in per_match.values() if credit == 0.0)
        n = exact + partial + miss
        score_pct = (1.0 * exact + 0.5 * partial) / n if n else 0.0
        return ScorelineKpi(exact=exact, partial=partial, miss=miss, n=n, score_pct=score_pct)

    async def _list_available_models(self, session: AsyncSession) -> list[ModelOption]:
        stmt = (
            select(
                ModelVersionORM.id,
                ModelVersionORM.name,
                ModelVersionORM.family,
                func.count(func.distinct(PredictionORM.match_id)).label("n"),
            )
            .join(PredictionORM, PredictionORM.model_version_id == ModelVersionORM.id)
            .group_by(ModelVersionORM.id, ModelVersionORM.name, ModelVersionORM.family)
            .having(func.count(func.distinct(PredictionORM.match_id)) > 0)
            .order_by(ModelVersionORM.name)
        )
        result = await session.execute(stmt)
        return [
            ModelOption(id=r.id, name=r.name, family=r.family, n_predictions=r.n) for r in result
        ]

    def _pick_model(self, available: list[ModelOption], name: str | None) -> ModelOption:
        if name is None:
            return available[0]
        for m in available:
            if m.name == name:
                return m
        raise ModelNotFoundError(f"model {name!r} not found or has no predictions")

    async def _load_match_rows(
        self, session: AsyncSession, model_id: UUID
    ) -> list[_MatchAggregate]:
        pred_stmt = (
            select(
                MatchORM.id,
                MatchORM.kickoff_utc,
                MatchORM.stage,
                MatchORM.home_goals,
                MatchORM.away_goals,
                MatchORM.home_team_id,
                MatchORM.away_team_id,
                MatchORM.is_home_neutral,
                PredictionORM.market,
                PredictionORM.outcome,
                PredictionORM.prob,
            )
            .join(PredictionORM, PredictionORM.match_id == MatchORM.id)
            .where(
                PredictionORM.model_version_id == model_id,
                MatchORM.status == "finished",
                MatchORM.home_goals.is_not(None),
                MatchORM.away_goals.is_not(None),
            )
        )
        result = await session.execute(pred_stmt)

        by_match: dict[UUID, _MatchAggregate] = {}
        team_ids: set[UUID] = set()
        for row in result:
            agg = by_match.setdefault(
                row.id,
                _MatchAggregate(
                    match_id=row.id,
                    kickoff_utc=row.kickoff_utc,
                    stage=row.stage,
                    home_goals=row.home_goals,
                    away_goals=row.away_goals,
                    home_team_id=row.home_team_id,
                    away_team_id=row.away_team_id,
                    is_home_neutral=row.is_home_neutral,
                    probs={"1x2": {}, "over_under_2_5": {}, "btts": {}},
                ),
            )
            if row.market in agg.probs:
                agg.probs[row.market][row.outcome] = float(row.prob)
            team_ids.add(row.home_team_id)
            team_ids.add(row.away_team_id)

        if team_ids:
            team_name_stmt = select(TeamORM.id, TeamORM.name).where(TeamORM.id.in_(team_ids))
            team_rows = (await session.execute(team_name_stmt)).fetchall()
            team_map: dict[UUID, str] = {r[0]: r[1] for r in team_rows}
            for agg in by_match.values():
                agg.home_team = team_map.get(agg.home_team_id, "?")
                agg.away_team = team_map.get(agg.away_team_id, "?")

        return sorted(by_match.values(), key=lambda a: a.kickoff_utc)

    def _compute_kpis(self, rows: list[_MatchAggregate]) -> Kpis:
        hits = {"1x2": 0, "ou": 0, "btts": 0}
        n_by_mkt = {"1x2": 0, "ou": 0, "btts": 0}
        brier_sums = {"1x2": 0.0, "ou": 0.0, "btts": 0.0}

        for r in rows:
            if r.probs["1x2"]:
                top_1x2, _top_p = predicted_1x2_top(r.probs["1x2"])
                actual_1 = actual_1x2(r.home_goals, r.away_goals)
                hits["1x2"] += int(top_1x2 == actual_1)
                n_by_mkt["1x2"] += 1
                brier_sums["1x2"] += brier_multiclass(probs=r.probs["1x2"], actual=actual_1)

            ou_probs = r.probs["over_under_2_5"]
            if ou_probs:
                p_over = ou_probs.get("over", 0.0)
                if p_over != 0.5:
                    pred_ou = "over" if p_over > 0.5 else "under"
                    actual_o = actual_ou(r.home_goals, r.away_goals)
                    hits["ou"] += int(pred_ou == actual_o)
                    n_by_mkt["ou"] += 1
                    brier_sums["ou"] += brier_binary(
                        prob=p_over, outcome=1 if actual_o == "over" else 0
                    )

            btts_probs = r.probs["btts"]
            if btts_probs:
                p_yes = btts_probs.get("yes", 0.0)
                if p_yes != 0.5:
                    pred_b = "yes" if p_yes > 0.5 else "no"
                    actual_b = actual_btts(r.home_goals, r.away_goals)
                    hits["btts"] += int(pred_b == actual_b)
                    n_by_mkt["btts"] += 1
                    brier_sums["btts"] += brier_binary(
                        prob=p_yes, outcome=1 if actual_b == "yes" else 0
                    )

        markets: dict[str, MarketKpi] = {}
        for key in ("1x2", "ou", "btts"):
            n = n_by_mkt[key]
            h = hits[key]
            rate = (h / n) if n else 0.0
            low, high = wilson_ci(hits=h, n=n)
            brier_avg = (brier_sums[key] / n) if n else 0.0
            markets[key] = MarketKpi(
                hits=h, n=n, rate=rate, ci_low=low, ci_high=high, brier_avg=brier_avg
            )

        total_brier_n = sum(n_by_mkt.values())
        brier_overall = sum(brier_sums.values()) / total_brier_n if total_brier_n else 0.0

        return Kpis(
            n_matches_evaluated=len(rows),
            markets=markets,
            brier_overall=brier_overall,
        )

    def _compute_timeseries(self, rows: list[_MatchAggregate]) -> list[TimeseriesPoint]:
        cum_hits = {"1x2": 0, "ou": 0, "btts": 0}
        cum_n = {"1x2": 0, "ou": 0, "btts": 0}
        per_phase_n: dict[Phase, int] = {}
        per_phase_cum: dict[Phase, dict[str, float]] = {}

        for n_matches_processed, r in enumerate(rows, start=1):
            phase = normalize_phase(r.stage)

            if r.probs["1x2"]:
                top, _ = predicted_1x2_top(r.probs["1x2"])
                actual_1 = actual_1x2(r.home_goals, r.away_goals)
                cum_hits["1x2"] += int(top == actual_1)
                cum_n["1x2"] += 1
            if r.probs["over_under_2_5"]:
                p_over = r.probs["over_under_2_5"].get("over", 0.0)
                if p_over != 0.5:
                    pred = "over" if p_over > 0.5 else "under"
                    actual_o = actual_ou(r.home_goals, r.away_goals)
                    cum_hits["ou"] += int(pred == actual_o)
                    cum_n["ou"] += 1
            if r.probs["btts"]:
                p_yes = r.probs["btts"].get("yes", 0.0)
                if p_yes != 0.5:
                    pred = "yes" if p_yes > 0.5 else "no"
                    actual_b = actual_btts(r.home_goals, r.away_goals)
                    cum_hits["btts"] += int(pred == actual_b)
                    cum_n["btts"] += 1

            per_phase_n[phase] = n_matches_processed
            per_phase_cum[phase] = {
                k: (cum_hits[k] / cum_n[k]) if cum_n[k] else 0.0 for k in ("1x2", "ou", "btts")
            }

        out: list[TimeseriesPoint] = []
        last_n = 0
        last_cum: dict[str, float] = {"1x2": 0.0, "ou": 0.0, "btts": 0.0}
        for phase in PHASES:
            if phase in per_phase_n:
                last_n = per_phase_n[phase]
                last_cum = per_phase_cum[phase]
            out.append(TimeseriesPoint(phase=phase, n=last_n, cumulative=dict(last_cum)))
        return out

    def _serialize_matches(
        self,
        rows: list[_MatchAggregate],
        scoreline_per_match: dict[UUID, tuple[float, int, int]] | None = None,
    ) -> list[MatchRow]:
        scoreline_per_match = scoreline_per_match or {}
        out: list[MatchRow] = []
        for r in sorted(rows, key=lambda a: a.kickoff_utc, reverse=True):
            preds: dict[str, MatchPredictionDetail] = {}

            if r.probs["1x2"]:
                top, top_p = predicted_1x2_top(r.probs["1x2"])
                actual_1 = actual_1x2(r.home_goals, r.away_goals)
                preds["1x2"] = MatchPredictionDetail(
                    predicted=top,
                    predicted_prob=top_p,
                    actual=actual_1,
                    hit=top == actual_1,
                    brier=brier_multiclass(probs=r.probs["1x2"], actual=actual_1),
                )
            if r.probs["over_under_2_5"]:
                p_over = r.probs["over_under_2_5"].get("over", 0.0)
                pred_ou = "over" if p_over > 0.5 else ("under" if p_over < 0.5 else "abstain")
                actual_o = actual_ou(r.home_goals, r.away_goals)
                preds["ou"] = MatchPredictionDetail(
                    predicted=pred_ou,
                    predicted_prob=p_over,
                    actual=actual_o,
                    hit=pred_ou == actual_o,
                    brier=brier_binary(prob=p_over, outcome=1 if actual_o == "over" else 0),
                )
            if r.probs["btts"]:
                p_yes = r.probs["btts"].get("yes", 0.0)
                pred_b = "yes" if p_yes > 0.5 else ("no" if p_yes < 0.5 else "abstain")
                actual_b = actual_btts(r.home_goals, r.away_goals)
                preds["btts"] = MatchPredictionDetail(
                    predicted=pred_b,
                    predicted_prob=p_yes,
                    actual=actual_b,
                    hit=pred_b == actual_b,
                    brier=brier_binary(prob=p_yes, outcome=1 if actual_b == "yes" else 0),
                )

            scoreline_info = scoreline_per_match.get(r.match_id)
            credit, pred_h, pred_a = (
                (None, None, None) if scoreline_info is None else scoreline_info
            )

            out.append(
                MatchRow(
                    match_id=r.match_id,
                    kickoff_utc=r.kickoff_utc,
                    home_team=r.home_team,
                    away_team=r.away_team,
                    home_goals=r.home_goals,
                    away_goals=r.away_goals,
                    phase=normalize_phase(r.stage),
                    predictions=preds,
                    scoreline_credit=credit,
                    scoreline_predicted_home=pred_h,
                    scoreline_predicted_away=pred_a,
                )
            )
        return out
