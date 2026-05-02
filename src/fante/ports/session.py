"""SessionStore — capability of persisting and restoring game sessions."""

from typing import Protocol

from fante.domain.session import Session


class SessionStore(Protocol):
    def save(self, session: Session) -> None:
        """Persist the current session to durable storage."""
        ...

    def load(self) -> Session | None:
        """Load the last saved session, or None if no session exists."""
        ...

    def clear(self) -> None:
        """Delete any saved session (used on --reset)."""
        ...
