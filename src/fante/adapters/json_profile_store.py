"""JSON-file ProfileStore adapter."""

import json
from pathlib import Path

from fante.domain.profile import PlayerProfile


class JSONProfileStore:
    """Loads and persists a `PlayerProfile` from a JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> PlayerProfile:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return PlayerProfile.model_validate(data)

    def save(self, profile: PlayerProfile) -> None:
        self._path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
