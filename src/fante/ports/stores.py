"""Persistence ports — read/write game-domain state.

Phase 1.0 only needs ProfileStore. SessionStore arrives in Phase 1.5.
"""

from typing import Protocol

from fante.domain.profile import PlayerProfile


class ProfileStore(Protocol):
    """Load and persist the player profile."""

    def load(self) -> PlayerProfile: ...

    def save(self, profile: PlayerProfile) -> None: ...
