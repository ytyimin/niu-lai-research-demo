"""Theory–evidence reconciliation workflow prototype."""

from .case import CaseBundle
from .model import CachedModelAdapter, OllamaAdapter
from .store import ProjectStore
from .workflow import Workflow

__all__ = [
    "CachedModelAdapter",
    "CaseBundle",
    "OllamaAdapter",
    "ProjectStore",
    "Workflow",
]

__version__ = "0.4.0"
