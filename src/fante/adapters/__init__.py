"""Concrete adapters that implement port protocols.

Imported only by `fante.compose` and tests. The orchestrator core depends
on `fante.ports`, never on this package.
"""

from fante.adapters.bridge_narrator import BridgeNarrator
from fante.adapters.json_profile_store import JSONProfileStore
from fante.adapters.json_session_store import JSONSessionStore
from fante.adapters.local_dice import LocalDice
from fante.adapters.stdio_io import StdinInput, StdoutOutput

__all__ = [
    "BridgeNarrator",
    "JSONProfileStore",
    "JSONSessionStore",
    "LocalDice",
    "StdinInput",
    "StdoutOutput",
]
