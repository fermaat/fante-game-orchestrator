"""ColorNamingChallenge — say-a-color minigame.

Picks one entry from `config.pool`, prompts the player, matches their answer
against `accepted` (case + accent insensitive).

Adapter config:
  pool:
    - prompt: "¿De qué color es la madera mojada?"
      accepted: [marrón, marron, café, oscuro]
    - prompt: "¿De qué color es el cielo de noche?"
      accepted: [negro, "azul oscuro"]
"""

import random
import unicodedata
from typing import Any

from fante.domain.challenge import ChallengeSpec
from fante.domain.profile import PlayerProfile
from fante.ports.io import InputPort, OutputPort


def _normalize(s: str) -> str:
    # Lowercase + strip accents — kids spell loosely.
    nfd = unicodedata.normalize("NFD", s.lower().strip())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


class ColorNamingChallenge:
    def __init__(
        self,
        input_port: InputPort,
        output_port: OutputPort,
        rng: random.Random | None = None,
    ) -> None:
        self._in = input_port
        self._out = output_port
        self._rng = rng or random.Random()

    def run(self, spec: ChallengeSpec, user_input: str, profile: PlayerProfile) -> int:
        cfg = spec.metadata.get("config", {})
        pool: list[dict[str, Any]] = cfg.get("pool", [])
        if not pool:
            return 0
        entry = self._rng.choice(pool)
        prompt: str = entry.get("prompt", spec.prompt)
        accepted: list[str] = entry.get("accepted", [])

        self._out.emit(prompt)
        answer = self._in.read()
        if answer is None:
            return 0
        normalized = _normalize(answer)
        if any(_normalize(a) == normalized for a in accepted):
            self._out.emit("¡Eso es!")
            return 17
        self._out.emit(f"(Aceptable, aunque yo pensaba en: {', '.join(accepted[:2])}.)")
        return 9
