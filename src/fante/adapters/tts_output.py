"""TTSOutput — OutputPort that synthesizes via core-speech-io-hub and plays locally.

Also echoes the text to stdout by default so the parent can read along on screen.
"""

from core_utils import logger
from speech_io_hub.client.client import SpeechClient


class TTSOutput:
    def __init__(
        self,
        client: SpeechClient,
        echo_to_stdout: bool = True,
        voice: str | None = None,
    ) -> None:
        self._client = client
        self._echo = echo_to_stdout
        self._voice = voice

    def emit(self, text: str) -> None:
        if self._echo:
            print(text)
        try:
            self._client.say(text, voice=self._voice)
        except Exception:
            logger.exception("speech synthesis failed; continuing without audio")
