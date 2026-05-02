"""Functional tests for BridgeNarrator — real BridgeEngine, MockProvider."""

import pytest

pytestmark = pytest.mark.functional


def test_system_prompt_includes_profile_data(make_bridge_narrator) -> None:  # type: ignore[no-untyped-def]
    narrator, provider = make_bridge_narrator(responses=["¡Hola, Fante!"])

    narrator.respond("hola")

    # The first call's history starts with the system prompt.
    _, messages = provider.calls[0]
    system_msg = next(m for m in messages if m["role"] == "system")
    assert "Fante" in system_msg["content"]
    assert "elefantes" in system_msg["content"]
    assert "español" in system_msg["content"].lower()


def test_history_persists_across_turns(make_bridge_narrator) -> None:  # type: ignore[no-untyped-def]
    narrator, provider = make_bridge_narrator(responses=["resp1", "resp2"])

    narrator.respond("primero")
    narrator.respond("segundo")

    # Second call's history must include the first user/assistant exchange.
    _, second_history = provider.calls[1]
    user_messages = [m["content"] for m in second_history if m["role"] == "user"]
    assistant_messages = [m["content"] for m in second_history if m["role"] == "assistant"]
    assert "primero" in user_messages
    assert "resp1" in assistant_messages


def test_reset_clears_history(make_bridge_narrator) -> None:  # type: ignore[no-untyped-def]
    narrator, provider = make_bridge_narrator(responses=["a", "b"])

    narrator.respond("primero")
    narrator.reset()
    narrator.respond("segundo")

    _, second_history = provider.calls[1]
    user_messages = [m["content"] for m in second_history if m["role"] == "user"]
    assert "primero" not in user_messages
    assert user_messages == ["segundo"]


def test_language_field_changes_system_prompt(make_bridge_narrator) -> None:  # type: ignore[no-untyped-def]
    from fante.domain.profile import PlayerProfile

    profile_en = PlayerProfile(name="Fante", language="en")
    narrator, provider = make_bridge_narrator(responses=["Hi"], profile=profile_en)
    narrator.respond("hi")

    _, messages = provider.calls[0]
    system_msg = next(m for m in messages if m["role"] == "system")
    assert "english" in system_msg["content"].lower()
