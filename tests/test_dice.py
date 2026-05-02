"""Unit tests for LocalDice."""

import pytest

from fante.adapters.local_dice import LocalDice
from fante.domain.rules import RollResult


@pytest.mark.unit
class TestLocalDice:
    def setup_method(self) -> None:
        self.dice = LocalDice()

    def _assert_in_range(self, result: RollResult, lo: int, hi: int) -> None:
        assert lo <= result.total <= hi, f"{result.total} not in [{lo}, {hi}]"

    def test_single_die(self) -> None:
        r = self.dice.roll("1d6")
        self._assert_in_range(r, 1, 6)
        assert r.spec == "1d6"
        assert len(r.breakdown) == 1

    def test_multiple_dice(self) -> None:
        r = self.dice.roll("3d6")
        self._assert_in_range(r, 3, 18)
        assert len(r.breakdown) == 3

    def test_positive_modifier(self) -> None:
        r = self.dice.roll("1d20+2")
        self._assert_in_range(r, 3, 22)
        assert len(r.breakdown) == 2
        assert r.breakdown[-1] == 2

    def test_negative_modifier(self) -> None:
        r = self.dice.roll("2d6-1")
        self._assert_in_range(r, 1, 11)
        assert r.breakdown[-1] == -1

    def test_implicit_count(self) -> None:
        r = self.dice.roll("d20")
        self._assert_in_range(r, 1, 20)

    def test_case_insensitive(self) -> None:
        r = self.dice.roll("2D6")
        self._assert_in_range(r, 2, 12)

    def test_invalid_spec_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid dice spec"):
            self.dice.roll("abc")

    def test_invalid_sides_raises(self) -> None:
        with pytest.raises(ValueError):
            self.dice.roll("1d1")

    def test_str_representation(self) -> None:
        r = self.dice.roll("2d6")
        s = str(r)
        assert "2d6" in s
        assert str(r.total) in s
