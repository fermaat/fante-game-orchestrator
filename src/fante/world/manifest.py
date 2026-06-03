"""WorldManifest — single source of truth for what the visual layer can show.

Loaded from YAML (`data/world_manifest.yaml`). Consumed by the
`WorldDirector` to validate and map game concepts to visuals, and (future)
injected into the narrator prompt so it leans toward showable actions.

The manifest is game-specific *data*; the director and port are generic.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ActorManifest(BaseModel):
    """Declared poses and moods for one actor."""

    poses: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)


class WorldManifest(BaseModel):
    """Declares every background, actor, pose, mood and fx the screen knows,
    plus the maps from game concepts to those visuals."""

    protagonist: str
    default_background: str | None = None
    backgrounds: list[str] = Field(default_factory=list)
    actors: dict[str, ActorManifest] = Field(default_factory=dict)
    fx: list[str] = Field(default_factory=list)

    # game concept → visual
    action_poses: dict[str, str] = Field(default_factory=dict)
    topic_backgrounds: dict[str, str] = Field(default_factory=dict)
    outcome_fx: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> "WorldManifest":
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.model_validate(data)

    def has_pose(self, actor_id: str, pose: str) -> bool:
        actor = self.actors.get(actor_id)
        return actor is not None and pose in actor.poses

    def has_mood(self, actor_id: str, mood: str) -> bool:
        actor = self.actors.get(actor_id)
        return actor is not None and mood in actor.moods

    def has_background(self, background: str) -> bool:
        return background in self.backgrounds

    def has_fx(self, effect: str) -> bool:
        return effect in self.fx
