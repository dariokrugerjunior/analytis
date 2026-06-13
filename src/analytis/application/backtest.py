"""Walk-forward backtest over finished matches in the DB."""

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.modeling.dixon_coles import score_matrix
from analytis.modeling.evaluation import (
    brier_score,
    expected_calibration_error,
    log_loss,
)
from analytis.modeling.fitting import (
    FitConfig,
    MatchObservation,
    fit_dixon_coles,
)
from analytis.modeling.markets import (
    btts_probabilities,
    match_result_probabilities,
    over_under_probabilities,
)
from analytis.modeling.walk_forward import iter_walk_forward_slices
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class BacktestParams:
    since: datetime
    until: datetime
    min_train_size: int = 200
    test_size: int = 50
    max_iter: int = 200
    decay_per_day: float = 0.005


@dataclass
class SliceReport:
    train_end: str
    test_start: str
    test_end: str
    n_train: int
    n_test: int
    n_skipped: int = 0
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class BacktestResult:
    run_id: str
    report_path: str
    n_slices: int
    total_test_matches: int
    metrics: dict[str, float]


def _markets_for_observation(
    obs: MatchObservation,
    params_attack: dict[str, float],
    params_defense: dict[str, float],
    home_advantage: float,
    rho: float,
) -> tuple[float, float, float, float, float, float, float]:
    if obs.home_team not in params_attack or obs.away_team not in params_attack:
        raise KeyError("team not in trained params")
    ha = 0.0 if obs.is_neutral else home_advantage
    lam_h = math.exp(params_attack[obs.home_team] - params_defense[obs.away_team] + ha)
    lam_a = math.exp(params_attack[obs.away_team] - params_defense[obs.home_team])
    matrix = score_matrix(lam_h, lam_a, rho, max_goals=10)
    mr = match_result_probabilities(matrix)
    ou = over_under_probabilities(matrix, line=2.5)
    bt = btts_probabilities(matrix)
    return mr.home, mr.draw, mr.away, ou.over, ou.under, bt.yes, bt.no


def _agg_metrics(
    predictions: dict[str, list[float]], outcomes: dict[str, list[int]]
) -> dict[str, float]:
    out: dict[str, float] = {}
    for key in predictions:
        probs = predictions[key]
        obs = outcomes[key]
        if not probs:
            continue
        out[f"brier_{key}"] = brier_score(probs=probs, outcomes=obs)
        out[f"log_loss_{key}"] = log_loss(probs=probs, outcomes=obs)
        out[f"ece_{key}"] = expected_calibration_error(probs=probs, outcomes=obs, n_bins=10)
    return out


