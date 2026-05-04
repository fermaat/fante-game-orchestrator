"""Shared test fixtures.

Two fake levels are provided:

* `MockProvider` — a `BaseLLMProvider` returning canned text. Use it to
  exercise the real `BridgeNarrator` (BridgeEngine + history) end-to-end
  without an LLM.
* `FakeNarrator` — a port-level fake. Use it to exercise `GameManager`
  without pulling in the bridge.

`make_game` composes a `GameManager` with port-level fakes and a fixed
profile, so tests read like behaviour scenarios.
"""

from collections.abc import Callable, Generator, Iterable
from pathlib import Path
from typing import Any

import pytest
from core_llm_bridge.core.base import BaseLLMProvider
from core_llm_bridge.core.models import BridgeResponse, ConversationBuffer, LLMConfig

from fante.adapters.bridge_narrator import BridgeNarrator
from fante.domain.actor import Actor
from fante.domain.profile import Attributes, PlayerProfile
from fante.domain.rules import AppliedModifier, CheckResult, PlotDieFace, RollResult
from fante.events.bus import EventBus
from fante.manager import GameManager

# ---------- LLM-level fake -------------------------------------------------


class MockProvider(BaseLLMProvider):  # type: ignore[misc]
    """Returns canned responses one by one. Records the prompts it received."""

    def __init__(self, responses: Iterable[str], model: str = "mock") -> None:
        super().__init__(model=model)
        self._responses = list(responses)
        self.calls: list[tuple[str, list[dict[str, Any]]]] = []

    def generate(
        self,
        prompt: str,
        history: ConversationBuffer,
        config: LLMConfig | None = None,
    ) -> BridgeResponse:
        self.calls.append((prompt, history.get_messages_for_api()))
        if not self._responses:
            text = "(sin respuesta)"
        else:
            text = self._responses.pop(0)
        return BridgeResponse(text=text, finish_reason="stop")

    def generate_stream(
        self,
        prompt: str,
        history: ConversationBuffer,
        config: LLMConfig | None = None,
    ) -> Generator[BridgeResponse, None, None]:
        yield self.generate(prompt, history, config)


# ---------- Port-level fakes ----------------------------------------------


class FakeNarrator:
    def __init__(self, responses: Iterable[str]) -> None:
        self._responses = list(responses)
        self.received: list[str] = []
        self.received_check_results: list[Any] = []
        self.reset_count = 0
        self._history: list[dict[str, str]] = []

    def respond(self, user_input: str, check_result: Any = None) -> str:
        self.received.append(user_input)
        self.received_check_results.append(check_result)
        return self._responses.pop(0) if self._responses else "(sin respuesta)"

    def reset(self) -> None:
        self.reset_count += 1
        self._history = []

    def get_history(self) -> list[dict[str, str]]:
        return list(self._history)

    def seed_history(self, messages: list[dict[str, str]]) -> None:
        self._history = list(messages)


class FakeInput:
    def __init__(self, lines: Iterable[str | None]) -> None:
        self._lines: list[str | None] = list(lines)

    def read(self) -> str | None:
        return self._lines.pop(0) if self._lines else None


class FakeOutput:
    def __init__(self) -> None:
        self.emitted: list[str] = []

    def emit(self, text: str) -> None:
        self.emitted.append(text)


class FakeProfileStore:
    def __init__(self, profile: PlayerProfile) -> None:
        self._profile = profile
        self.saved: list[PlayerProfile] = []

    def load(self) -> PlayerProfile:
        return self._profile

    def save(self, profile: PlayerProfile) -> None:
        self.saved.append(profile)


class FakeSessionStore:
    def __init__(self) -> None:
        self._session: object = None
        self.save_count = 0
        self.clear_count = 0

    def save(self, session: object) -> None:
        self._session = session
        self.save_count += 1

    def load(self) -> object:
        return self._session

    def clear(self) -> None:
        self._session = None
        self.clear_count += 1


# ---------- Builders -------------------------------------------------------


class FakeRulesPort:
    def __init__(self) -> None:
        self._check_result: CheckResult | None = None

    def set_check_result(self, result: CheckResult) -> None:
        self._check_result = result

    def roll(self, spec: str) -> RollResult:
        return RollResult(spec=spec, total=10, breakdown=[10])

    def check(
        self,
        rule_id: str,
        actor: Actor,
        context: dict[str, Any] | None = None,
        player_score: int | None = None,
    ) -> CheckResult:
        if self._check_result is not None:
            return self._check_result
        return CheckResult(
            rule_id=rule_id,
            pack_name="fake",
            d20_rolls=[10],
            kept_roll=10,
            attribute_bonus=0,
            skill_bonus=0,
            situational_modifier=0,
            total=10,
            difficulty=10,
            success=True,
            plot_dice=[PlotDieFace.BLANK],
            applied_modifiers=[],
            narration_seed=None,
        )


@pytest.fixture
def sample_profile() -> PlayerProfile:
    return PlayerProfile(
        name="Fante",
        background="Joven explorador",
        preferences=["elefantes", "aventuras"],
        attributes=Attributes(
            strength=3, speed=4, intellect=3, willpower=5, awareness=4, presence=6
        ),
        language="es",
    )


@pytest.fixture
def make_game(
    sample_profile: PlayerProfile,
) -> Callable[..., tuple[GameManager, FakeInput, FakeOutput, FakeNarrator]]:
    def _build(
        narrator_responses: Iterable[str] = (),
        input_lines: Iterable[str | None] = (None,),
        profile: PlayerProfile | None = None,
    ) -> tuple[GameManager, FakeInput, FakeOutput, FakeNarrator]:
        narrator = FakeNarrator(narrator_responses)
        in_port = FakeInput(input_lines)
        out_port = FakeOutput()
        store = FakeProfileStore(profile or sample_profile)
        game = GameManager(
            narrator=narrator,
            input_port=in_port,
            output_port=out_port,
            profile_store=store,
            bus=EventBus(),
        )
        return game, in_port, out_port, narrator

    return _build


@pytest.fixture
def make_bridge_narrator(
    sample_profile: PlayerProfile,
) -> Callable[..., tuple[BridgeNarrator, MockProvider]]:
    def _build(
        responses: Iterable[str] = ("Una respuesta cualquiera.",),
        profile: PlayerProfile | None = None,
    ) -> tuple[BridgeNarrator, MockProvider]:
        provider = MockProvider(responses)
        narrator = BridgeNarrator(provider=provider, profile=profile or sample_profile)
        return narrator, provider

    return _build


@pytest.fixture
def tmp_profile_path(tmp_path: Path, sample_profile: PlayerProfile) -> Path:
    path = tmp_path / "player_profile.json"
    path.write_text(sample_profile.model_dump_json(indent=2), encoding="utf-8")
    return path
