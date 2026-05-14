"""ChallengeDispatcher — implements `ChallengePort` by routing to a concrete adapter.

GameManager sees a single `ChallengePort`. Internally, the dispatcher inspects
`spec.adapter_id` and delegates to the registered adapter for that id.

This keeps GameManager unaware of how many minigames exist or how they're
implemented — adding a new minigame is a registration step, not a manager change.
"""

from fante.domain.challenge import ChallengeSpec
from fante.domain.profile import PlayerProfile
from fante.ports.challenge import ChallengePort


class ChallengeDispatcher:
    def __init__(self, adapters: dict[str, ChallengePort]) -> None:
        self._adapters = dict(adapters)

    def register(self, adapter_id: str, adapter: ChallengePort) -> None:
        self._adapters[adapter_id] = adapter

    def run(self, spec: ChallengeSpec, user_input: str, profile: PlayerProfile) -> int:
        adapter = self._adapters.get(spec.adapter_id)
        if adapter is None:
            raise KeyError(f"No challenge adapter registered for id '{spec.adapter_id}'")
        return adapter.run(spec, user_input, profile)
