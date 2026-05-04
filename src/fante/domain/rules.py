"""Domain types for game rules."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel


@dataclass(frozen=True)
class RollResult:
    """Result of a dice roll."""

    spec: str
    total: int
    breakdown: list[int]

    def __str__(self) -> str:
        rolls = " + ".join(str(r) for r in self.breakdown)
        if len(self.breakdown) > 1:
            return f"{self.spec} → [{rolls}] = {self.total}"
        return f"{self.spec} → {self.total}"


class PlotDieFace(StrEnum):
    OPPORTUNITY = "OPPORTUNITY"
    COMPLICATION = "COMPLICATION"
    BLANK = "BLANK"


class AppliedModifier(BaseModel):
    reason: str
    delta: int


class CheckResult(BaseModel):
    """Full result of an action check — mirrors mcp-game-rules wire format."""

    rule_id: str
    pack_name: str
    d20_rolls: list[int]
    kept_roll: int
    attribute_bonus: int
    skill_bonus: int
    situational_modifier: int
    total: int
    difficulty: int
    success: bool
    plot_dice: list[PlotDieFace]
    applied_modifiers: list[AppliedModifier]
    narration_seed: str | None

    @property
    def skill_mode(self) -> bool:
        """True when player_score was used instead of a d20 roll."""
        return len(self.d20_rolls) == 0
