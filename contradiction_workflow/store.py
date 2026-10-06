"""Append-only records and explicit workflow state transitions."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_SEQUENCE = (
    "case_created",
    "puzzle_approved",
    "literature_map_approved",
    "expectation_locked",
    "contradiction_adjudicated",
    "reconstruction_locked",
    "transfer_scored",
    "exported",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def payload_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ProjectStore:
    """A folder-backed project store suitable for a transparent prototype."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.project_path = self.root / "project.json"
        self.events_path = self.root / "events.jsonl"
        self.records_root = self.root / "records"
        if not self.project_path.exists():
            raise FileNotFoundError(f"No project exists at {self.root}")

    @classmethod
    def create(cls, root: str | Path, case_id: str) -> "ProjectStore":
        project_root = Path(root).resolve()
        if (project_root / "project.json").exists():
            raise FileExistsError(f"Project already exists at {project_root}")
        project_root.mkdir(parents=True, exist_ok=True)
        (project_root / "records").mkdir(exist_ok=True)
        project = {
            "case_id": case_id,
            "state": "case_created",
            "created_at": utc_now(),
        }
        cls._atomic_write(project_root / "project.json", project)
        store = cls(project_root)
        store._append_event(
            {
                "event": "project_created",
                "actor": "system",
                "from_state": None,
                "to_state": "case_created",
                "record_ref": None,
            }
        )
        return store

    @staticmethod
    def _atomic_write(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            text=True,
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")

            delay_seconds = 0.05
            for attempt in range(8):
                try:
                    os.replace(temp_path, path)
                    return
                except PermissionError:
                    if attempt == 7:
                        raise
                    time.sleep(delay_seconds)
                    delay_seconds = min(delay_seconds * 2, 0.5)
        finally:
            temp_path.unlink(missing_ok=True)

    @property
    def project(self) -> dict[str, Any]:
        with self.project_path.open(encoding="utf-8") as handle:
            return json.load(handle)

    @property
    def state(self) -> str:
        return str(self.project["state"])

    def append_record(
        self, record_type: str, payload: dict[str, Any], actor: str
    ) -> dict[str, Any]:
        record_dir = self.records_root / record_type
        record_dir.mkdir(parents=True, exist_ok=True)
        versions = sorted(record_dir.glob("v*.json"))
        version = len(versions) + 1
        path = record_dir / f"v{version:04d}.json"
        if path.exists():
            raise RuntimeError(f"Refusing to overwrite {path}")
        scientific_hash = payload_hash(payload)
        record = {
            "record_type": record_type,
            "version": version,
            "created_at": utc_now(),
            "actor": actor,
            "payload_hash": scientific_hash,
            "payload": payload,
        }
        self._atomic_write(path, record)
        return {
            "record_type": record_type,
            "version": version,
            "path": str(path.relative_to(self.root)),
            "payload_hash": scientific_hash,
        }

    def latest_record(self, record_type: str) -> dict[str, Any]:
        paths = sorted((self.records_root / record_type).glob("v*.json"))
        if not paths:
            raise FileNotFoundError(f"No {record_type} record")
        with paths[-1].open(encoding="utf-8") as handle:
            return json.load(handle)

    def transition(
        self,
        expected_state: str,
        new_state: str,
        actor: str,
        record_ref: dict[str, Any],
    ) -> None:
        if self.state != expected_state:
            raise RuntimeError(
                f"Expected state {expected_state!r}; project is {self.state!r}"
            )
        expected_index = STATE_SEQUENCE.index(expected_state)
        if STATE_SEQUENCE[expected_index + 1] != new_state:
            raise RuntimeError(f"Illegal transition: {expected_state} -> {new_state}")
        project = self.project
        project["state"] = new_state
        project["updated_at"] = utc_now()
        self._atomic_write(self.project_path, project)
        self._append_event(
            {
                "event": "state_transition",
                "actor": actor,
                "from_state": expected_state,
                "to_state": new_state,
                "record_ref": record_ref,
            }
        )

    def _append_event(self, event: dict[str, Any]) -> None:
        event = {"timestamp": utc_now(), **event}
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(event) + "\n")

    def event_count(self) -> int:
        if not self.events_path.exists():
            return 0
        with self.events_path.open(encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
