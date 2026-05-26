"""RepeatExpressionChallenge — repeat-after-me minigame.

Designed for very young kids: the narrator says a short expression (a sound, an
action verb, a phrase) and the player has to repeat it. Scoring is **forgiving by
design** — token overlap, not exact match — because a 2-year-old's pronunciation
is still developing and Whisper's transcription will wobble.

Adapter config:
  pool:
    - expression: "trepa trepa trepa"
    - expression: "uno dos tres"
    - expression: "¡abracadabra!"
"""

import random
import unicodedata
from typing import Any

from fante.domain.challenge import ChallengeSpec
from fante.domain.profile import PlayerProfile
from fante.ports.io import InputPort, OutputPort


def _normalize(s: str) -> str:
    """Lowercase, strip accents/punctuation, collapse whitespace."""
    nfd = unicodedata.normalize("NFD", s.lower().strip())
    flat = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    flat = "".join(c if c.isalnum() or c.isspace() else " " for c in flat)
    return " ".join(flat.split())


def _tokens(s: str) -> set[str]:
    return set(_normalize(s).split())


class RepeatExpressionChallenge:
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
        expression: str = entry["expression"]

        self._out.emit(f"{spec.prompt} {expression}")
        answer = self._in.read()
        if not answer or not answer.strip():
            self._out.emit(f"(¡Te tocaba repetir «{expression}»!)")
            return 5

        expected = _tokens(expression)
        said = _tokens(answer)
        if not expected:
            return 10
        coverage = len(expected & said) / len(expected)
        if coverage >= 0.5:
            self._out.emit("¡Bien dicho!")
            return 18
        self._out.emit(f"(Casi: era «{expression}».)")
        return 10
