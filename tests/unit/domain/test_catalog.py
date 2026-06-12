"""Tests for catalog domain entities."""

from uuid import uuid4

import pytest

from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.player import Player, PreferredFoot
from analytis.domain.referee import Referee
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.domain.venue import Venue


def test_competition_minimal() -> None:
    c = Competition(
        name="FIFA World Cup 2026",
        slug="wc-2026",
        competition_type=CompetitionType.SELECAO,
        country="INTL",
    )
    assert c.name == "FIFA World Cup 2026"
    assert c.competition_type is CompetitionType.SELECAO


def test_competition_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="name"):
        Competition(
            name="",
            slug="x",
            competition_type=CompetitionType.CLUBE,
            country="BRA",
        )


def test_team_minimal() -> None:
    t = Team(name="Brazil", short_name="BRA", team_type=TeamType.SELECAO, country="BRA")
    assert t.team_type is TeamType.SELECAO


def test_team_external_ids_roundtrip() -> None:
    t = Team(
        name="Flamengo",
        short_name="FLA",
        team_type=TeamType.CLUBE,
        country="BRA",
        external_ids={"footballdata": "127", "fbref": "639950ae"},
    )
    assert t.external_ids["footballdata"] == "127"


def test_player_with_preferred_foot() -> None:
    p = Player(name="Vinicius Jr", preferred_foot=PreferredFoot.RIGHT, position="LW")
    assert p.preferred_foot is PreferredFoot.RIGHT


def test_venue_altitude_nonnegative() -> None:
    Venue(name="Estadio Azteca", city="Mexico City", country="MEX", altitude_m=2240)
    with pytest.raises(ValueError, match="altitude_m"):
        Venue(name="Submarine", city="Atlantis", country="ATL", altitude_m=-10)


def test_referee_stats_default_none() -> None:
    r = Referee(name="Joel Aguilar", country="SLV")
    assert r.cards_per_game is None


def test_season_label() -> None:
    s = Season(label="2026", competition_id=uuid4())
    assert s.label == "2026"
