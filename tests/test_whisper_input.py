"""Functional tests for WhisperInput."""

import builtins

import pytest

from fante.adapters.whisper_input import WhisperInput

from tests.conftest import MockSpeechClient

# ---------- VAD mode (legacy) ---------------------------------------------


@pytest.mark.functional
def test_vad_mode_returns_transcription(monkeypatch):
    monkeypatch.setattr(
        "fante.adapters.whisper_input.record_until_silence",
        lambda **kw: b"RIFF\x24\x00\x00\x00fake-wav",
    )
    client = MockSpeechClient(transcripts=["trepar el muro"])
    inp = WhisperInput(
        client=client,
        language="es",
        initial_prompt="trepar, saltar",
        input_mode="vad",
    )
    assert inp.read() == "trepar el muro"
    assert client.transcribe_calls[0]["language"] == "es"
    assert client.transcribe_calls[0]["initial_prompt"] == "trepar, saltar"


@pytest.mark.functional
def test_vad_mode_returns_empty_on_no_speech(monkeypatch):
    def raise_no_speech(**kw):
        raise RuntimeError("No speech detected.")

    monkeypatch.setattr(
        "fante.adapters.whisper_input.record_until_silence",
        raise_no_speech,
    )
    inp = WhisperInput(client=MockSpeechClient(), input_mode="vad")
    assert inp.read() == ""


@pytest.mark.functional
def test_vad_mode_swallows_transcription_errors(monkeypatch):
    monkeypatch.setattr(
        "fante.adapters.whisper_input.record_until_silence",
        lambda **kw: b"RIFF",
    )

    class BoomClient(MockSpeechClient):
        def transcribe(self, *a, **kw):
            raise RuntimeError("server down")

    inp = WhisperInput(client=BoomClient(), input_mode="vad")
    assert inp.read() == ""


# ---------- Push-to-talk mode (default) ----------------------------------


@pytest.mark.functional
def test_push_to_talk_enter_then_voice(monkeypatch):
    """User hits Enter with no typed text → mic opens, voice transcribed."""
    monkeypatch.setattr(builtins, "input", lambda: "")
    monkeypatch.setattr(
        "fante.adapters.whisper_input.record_until_silence",
        lambda **kw: b"RIFF\x24\x00\x00\x00fake",
    )
    client = MockSpeechClient(transcripts=["pon el caballo"])
    inp = WhisperInput(client=client, input_mode="push_to_talk")
    assert inp.read() == "pon el caballo"
    assert len(client.transcribe_calls) == 1  # mic was used


@pytest.mark.functional
def test_push_to_talk_typed_text_bypasses_mic(monkeypatch):
    """User types text before Enter → that's the input, no mic call."""
    monkeypatch.setattr(builtins, "input", lambda: "trepa el muro  ")  # with extra ws

    def should_not_be_called(**kw):
        raise AssertionError("mic should not open when text was typed")

    monkeypatch.setattr(
        "fante.adapters.whisper_input.record_until_silence",
        should_not_be_called,
    )
    client = MockSpeechClient()
    inp = WhisperInput(client=client, input_mode="push_to_talk")
    assert inp.read() == "trepa el muro"  # stripped
    assert len(client.transcribe_calls) == 0


@pytest.mark.functional
def test_push_to_talk_eof_returns_none(monkeypatch):
    """stdin closed during push-to-talk wait → return None (signals EOF)."""

    def raise_eof():
        raise EOFError

    monkeypatch.setattr(builtins, "input", raise_eof)
    inp = WhisperInput(client=MockSpeechClient(), input_mode="push_to_talk")
    assert inp.read() is None


@pytest.mark.functional
def test_default_is_push_to_talk(monkeypatch):
    """Constructor default mode should be push_to_talk (not VAD)."""
    monkeypatch.setattr(builtins, "input", lambda: "")
    monkeypatch.setattr(
        "fante.adapters.whisper_input.record_until_silence",
        lambda **kw: b"RIFF",
    )
    client = MockSpeechClient(transcripts=["ok"])
    inp = WhisperInput(client=client)  # no input_mode argument
    assert inp.read() == "ok"
