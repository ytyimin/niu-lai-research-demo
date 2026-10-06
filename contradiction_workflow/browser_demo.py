"""Niu Lai browser exports; the scientific workflow stays unchanged."""
from __future__ import annotations
import io
import json
import zipfile
from pathlib import Path
from .store import ProjectStore

RECORD_TITLES = {
    "puzzle": "1. Preserve the puzzle",
    "literature_map": "2. Map the theoretical search space",
    "expectation": "3. Lock a qualified expectation",
    "contradiction": "4. Assess the theory–evidence relationship",
    "reconstruction": "5. Propose a mechanism and a discriminating test",
}

def write_browser_report(store: ProjectStore) -> Path:
    """Export records without inventing a transfer or export transition."""
    if store.project["case_id"] != "niu_lai_illustration":
        raise ValueError("This report is specific to the Niu Lai illustration")
    if store.state != "reconstruction_locked":
        raise ValueError("Complete the five approval steps before exporting the report")
    parts = [
        "# Niu Lai: theory–evidence reconciliation demo", "",
        "This is an authored, fixed-corpus reference walkthrough. Browser approvals "
        "record a visitor's progress; they are not independent expert validation or "
        "observations of an unaided historical research process.", "",
        "**Transfer: NOT EVALUATED.** No independent held-out evidence was supplied.", "",
        "The final reconstruction is a conjecture and proposed test. Original "
        "discovery history and practical AI benefit remain unestimated. The "
        "sequential survival review is a separate retrospective assessment.", "",
        f"Workflow state: `{store.state}`. Logged events: {store.event_count()}.", "",
    ]
    for record, title in RECORD_TITLES.items():
        payload = store.latest_record(record)["payload"]
        parts.extend([f"## {title}", "", "```json",
                      json.dumps(payload, ensure_ascii=False, indent=2), "```", ""])
    report = store.root / "illustrative_report.md"
    report.write_text("\n".join(parts), encoding="utf-8")
    status = {
        "kind": "authored_browser_walkthrough", "state": store.state,
        "transfer": "not_evaluated", "ai_benefit_estimate": None,
        "independent_expert_validation": False,
        "reason": "No independent held-out evidence or original discovery history supplied",
    }
    (store.root / "status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

def audit_archive(store: ProjectStore) -> bytes:
    """Return only this session's files, including any completed survival review."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(store.root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                archive.write(path, arcname=path.relative_to(store.root).as_posix())
    return buffer.getvalue()
