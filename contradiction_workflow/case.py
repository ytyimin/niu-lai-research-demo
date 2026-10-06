"""Load a shareable qualitative case packet and enforce the Step 3 boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


@dataclass(frozen=True)
class CaseBundle:
    """Files for one reproducible demonstration case."""

    root: Path
    manifest: dict[str, Any]
    neutral_context: dict[str, Any]
    evidence: dict[str, Any]
    held_out_evidence: dict[str, Any]
    theory_sources: dict[str, dict[str, Any]]

    @classmethod
    def load(cls, root: str | Path) -> "CaseBundle":
        case_root = Path(root).resolve()
        theory_root = case_root / "theory_sources"
        sources: dict[str, dict[str, Any]] = {}
        for path in sorted(theory_root.glob("*.json")):
            source = _read_json(path)
            source_id = source.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                raise ValueError(f"Theory source lacks source_id: {path}")
            if source_id in sources:
                raise ValueError(f"Duplicate theory source id: {source_id}")
            sources[source_id] = source

        bundle = cls(
            root=case_root,
            manifest=_read_json(case_root / "manifest.json"),
            neutral_context=_read_json(case_root / "neutral_context.json"),
            evidence=_read_json(case_root / "evidence.json"),
            held_out_evidence=_read_json(case_root / "held_out_evidence.json"),
            theory_sources=sources,
        )
        bundle._validate()
        return bundle

    @property
    def case_id(self) -> str:
        return str(self.manifest["case_id"])

    def _validate(self) -> None:
        required_manifest = {
            "case_id",
            "title",
            "version",
            "provenance",
            "license",
            "sensitivity",
        }
        missing = required_manifest - self.manifest.keys()
        if missing:
            raise ValueError(f"Manifest missing fields: {sorted(missing)}")
        if self.manifest["sensitivity"] not in {"public_synthetic", "public_source_illustration"}:
            raise ValueError("Only declared synthetic or public-source illustrative cases are supported")
        if self.manifest["sensitivity"] == "public_source_illustration":
            if self.manifest.get("license") == "CC0-1.0":
                raise ValueError("Do not relabel third-party source material as CC0")
            if not self.manifest.get("expectation_alias"):
                raise ValueError("Public illustrative cases require a neutral expectation alias")
        if not self.theory_sources:
            raise ValueError("At least one theory source is required")

    def evidence_items(self) -> list[dict[str, Any]]:
        items = self.evidence.get("items", [])
        if not isinstance(items, list):
            raise ValueError("evidence.items must be a list")
        return items

    def held_out_items(self) -> list[dict[str, Any]]:
        items = self.held_out_evidence.get("items", [])
        if not isinstance(items, list):
            raise ValueError("held_out_evidence.items must be a list")
        return items

    def expectation_packet(self, selected_source_ids: list[str]) -> dict[str, Any]:
        """Return the only payload permitted to reach the expectation model.

        Evidence, puzzle records, focal outcomes, and held-out materials are
        deliberately absent. The model adapter receives this returned object,
        not the CaseBundle.
        """

        if not selected_source_ids:
            raise ValueError("Select at least one theory source")
        missing = sorted(set(selected_source_ids) - self.theory_sources.keys())
        if missing:
            raise ValueError(f"Unknown theory sources: {missing}")
        return {
            "case_id": self.manifest.get("expectation_alias", self.case_id),
            "neutral_context": self.neutral_context,
            "theory_sources": [
                self.theory_sources[source_id] for source_id in selected_source_ids
            ],
        }

    def source_passage_ids(self) -> set[str]:
        passage_ids: set[str] = set()
        for source in self.theory_sources.values():
            for passage in source.get("passages", []):
                passage_id = passage.get("passage_id")
                if isinstance(passage_id, str):
                    passage_ids.add(passage_id)
        return passage_ids
