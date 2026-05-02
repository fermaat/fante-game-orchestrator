"""PlayerProfile — versioned schema describing the player character."""

from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["es", "en", "mixed"]


class PlayerProfile(BaseModel):
    """Player character sheet.

    `schema_version` is bumped whenever the schema changes in a
    backwards-incompatible way. Loaders should branch on it.
    """

    schema_version: int = 1
    name: str
    background: str = ""
    preferences: list[str] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)
    language: Language = "es"
    seed_prompt: str | None = None
