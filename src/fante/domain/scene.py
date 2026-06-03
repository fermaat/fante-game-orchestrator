"""Scene domain types — the wire contract for the visual layer.

`SceneState` is declarative and idempotent: every push carries a *full*
description of the desired scene, so a renderer just animates toward it.
The orchestrator owns the truth; the renderer holds only ephemeral
presentation state (tweens, particles).
"""

from pydantic import BaseModel, Field


class ActorView(BaseModel):
    """An actor as it should be drawn this frame."""

    id: str
    pose: str = "idle"
    mood: str = "neutral"


class SceneState(BaseModel):
    """Full description of the scene the renderer should display."""

    background: str | None = None
    actors: list[ActorView] = Field(default_factory=list)
    fx: list[str] = Field(default_factory=list)
