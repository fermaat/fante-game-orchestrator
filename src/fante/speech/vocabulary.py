"""Builds Whisper `initial_prompt` from the curated game vocabulary YAML.

The vocabulary file is grouped by category for human readability; this module
flattens the categories into a single comma-joined string and dedupes while
preserving insertion order.
"""

from pathlib import Path
from typing import Any

import yaml


def load_vocabulary(path: Path, language: str) -> str:
    """Return a comma-joined `initial_prompt` for the given language.

    `language` accepts "es", "en", or "mixed" (es+en combined).
    Returns "" if the file is empty/missing or the language has no entries.
    """
    if not path.exists():
        return ""
    with path.open() as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    if language == "mixed":
        words = _flatten(data.get("es", {})) + _flatten(data.get("en", {}))
    else:
        words = _flatten(data.get(language, {}))

    # Dedupe preserving order
    seen: dict[str, None] = {}
    for w in words:
        if w and w not in seen:
            seen[w] = None
    return ", ".join(seen)


def _flatten(by_category: dict[str, list[str]]) -> list[str]:
    out: list[str] = []
    for category_words in by_category.values():
        if category_words:
            out.extend(str(w) for w in category_words)
    return out
