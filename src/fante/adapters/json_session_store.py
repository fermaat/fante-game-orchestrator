"""JSONSessionStore — SessionStore adapter backed by a local JSON file."""

from pathlib import Path

from fante.domain.session import Session


class JSONSessionStore:
    """Persists a Session as JSON at `path`. Creates parent dirs on first save."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, session: Session) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(session.model_dump_json(indent=2), encoding="utf-8")

    def load(self) -> Session | None:
        if not self._path.exists():
            return None
        return Session.model_validate_json(self._path.read_text(encoding="utf-8"))

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()
