"""Functional tests for WhisperInput."""

import pytest

from fante.adapters.whisper_input import WhisperInput

from tests.conftest import MockSpeechClient


@pytest.mark.functional
def test_whisper_input_returns_transcription(monkeypatch):
    monkeypatch.setattr(
        "fante.adapters.whisper_input.record_until_silence",
        lambda **kw: b"RIFF\x24\x00\x00\x00fake-wav",
    )
    client = MockSpeechClient(transcripts=["trepar el muro"])
    inp = WhisperInput(client=client, language="es", initial_prompt="trepar, saltar")
    assert inp.read() == "trepar el muro"
    assert client.transcribe_calls[0]["language"] == "es"
    assert client.transcribe_calls[0]["initial_prompt"] == "trepar, saltar"


@pytest.mark.functional
def test_whisper_input_returns_empty_on_no_speech(monkeypatch):
    def raise_no_speech(**kw):
        raise RuntimeError("No speech detected.")

    monkeypatch.setattr(
        "fante.adapters.whisper_input.record_until_silence",
        raise_no_speech,
    )
    inp = WhisperInput(client=MockSpeechClient())
    assert inp.read() == ""


@pytest.mark.functional
def test_whisper_input_swallows_transcription_errors(monkeypatch):
    monkeypatch.setattr(
        "fante.adapters.whisper_input.record_until_silence",
        lambda **kw: b"RIFF",
    )

    class BoomClient(MockSpeechClient):
        def transcribe(self, *a, **kw):
            raise RuntimeError("server down")

    inp = WhisperInput(client=BoomClient())
    assert inp.read() == ""  # logged, not raised
