"""Port protocols — abstract capabilities the orchestrator depends on.

The orchestrator imports only from this package. Concrete adapters live in
`fante.adapters` and are wired in `fante.compose`.
"""

from fante.ports.io import InputPort, OutputPort
from fante.ports.narrator import NarratorPort
from fante.ports.stores import ProfileStore

__all__ = [
    "InputPort",
    "NarratorPort",
    "OutputPort",
    "ProfileStore",
]
