"""PlayerProfile — versioned schema describing the player character."""

from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["es", "en", "mixed"]


class Attributes(BaseModel):
    """Cosmere-model character attributes, 0–8 each."""

    strength: int = 0
    speed: int = 0
    intellect: int = 0
    willpower: int = 0
    awareness: int = 0
    presence: int = 0


class PlayerProfile(BaseModel):
    """Player character sheet.

    `schema_version` is bumped whenever the schema changes in a
    backwards-incompatible way. Loaders should branch on it.
    """

    schema_version: int = 2
    name: str
    background: str = ""
    preferences: list[str] = Field(default_factory=list)
    attributes: Attributes = Field(default_factory=Attributes)
    skills: dict[str, int] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    language: Language = "es"
    seed_prompt: str | None = None