class BacktestUseCase:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        reports_dir: Path | None = None,
    ) -> None:
        self._factory = session_factory
        self._reports_dir = reports_dir or Path("models")

    async def execute(self, params: BacktestParams) -> BacktestResult:
        async with UnitOfWork(self._factory) as uow:
            stmt = (
                select(MatchORM)
                .where(
                    MatchORM.status == "finished",
                    MatchORM.kickoff_utc >= params.since,
                    MatchORM.kickoff_utc < params.until,
                    MatchORM.home_goals.is_not(None),
                    MatchORM.away_goals.is_not(None),
                )
                .order_by(MatchORM.kickoff_utc.asc())
            )
            matches = list((await uow.session.scalars(stmt)).all())

            team_stmt = select(TeamORM.id, TeamORM.name)
            team_rows = (await uow.session.execute(team_stmt)).all()
            id_to_name: dict[Any, str] = {row.id: row.name for row in team_rows}

        observations: list[MatchObservation] = []
        for m in matches:
            home_name = id_to_name.get(m.home_team_id)
            away_name = id_to_name.get(m.away_team_id)
            if not home_name or not away_name:
                continue
            if m.home_goals is None or m.away_goals is None:
                continue
            observations.append(
                MatchObservation(
                    home_team=home_name,
                    away_team=away_name,
                    home_goals=int(m.home_goals),
                    away_goals=int(m.away_goals),
                    kickoff_utc=m.kickoff_utc,
                    is_neutral=m.is_home_neutral,
                )
            )

        if not observations:
            raise ValueError("no finished matches in window")

        slices_report: list[SliceReport] = []
        per_market_probs: dict[str, list[float]] = {
            "1x2_home": [],
            "1x2_draw": [],
            "1x2_away": [],
            "ou_over_2_5": [],
            "ou_under_2_5": [],
            "btts_yes": [],
            "btts_no": [],
        }
        per_market_outs: dict[str, list[int]] = {k: [] for k in per_market_probs}

        for sl in iter_walk_forward_slices(
            observations,
            min_train_size=params.min_train_size,
            test_size=params.test_size,
            key=lambda m: m.kickoff_utc,
        ):
            train = observations[: sl.train_end_idx]
            test = observations[sl.test_start_idx : sl.test_end_idx]
            try:
                fit = fit_dixon_coles(
                    train,
                    config=FitConfig(
                        max_iter=params.max_iter,
                        decay_per_day=params.decay_per_day,
                    ),
                )
            except ValueError:
                continue

            slice_probs: dict[str, list[float]] = {k: [] for k in per_market_probs}
            slice_outs: dict[str, list[int]] = {k: [] for k in per_market_outs}
            skipped = 0
            for obs in test:
                try:
                    h, d, a, over, under, yes, no = _markets_for_observation(
                        obs,
                        fit.attack,
                        fit.defense,
                        fit.home_advantage,
                        fit.rho,
                    )
                except KeyError:
                    skipped += 1
                    continue
                home_win = 1 if obs.home_goals > obs.away_goals else 0
                draw = 1 if obs.home_goals == obs.away_goals else 0
                away_win = 1 if obs.home_goals < obs.away_goals else 0
                over_obs = 1 if obs.home_goals + obs.away_goals > 2 else 0
                btts_obs = 1 if obs.home_goals >= 1 and obs.away_goals >= 1 else 0
                slice_probs["1x2_home"].append(h)
                slice_outs["1x2_home"].append(home_win)
                slice_probs["1x2_draw"].append(d)
                slice_outs["1x2_draw"].append(draw)
                slice_probs["1x2_away"].append(a)
                slice_outs["1x2_away"].append(away_win)
                slice_probs["ou_over_2_5"].append(over)
                slice_outs["ou_over_2_5"].append(over_obs)
                slice_probs["ou_under_2_5"].append(under)
                slice_outs["ou_under_2_5"].append(1 - over_obs)
                slice_probs["btts_yes"].append(yes)
                slice_outs["btts_yes"].append(btts_obs)
                slice_probs["btts_no"].append(no)
                slice_outs["btts_no"].append(1 - btts_obs)

            slice_metrics = _agg_metrics(slice_probs, slice_outs)
            slices_report.append(
                SliceReport(
                    train_end=sl.train_end_key.isoformat(),
                    test_start=sl.test_start_key.isoformat(),
                    test_end=sl.test_end_key.isoformat(),
                    n_train=len(train),
                    n_test=len(test),
                    n_skipped=skipped,
                    metrics=slice_metrics,
                )
            )
            for k in per_market_probs:
                per_market_probs[k].extend(slice_probs[k])
                per_market_outs[k].extend(slice_outs[k])

        agg = _agg_metrics(per_market_probs, per_market_outs)
        run_id = str(uuid4())
        report_dir = self._reports_dir / run_id
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "backtest.json"
        report = {
            "run_id": run_id,
            "params": {
                "since": params.since.isoformat(),
                "until": params.until.isoformat(),
                "min_train_size": params.min_train_size,
                "test_size": params.test_size,
                "decay_per_day": params.decay_per_day,
            },
            "slices": [asdict(s) for s in slices_report],
            "aggregate": agg,
        }
        report_path.write_text(json.dumps(report, indent=2, default=str))

        return BacktestResult(
            run_id=run_id,
            report_path=str(report_path),
            n_slices=len(slices_report),
            total_test_matches=sum(s.n_test for s in slices_report),
            metrics=agg,
        )
