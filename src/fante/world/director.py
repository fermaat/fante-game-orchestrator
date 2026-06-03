"""WorldDirector — translates domain events into a SceneState.

Rule-based (no LLM): it walks the manifest to map game concepts to visuals.
It holds the orchestrator-side *scene intent* (current background, the
protagonist's pose/mood, transient fx) and rebuilds a full, idempotent
`SceneState` after each relevant event.

Anything not declared in the manifest is dropped (and logged), so the
renderer only ever receives ids it can draw.
"""

from core_utils import logger

from fante.domain.rules import CheckResult
from fante.domain.scene import ActorView, SceneState
from fante.domain.turn import ActionIntent
from fante.world.manifest import WorldManifest


class WorldDirector:
    def __init__(self, manifest: WorldManifest) -> None:
        self._manifest = manifest
        self._background = manifest.default_background
        self._pose = "idle"
        self._mood = "neutral"
        self._fx: list[str] = []

    def on_action(self, intent: ActionIntent) -> None:
        """An action was classified — pose the protagonist accordingly."""
        pose = self._manifest.action_poses.get(intent.rule_id, "idle")
        self._pose = self._validated_pose(pose)
        self._fx = []

    def on_check(self, result: CheckResult) -> None:
        """A check resolved — react with fx, mood and (maybe) a new background."""
        outcome = "success" if result.success else "failure"
        effect = self._manifest.outcome_fx.get(outcome)
        self._fx = [effect] if effect and self._manifest.has_fx(effect) else []
        self._mood = self._validated_mood("happy" if result.success else "sad")

        if result.knowledge_topic:
            background = self._manifest.topic_backgrounds.get(result.knowledge_topic)
            if background and self._manifest.has_background(background):
                self._background = background

    def on_turn_finished(self) -> None:
        """Return the protagonist to rest between turns."""
        self._pose = "idle"
        self._mood = "neutral"
        self._fx = []

    def build_scene(self) -> SceneState:
        return SceneState(
            background=self._background,
            actors=[
                ActorView(
                    id=self._manifest.protagonist,
                    pose=self._pose,
                    mood=self._mood,
                )
            ],
            fx=list(self._fx),
        )

    def _validated_pose(self, pose: str) -> str:
        protagonist = self._manifest.protagonist
        if self._manifest.has_pose(protagonist, pose):
            return pose
        logger.warning(f"world: unknown pose {pose!r} for {protagonist!r}; using 'idle'")
        return "idle"

    def _validated_mood(self, mood: str) -> str:
        protagonist = self._manifest.protagonist
        if self._manifest.has_mood(protagonist, mood):
            return mood
        return "neutral"
