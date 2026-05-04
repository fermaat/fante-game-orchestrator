"""Actor domain type — mirrors mcp-game-rules wire format without importing it."""

from pydantic import BaseModel

from fante.domain.profile import Attributes, PlayerProfile


class Actor(BaseModel):
    """Character representation sent to the rules server."""

    name: str
    attributes: Attributes
    skills: dict[str, int]
    tags: list[str]


def profile_to_actor(profile: PlayerProfile) -> Actor:
    return Actor(
        name=profile.name,
        attributes=profile.attributes,
        skills=profile.skills,
        tags=profile.tags,
    )
