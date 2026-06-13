"""Tests for FIFA confederation enum and helpers."""

from analytis.domain.confederation import Confederation, confederation_of_country


def test_known_country_maps_to_confederation() -> None:
    assert confederation_of_country("BRA") is Confederation.CONMEBOL
    assert confederation_of_country("FRA") is Confederation.UEFA
    assert confederation_of_country("MEX") is Confederation.CONCACAF
    assert confederation_of_country("JPN") is Confederation.AFC
    assert confederation_of_country("MAR") is Confederation.CAF
    assert confederation_of_country("AUS") is Confederation.AFC  # since 2006
    assert confederation_of_country("NZL") is Confederation.OFC


def test_unknown_country_returns_unknown() -> None:
    assert confederation_of_country("ZZZ") is Confederation.UNKNOWN


def test_case_insensitive() -> None:
    assert confederation_of_country("bra") is Confederation.CONMEBOL


def test_all_confederation_codes_are_short() -> None:
    for c in Confederation:
        assert len(c.value) <= 10
