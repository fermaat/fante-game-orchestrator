"""Phase 4.0 minitest — eyeball the event → SceneState seam end to end.

Builds the real WorldDirector from data/world_manifest.yaml, wires it to the
EventBus via install_world_view, and replays a scripted turn. Each pushed
SceneState is printed as the JSON a renderer would receive over WebSocket.

Run:  pdm run python examples/world_seam_demo.py
"""

from pathlib import Path

from fante.domain.events import ActionClassified, CheckResolved, TurnFinished
from fante.domain.rules import CheckResult, PlotDieFace
from fante.domain.scene import SceneState
from fante.domain.turn import ActionIntent
from fante.events.bus import EventBus
from fante.events.world_view import install_world_view
from fante.world.director import WorldDirector
from fante.world.manifest import WorldManifest


class PrintingWorldPort:
    """A WorldPort that prints each SceneState as the renderer would receive it."""

    def push(self, scene: SceneState) -> None:
        print(f"   → {scene.model_dump_json()}")


def _check(success: bool, topic: str | None) -> CheckResult:
    return CheckResult(
        rule_id="climb",
        pack_name="physics_basic",
        d20_rolls=[15],
        kept_roll=15,
        attribute_bonus=3,
        skill_bonus=0,
        situational_modifier=0,
        total=18,
        difficulty=12,
        success=success,
        plot_dice=[PlotDieFace.BLANK],
        applied_modifiers=[],
        narration_seed=None,
        knowledge_topic=topic,
    )


def main() -> None:
    manifest = WorldManifest.from_file(Path("data/world_manifest.yaml"))
    bus = EventBus()
    install_world_view(bus, PrintingWorldPort(), WorldDirector(manifest))

    print(f"Manifest loaded — protagonist={manifest.protagonist!r}\n")

    print("1) Player tries to climb  →  pose should become 'climbing'")
    bus.publish(ActionClassified(turn_index=1, intent=ActionIntent(rule_id="climb")))

    print("\n2) Check succeeds in the 'adventure' topic  →  sparkle + happy + forest")
    bus.publish(CheckResolved(turn_index=1, result=_check(success=True, topic="adventure")))

    print("\n3) Turn finished  →  back to idle/neutral, fx cleared")
    bus.publish(TurnFinished(turn_index=1))

    print("\n4) Unknown action 'teleport'  →  not in manifest, falls back to 'idle'")
    bus.publish(ActionClassified(turn_index=2, intent=ActionIntent(rule_id="teleport")))

    print("\n5) Check fails  →  puff + sad (background sticks at 'forest')")
    bus.publish(CheckResolved(turn_index=2, result=_check(success=False, topic=None)))


if __name__ == "__main__":
    main()
