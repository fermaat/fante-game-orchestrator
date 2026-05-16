"""WhisperInput — InputPort that records via VAD and transcribes via core-speech-io-hub.

In voice mode, `read()` blocks until the user speaks and stops. Returns the empty
string when no speech is detected or transcription fails (the GameManager loop
treats empty as 'try again', not as EOF).
"""

from core_utils import logger
from speech_io_hub.audio.vad import record_until_silence
from speech_io_hub.client.client import SpeechClient


class WhisperInput:
    def __init__(
        self,
        client: SpeechClient,
        language: str = "es",
        initial_prompt: str | None = None,
        prompt_user: bool = True,
    ) -> None:
        self._client = client
        self._language = language
        self._initial_prompt = initial_prompt
        self._prompt_user = prompt_user

    def read(self) -> str | None:
        if self._prompt_user:
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
