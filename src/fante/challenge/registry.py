"""ChallengeRegistry — loads minigame definitions from YAML.

Each `data/challenges/*.yaml` file is one definition:

    id: math_quick
    adapter: math_quick           # which Python adapter implements this
    categories: [mental, reflexes]
    attributes: [intellect, speed]
    topics: [math]
    min_age: 5
    max_age: 99
    prompt: "Resuelve rápido:"
    config: { ... }               # adapter-specific
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from fante.domain.challenge import ChallengeCategory, ChallengeSpec
from fante.domain.profile import PlayerProfile


@dataclass(frozen=True)
class ChallengeDef:
    """A registry entry — metadata about a minigame the orchestrator can run."""

    id: str
    adapter_id: str
    categories: tuple[ChallengeCategory, ...]
    attributes: tuple[str, ...]
    topics: tuple[str, ...]
    min_age: int
    max_age: int
    prompt: str
    config: dict[str, Any] = field(default_factory=dict)

    def to_spec(self, session_topic: str | None) -> ChallengeSpec:
        # We pick the first listed category as the spec's category; the registry
        # filter ensures it matches what the rule asked for.
        return ChallengeSpec(
            id=self.id,
            adapter_id=self.adapter_id,
            prompt=self.prompt,
            category=self.categories[0],
            metadata={
                "config": dict(self.config),
                "session_topic": session_topic,
            },
        )


class ChallengeRegistry:
    """In-memory catalogue of `ChallengeDef`s.

    Use `ChallengeRegistry.from_directory(path)` to load YAML files at startup.
    """

    def __init__(self, definitions: list[ChallengeDef]) -> None:
        self._defs = list(definitions)

    @classmethod
    def from_directory(cls, path: Path) -> "ChallengeRegistry":
        defs: list[ChallengeDef] = []
        if not path.exists():
            return cls(defs)
        for file in sorted(path.glob("*.yaml")):
            with file.open() as f:
                raw = yaml.safe_load(f) or {}
            defs.append(_parse_def(raw))
        return cls(defs)

    def all(self) -> list[ChallengeDef]:
        return list(self._defs)

    def filter(
        self,
        category: ChallengeCategory,
        attribute: str | None,
        profile: PlayerProfile,
    ) -> list[ChallengeDef]:
        """Strict filters (must all pass)."""
        out = []
        for d in self._defs:
            if category not in d.categories:
                continue
            if attribute is not None and d.attributes and attribute not in d.attributes:
                continue
            if profile.age is not None and not (d.min_age <= profile.age <= d.max_age):
                continue
            out.append(d)
        return out


def _parse_def(raw: dict[str, Any]) -> ChallengeDef:
    return ChallengeDef(
        id=raw["id"],
        adapter_id=raw["adapter"],
        categories=tuple(raw.get("categories", [])),
        attributes=tuple(raw.get("attributes", [])),
        topics=tuple(raw.get("topics", [])),
        min_age=int(raw.get("min_age", 0)),
        max_age=int(raw.get("max_age", 999)),
        prompt=str(raw.get("prompt", "")),
        config=dict(raw.get("config", {})),
    )
