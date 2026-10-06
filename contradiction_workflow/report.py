"""Generate a readable report from the authoritative machine records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .store import ProjectStore


def _payload(store: ProjectStore, record_type: str) -> dict[str, Any]:
    return store.latest_record(record_type)["payload"]


def _json_block(value: Any) -> str:
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"


def render_markdown(store: ProjectStore, title: str) -> str:
    sections = [f"# {title}", ""]
    for heading, record_type in (
        ("Preserved puzzle", "puzzle"),
        ("Literature map", "literature_map"),
        ("Locked expectation", "expectation"),
        ("Adjudicated contradiction", "contradiction"),
        ("Locked reconstruction", "reconstruction"),
        ("Prospective transfer result", "transfer"),
    ):
        sections.extend([f"## {heading}", "", _json_block(_payload(store, record_type)), ""])
    sections.extend(
        [
            "## Audit summary",
            "",
            f"Final state before export: `{store.state}`.",
            f"Recorded events: {store.event_count()}.",
            "",
        ]
    )
    return "\n".join(sections)


def write_markdown(store: ProjectStore, title: str) -> Path:
    path = store.root / "report.md"
    path.write_text(render_markdown(store, title), encoding="utf-8")
    return path

