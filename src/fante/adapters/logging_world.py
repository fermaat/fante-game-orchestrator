"""LoggingWorldAdapter — a WorldPort stub that logs each SceneState.

Lets domain events visibly "flow toward a screen" with no renderer at all.
Replaced by a `WebSocketWorldAdapter` once the `fante-world-web` repo exists.
"""

from core_utils import logger

from fante.domain.scene import SceneState


class LoggingWorldAdapter:
    """WorldPort adapter that logs the scene instead of drawing it."""

    def push(self, scene: SceneState) -> None:
        logger.info(f"[world] {scene.model_dump_json()}")
