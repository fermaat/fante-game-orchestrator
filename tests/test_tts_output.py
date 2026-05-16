"""Functional tests for TTSOutput."""

import pytest

from fante.adapters.tts_output import TTSOutput

from tests.conftest import MockSpeechClient


@pytest.mark.functional
def test_tts_output_calls_say():
    client = MockSpeechClient()
    out = TTSOutput(client=client, echo_to_stdout=False)
    out.emit("hola fante")
    assert client.say_calls == [{"text": "hola fante", "voice": None}]


@pytest.mark.functional
def test_tts_output_echoes_to_stdout(capsys):
    client = MockSpeechClient()
    out = TTSOutput(client=client, echo_to_stdout=True)
    out.emit("texto visible")
    captured = capsys.readouterr()
    assert "texto visible" in captured.out


@pytest.mark.functional
def test_tts_output_swallows_synth_errors():
    class BoomClient(MockSpeechClient):
        def say(self, *a, **kw):
            raise RuntimeError("synth crashed")

    out = TTSOutput(client=BoomClient(), echo_to_stdout=False)
    out.emit("hola")  # should not raise
