"""WorldPort — sink for visual scene state delivered to a renderer.

The orchestrator depends only on `push`. Concrete adapters (a logging stub
now, a WebSocket client once the renderer repo exists) live in
`fante.adapters`.

The input back-channel (renderer → orchestrator, for interactive minigames)
is intentionally not part of this protocol yet; it lands in Phase 4.2 with the
first visual `ChallengePort`. See `docs/world_engine_design.md`.
"""

from typing import Protocol

from fante.domain.scene import SceneState


class WorldPort(Protocol):
    """Sink for the desired scene state."""

    def push(self, scene: SceneState) -> None: ...
