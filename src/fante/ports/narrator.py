"""NarratorPort — capability of producing narrative responses to player input."""

from typing import Protocol


class NarratorPort(Protocol):
    """Generates narration in reply to player input.

    The narrator owns its own conversation memory; the orchestrator does not
    pass history in. Adapters decide how to persist/prune history (e.g. the
    bridge adapter delegates to `BridgeEngine`'s `ConversationBuffer`).
    """

    def respond(self, user_input: str) -> str:
        """Generate a narration in reply to a single player utterance."""
        ...

    def reset(self) -> None:
        """Clear conversation memory. Used on game restart or scene change."""
        ...
