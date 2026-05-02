"""Session domain type — persisted state between game runs."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Session(BaseModel):
    """Snapshot of a game session that can be saved and restored."""

    turn_index: int = 0
    history: list[dict[str, str]] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
