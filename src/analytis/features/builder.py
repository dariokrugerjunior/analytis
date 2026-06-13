"""Feature builder — orchestrates feature computation for a match.

Given (match, as_of), pulls past matches and H2H from the repos, builds
typed samples, calls the pure feature functions, and returns a flat dict
of feature_name -> value.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from analytis.domain.match import Match
from analytis.features.context import (
    H2HSample,
    h2h_home_win_rate,
    h2h_total_goals_avg,
    rest_days,
)
from analytis.features.form import (
    FormSample,
    form_goal_diff,
    form_goals_against,
    form_goals_for,
)
from analytis.features.strength import (
    MatchSample,
    StrengthPrior,
    shrunk_attack_per_90,
    shrunk_defense_per_90,
)
from analytis.persistence.repositories import MatchRepository


@dataclass(frozen=True)
class BuilderConfig:
    strength_window: int = 20
    form_window: int = 10
    h2h_window: int = 10
    decay: float = 0.3


_DEFAULT_PRIOR = StrengthPrior(
    attack_per_90=1.2,
    defense_per_90=1.2,
    prior_strength=5.0,
)


def _strength_samples_for_team(team_id: UUID, matches: list[Match]) -> list[MatchSample]:
    samples: list[MatchSample] = []
    for m in matches:
        if m.home_goals is None or m.away_goals is None:
            continue
        if m.home_team_id == team_id:
            samples.append(
                MatchSample(
                    goals_for=m.home_goals,
                    goals_against=m.away_goals,
                    minutes_played=90,
                )
            )
        else:
            samples.append(
                MatchSample(
                    goals_for=m.away_goals,
                    goals_against=m.home_goals,
                    minutes_played=90,
                )
            )
    return samples


def _form_samples_for_team(team_id: UUID, matches: list[Match]) -> list[FormSample]:
    samples: list[FormSample] = []
    for m in matches:
        if m.home_goals is None or m.away_goals is None:
            continue
        if m.home_team_id == team_id:
            samples.append(FormSample(goals_for=m.home_goals, goals_against=m.away_goals))
        else:
            samples.append(FormSample(goals_for=m.away_goals, goals_against=m.home_goals))
    return samples


def _h2h_samples(home_team_id: UUID, matches: list[Match]) -> list[H2HSample]:
    """Normalise H2H so home_goals/away_goals are from the *current* home team's
    perspective."""
    samples: list[H2HSample] = []
    for m in matches:
        if m.home_goals is None or m.away_goals is None:
            continue
        if m.home_team_id == home_team_id:
            samples.append(H2HSample(home_goals=m.home_goals, away_goals=m.away_goals))
        else:
            samples.append(H2HSample(home_goals=m.away_goals, away_goals=m.home_goals))
    return samples


class FeatureBuilder:
    def __init__(
        self,
        match_repo: MatchRepository,
        *,
        config: BuilderConfig | None = None,
        prior: StrengthPrior | None = None,
    ) -> None:
        self._matches = match_repo
        self._config = config or BuilderConfig()
        self._prior = prior or _DEFAULT_PRIOR

    async def build(self, match: Match, as_of: datetime) -> dict[str, Any]:
        cfg = self._config
        prior = self._prior

        home_past = await self._matches.list_past_for_team(
            match.home_team_id, as_of, limit=cfg.strength_window
        )
        away_past = await self._matches.list_past_for_team(
            match.away_team_id, as_of, limit=cfg.strength_window
        )
        h2h_past = await self._matches.list_h2h(
            match.home_team_id,
            match.away_team_id,
            as_of,
            limit=cfg.h2h_window,
        )

        home_strength = _strength_samples_for_team(match.home_team_id, home_past)
        away_strength = _strength_samples_for_team(match.away_team_id, away_past)
        home_form = _form_samples_for_team(match.home_team_id, home_past)[: cfg.form_window]
        away_form = _form_samples_for_team(match.away_team_id, away_past)[: cfg.form_window]
        h2h_samples = _h2h_samples(match.home_team_id, h2h_past)

        last_home = home_past[0].kickoff_utc if home_past else None
        last_away = away_past[0].kickoff_utc if away_past else None

        features: dict[str, Any] = {
            "home_attack_per_90": shrunk_attack_per_90(history=home_strength, prior=prior),
            "home_defense_per_90": shrunk_defense_per_90(history=home_strength, prior=prior),
            "away_attack_per_90": shrunk_attack_per_90(history=away_strength, prior=prior),
            "away_defense_per_90": shrunk_defense_per_90(history=away_strength, prior=prior),
            "home_form_goals_for": form_goals_for(history=home_form, decay=cfg.decay),
            "home_form_goals_against": form_goals_against(history=home_form, decay=cfg.decay),
            "home_form_goal_diff": form_goal_diff(history=home_form, decay=cfg.decay),
            "away_form_goals_for": form_goals_for(history=away_form, decay=cfg.decay),
            "away_form_goals_against": form_goals_against(history=away_form, decay=cfg.decay),
            "away_form_goal_diff": form_goal_diff(history=away_form, decay=cfg.decay),
            "rest_days_home": rest_days(last_match_at=last_home, current_match_at=as_of),
            "rest_days_away": rest_days(last_match_at=last_away, current_match_at=as_of),
            "is_home_neutral": match.is_home_neutral,
            "h2h_home_win_rate": h2h_home_win_rate(history=h2h_samples),
            "h2h_total_goals_avg": h2h_total_goals_avg(history=h2h_samples),
            "n_past_home": len(home_past),
            "n_past_away": len(away_past),
            "n_h2h": len(h2h_samples),
        }
        return features
