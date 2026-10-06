from __future__ import annotations
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from contradiction_workflow import ProjectStore
from contradiction_workflow.browser_demo import audit_archive, write_browser_report
from contradiction_workflow.niu_lai_demo import run_illustration
from contradiction_workflow.survival_demo import run_survival_review

ROOT = Path(__file__).resolve().parents[1]

class BrowserExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def test_report_preserves_scientific_state_and_append_only_records(self):
        store = run_illustration(ROOT, self.base / "first")
        before = {p.relative_to(store.root): p.read_bytes()
                  for p in store.root.rglob("*") if p.is_file()}
        report = write_browser_report(store)
        self.assertIn("NOT EVALUATED", report.read_text(encoding="utf-8"))
        self.assertEqual(store.state, "reconstruction_locked")
        self.assertFalse((store.records_root / "transfer").exists())
        for rel, data in before.items():
            if rel.name not in ("illustrative_report.md", "status.json"):
                self.assertEqual((store.root / rel).read_bytes(), data)
        self.assertIsNone(json.loads((store.root / "status.json").read_text())["ai_benefit_estimate"])

    def test_report_requires_completed_niu_lai_run(self):
        store = ProjectStore.create(self.base / "incomplete", "niu_lai_illustration")
        with self.assertRaises(ValueError):
            write_browser_report(store)
        other = ProjectStore.create(self.base / "wrong-case", "demo_case")
        with self.assertRaises(ValueError):
            write_browser_report(other)

    def test_archive_contains_only_one_session_and_includes_its_review(self):
        first = run_illustration(ROOT, self.base / "first")
        second = ProjectStore.create(self.base / "second", "niu_lai_illustration")
        (second.root / "second-session-only.txt").write_text("other visitor")
        run_survival_review(ROOT, first.root / "survival_review")
        write_browser_report(first)
        with zipfile.ZipFile(io.BytesIO(audit_archive(first))) as archive:
            names = archive.namelist()
            self.assertIn("events.jsonl", names)
            self.assertIn("survival_review/summary.json", names)
            self.assertNotIn("second-session-only.txt", names)
            self.assertEqual(json.loads(archive.read("project.json"))["state"], "reconstruction_locked")
            self.assertFalse(any(name.startswith("/") or ".." in Path(name).parts for name in names))
        self.assertEqual(second.state, "case_created")
