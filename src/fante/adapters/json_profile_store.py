"""JSON-file ProfileStore adapter."""

import json
import logging
from pathlib import Path
from typing import Any

from fante.domain.profile import Attributes, PlayerProfile

_log = logging.getLogger(__name__)

_V1_DEFAULT_ATTRIBUTE = 4


def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    _log.warning(
        "Profile is schema_version 1 — auto-migrating to v2. "
        "Update data/player_profile.json to silence this warning."
    )
    data = dict(data)
    data.pop("stats", None)
    data["schema_version"] = 2
    data.setdefault("attributes", {k: _V1_DEFAULT_ATTRIBUTE for k in Attributes.model_fields})
    data.setdefault("skills", {})
    data.setdefault("tags", [])
    return data


class JSONProfileStore:
    """Loads and persists a `PlayerProfile` from a JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> PlayerProfile:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        if data.get("schema_version", 1) == 1:
            data = _migrate_v1_to_v2(data)
        return PlayerProfile.model_validate(data)

    def save(self, profile: PlayerProfile) -> None:
        self._path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
