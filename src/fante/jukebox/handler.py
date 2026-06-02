"""JukeboxHandler — process one turn while fante is in jukebox mode.

Delegates all audio I/O to core-music-hub via MusicHubClient. The handler is pure
translation: voice intent → HTTP call → user-facing message.
"""

from core_music_hub.client.client import MusicHubClient, SongNotFoundError
from core_utils import logger

from fante.jukebox.intent import JukeboxIntent, JukeboxIntentClassifier


class JukeboxHandler:
    """Translates a classified jukebox intent into MusicHubClient calls.

    Returns a (message, should_exit) pair from `process()` so the caller
    (GameManager) can switch mode without the handler knowing about GameManager.
    """

    def __init__(
        self,
        client: MusicHubClient,
        classifier: JukeboxIntentClassifier,
    ) -> None:
        self._client = client
        self._classifier = classifier

    def process(self, player_input: str) -> tuple[str, bool]:
        """Process one jukebox turn.

        Returns (message_to_player, should_exit_jukebox_mode).
        """
        intent = self._classifier.classify(player_input)
        logger.debug(f"jukebox.intent action={intent.action} song_query={intent.song_query!r}")

        if intent.action == "play":
            return self._handle_play(intent), False
        if intent.action == "stop":
            try:
                self._client.stop()
            except Exception:
                logger.exception("jukebox: stop failed")
            return "Música parada.", False
        if intent.action == "next":
            return self._handle_next(), False
        if intent.action == "list":
            return self._handle_list(), False
        if intent.action == "exit":
            try:
                self._client.stop()
            except Exception:
                pass
            return "Dejo la música. ¡Volvemos a la aventura!", True
        return "No te he entendido. Pide una canción, di 'otra', 'para', o 'salir'.", False

    def _handle_play(self, intent: JukeboxIntent) -> str:
        query = (intent.song_query or "").strip()
        if not query:
            return "¿Qué canción quieres oír?"
        try:
            result = self._client.play(alias=query)
        except SongNotFoundError:
            return f"No conozco «{query}». Di 'lista' para oír las que tengo."
        except Exception:
            logger.exception("jukebox: play failed")
            return "Algo ha fallado al poner la música. Inténtalo de nuevo."
        return f"Ahora suena: {result['title']}."

    def _handle_next(self) -> str:
        try:
            result = self._client.next()
        except SongNotFoundError:
            return "Sólo tengo una canción y ya estaba sonando."
        except Exception:
            logger.exception("jukebox: next failed")
            return "Algo ha fallado al cambiar de canción."
        return f"Cambiando a: {result['title']}."

    def _handle_list(self) -> str:
        try:
            songs = self._client.catalog()
        except Exception:
            logger.exception("jukebox: catalog failed")
            return "No he podido pedir la lista."
        if not songs:
            return "No tengo ninguna canción todavía."
        titles = ", ".join(s["title"] for s in songs[:8])
        if len(songs) > 8:
            titles += f", y {len(songs) - 8} más"
        return f"Tengo: {titles}."
