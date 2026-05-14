"""MathQuickChallenge — quick arithmetic minigame.

Generates a problem like `7 + 4 = ?`, prompts the player, validates the answer.
Returns a score in [0, 20]: 18 on correct first try, lower on incorrect.

Adapter config (from YAML):
  operations: [add, subtract]    # which operators to use
  max_operand: 10                # operands range [1, max_operand]
"""

import random
from collections.abc import Callable

from fante.domain.challenge import ChallengeSpec
from fante.domain.profile import PlayerProfile
from fante.ports.io import InputPort, OutputPort

_OPS: dict[str, tuple[str, Callable[[int, int], int]]] = {
    "add": ("+", lambda a, b: a + b),
    "subtract": ("-", lambda a, b: a - b),
}


class MathQuickChallenge:
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
        ops_cfg = cfg.get("operations", ["add"])
        max_op = int(cfg.get("max_operand", 10))

        op_name = self._rng.choice(ops_cfg)
        symbol, fn = _OPS[op_name]
        a = self._rng.randint(1, max_op)
        b = self._rng.randint(1, max_op)
        if op_name == "subtract" and b > a:
            a, b = b, a  # keep result non-negative for young players
        expected = fn(a, b)

        self._out.emit(f"{spec.prompt} {a} {symbol} {b} = ?")
        answer = self._in.read()
        if answer is None:
            return 0
        try:
            given = int(answer.strip())
        except ValueError:
            self._out.emit(f"(Esperaba un número; la respuesta era {expected}.)")
            return 6
        if given == expected:
            self._out.emit("¡Correcto!")
            return 18
        self._out.emit(f"(Casi: la respuesta era {expected}.)")
        return 8
