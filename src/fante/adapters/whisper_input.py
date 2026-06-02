"""WhisperInput — InputPort that records via VAD and transcribes via core-speech-io-hub.

Two input modes:
  - "push_to_talk" (default): the user presses Enter on the terminal; then the mic
    opens and the VAD captures their utterance. This avoids feedback from TTS and
    music playing through the speakers being picked up by the mic.
    As a bonus, typed text + Enter is returned directly without opening the mic
    (handy for debugging or when audio is unreliable).
  - "vad": legacy always-listening behaviour — the mic opens immediately on each
    turn and the VAD decides when the utterance ends. Kept available for testing
    or for environments where push-to-talk isn't practical.

`read()` returns the empty string on no-speech / transcription failure (the
GameManager loop treats empty as "try again", not as EOF). It returns None only
when stdin closes during push-to-talk waiting.
"""

import sys
from typing import Literal

from core_utils import logger
from speech_io_hub.audio.vad import record_until_silence
from speech_io_hub.client.client import SpeechClient

try:
    import termios

    _HAS_TERMIOS = True
except ImportError:
    _HAS_TERMIOS = False

InputMode = Literal["push_to_talk", "vad"]


def _flush_stdin() -> None:
    """Discard any Enter / characters buffered in stdin before prompting.

    Prevents the "phantom Enter" effect where a queued Enter from a previous
    turn causes input() to return immediately, making it look like the user
    didn't press anything but the mic opened anyway. Best-effort: no-op when
    stdin isn't a terminal (CI, pipes) or on non-POSIX systems.
    """
    if not _HAS_TERMIOS:
        return
    try:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except (termios.error, OSError):
        pass


class WhisperInput:
    def __init__(
        self,
        client: SpeechClient,
        language: str = "es",
        initial_prompt: str | None = None,
        prompt_user: bool = True,
        input_mode: InputMode = "push_to_talk",
    ) -> None:
        self._client = client
        self._language = language
        self._initial_prompt = initial_prompt
        self._prompt_user = prompt_user
        self._input_mode = input_mode

    def read(self) -> str | None:
        if self._input_mode == "push_to_talk":
            _flush_stdin()  # discard buffered Enter from previous turns
            print("(Pulsa Enter y habla — o escribe y pulsa Enter)", flush=True)
            try:
                typed = input().strip()
            except EOFError:
                return None
            if typed:
                # User typed something instead of just hitting Enter — use it
                # directly and skip the mic. Useful for parents debugging or
                # when audio is unreliable in this turn.
                return typed
            print("(Escuchando...)", flush=True)
        elif self._prompt_user:
            print("(habla cuando quieras)", flush=True)

        try:
            wav = record_until_silence()
        except RuntimeError:
            return ""
        try:
            result = self._client.transcribe(
                wav,
                language=self._language,
                initial_prompt=self._initial_prompt,
            )
        except Exception:
            logger.exception("transcription failed")
            return ""
        text = str(result.get("text", "")).strip()
        if text:
            print(f"> {text}")
        return text  # may be ""; manager loop continues
