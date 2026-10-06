"""Model adapters. Cached replay is the reproducible default."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Protocol


class ModelAdapter(Protocol):
    def run(self, task: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class CachedModelAdapter:
    """Replay reviewed outputs without credentials or network access."""
    offline_only = True

    def __init__(self, cache_root: str | Path):
        self.cache_root = Path(cache_root).resolve()

    def run(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        del payload  # The cached result is intentionally deterministic.
        path = self.cache_root / f"{task}.json"
        if not path.exists():
            raise FileNotFoundError(f"No cached output for task {task!r}")
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError(f"Cached output must be an object: {path}")
        return value


class OllamaAdapter:
    """Optional local-model adapter using Ollama's HTTP API."""
    offline_only = False

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self.base_url = base_url or os.getenv(
            "OLLAMA_URL", "http://127.0.0.1:11434/api/generate"
        )

    def run(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Return one valid JSON object only. "
            f"Task: {task}. Inputs: {json.dumps(payload, ensure_ascii=False)}"
        )
        body = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False, "format": "json"}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.base_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            outer = json.load(response)
        result = json.loads(outer["response"])
        if not isinstance(result, dict):
            raise ValueError("The model did not return a JSON object")
        return result
