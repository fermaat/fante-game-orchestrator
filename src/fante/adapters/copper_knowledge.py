"""CopperKnowledgeAdapter — KnowledgePort backed by a running copper server."""

import json
from typing import Any

import httpx

from core_utils import logger


class CopperKnowledgeAdapter:
    """KnowledgePort that calls copper's POST /minds/{mind}/tap endpoint.

    Fails loudly on any HTTP or connection error — no silent fallback.
    """

    def __init__(self, copper_url: str, mind_map: dict[str, str]) -> None:
        self._base_url = copper_url.rstrip("/")
        self._mind_map = mind_map

    def query(self, topic: str, context: dict[str, Any] | None = None) -> str:
        mind = self._mind_map.get(topic)
        if mind is None:
            raise ValueError(f"No copper mind configured for topic '{topic}'")

        personality = f"tap.{topic}"
        question = json.dumps(context or {})
        url = f"{self._base_url}/minds/{mind}/tap"

        logger.info("copper_knowledge | topic=%s mind=%s url=%s", topic, mind, url)

        response = httpx.post(
            url,
            json={"question": question, "personality": personality},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return str(data["answer"])
