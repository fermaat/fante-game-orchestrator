"""LocalDice — RulesPort adapter using the standard library's SystemRandom.

Parses XdY+Z / XdY-Z / XdY / dY notation. Phase 2 will replace this with
MCPRulesAdapter; LocalDice stays as the offline/test fallback.
"""

import random
import re
from typing import Any

from fante.domain.actor import Actor
from fante.domain.rules import CheckResult, RollResult

_DICE_RE = re.compile(
    r"^(?P<count>[1-9]\d*)?d(?P<sides>[1-9]\d*)(?P<mod>[+-][1-9]\d*)?$",
    re.IGNORECASE,
)

_rng = random.SystemRandom()


def _parse(spec: str) -> tuple[int, int, int]:
    """Return (count, sides, modifier) or raise ValueError."""
    m = _DICE_RE.match(spec.strip())
    if not m:
        raise ValueError(f"Invalid dice spec: {spec!r}. Expected format: XdY, XdY+Z, dY, etc.")
    count = int(m.group("count") or 1)
    sides = int(m.group("sides"))
    mod = int(m.group("mod") or 0)
    if sides < 2:
        raise ValueError(f"Dice must have at least 2 sides, got {sides}")
    return count, sides, mod


class LocalDice:
    """RulesPort adapter — rolls dice locally using SystemRandom."""

    def roll(self, spec: str) -> RollResult:
        count, sides, mod = _parse(spec)
        rolls = [_rng.randint(1, sides) for _ in range(count)]
        breakdown = rolls + ([mod] if mod != 0 else [])
        return RollResult(spec=spec, total=sum(rolls) + mod, breakdown=breakdown)

    def check(
        self,
        rule_id: str,
        actor: Actor,
        context: dict[str, Any] | None = None,
        player_score: int | None = None,
    ) -> CheckResult:
        raise NotImplementedError(
            "LocalDice only supports roll(); use MCPRulesAdapter for check()."
        )
