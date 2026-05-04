"""NarratorPort — capability of producing narrative responses to player input."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from fante.domain.rules import CheckResult


class NarratorPort(Protocol):
    """Generates narration in reply to player input.

    The narrator owns its own conversation memory; the orchestrator does not
    pass history in. Adapters decide how to persist/prune history (e.g. the
    bridge adapter delegates to `BridgeEngine`'s `ConversationBuffer`).
    """

    def respond(self, user_input: str, check_result: "CheckResult | None" = None) -> str:
        """Generate a narration. If check_result is given, weave its narration_seed."""
        ...

    def reset(self) -> None:
        """Clear conversation memory. Used on game restart or scene change."""
        ...

    def get_history(self) -> list[dict[str, str]]:
        """Return current conversation as a list of role/content dicts."""
        ...

    def seed_history(self, messages: list[dict[str, str]]) -> None:
        """Replace conversation history from a list of role/content dicts."""
        ...
