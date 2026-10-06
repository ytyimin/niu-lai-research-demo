from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from contradiction_workflow import CachedModelAdapter, CaseBundle, ProjectStore, Workflow
from contradiction_workflow.demo import PUZZLE, run_demo


ROOT = Path(__file__).resolve().parents[1]


class SpyAdapter:
    def __init__(self) -> None:
        self.delegate = CachedModelAdapter(ROOT / "cached_outputs")
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def run(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((task, copy.deepcopy(payload)))
        return self.delegate.run(task, payload)


class WorkflowAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.case = CaseBundle.load(ROOT / "cases" / "demo_case")
        self.store = ProjectStore.create(Path(self.temp.name) / "run", self.case.case_id)
        self.spy = SpyAdapter()
        self.workflow = Workflow(self.case, self.store, self.spy)

    def approve_first_two_steps(self) -> None:
        self.workflow.approve_puzzle(
            PUZZLE,
            ["E1", "E2", "E3", "E4"],
            ["Incident difficulty may have changed."],
        )
        self.workflow.approve_literature_map(["T1", "T2"])

    def test_step3_model_receives_only_allowlisted_inputs(self) -> None:
        self.approve_first_two_steps()
        self.workflow.draft_expectation()
        self.assertEqual([call[0] for call in self.spy.calls], ["expectation", "challenge"])
        for _, payload in self.spy.calls:
            self.assertEqual(
                set(payload), {"case_id", "neutral_context", "theory_sources"}
            )
            serialized = json.dumps(payload).lower()
            for forbidden in (
                "evidence_id",
                "observed_pattern",
                "held_out_evidence",
                "resolution time fell",
            ):
                self.assertNotIn(forbidden, serialized)

    def test_unlocked_expectation_cannot_enter_contradiction_analysis(self) -> None:
        self.approve_first_two_steps()
        with self.assertRaises(RuntimeError):
            self.workflow.draft_contradiction()
        self.assertEqual(self.store.state, "literature_map_approved")

    def test_broken_source_link_is_rejected(self) -> None:
        self.approve_first_two_steps()
        draft = self.workflow.draft_expectation()
        draft["source_passage_ids"].append("NOT-A-PASSAGE")
        with self.assertRaises(ValueError):
            self.workflow.lock_expectation(draft)
        self.assertEqual(self.store.state, "literature_map_approved")

    def test_record_versions_are_append_only(self) -> None:
        first = self.store.append_record("diagnostic", {"value": 1}, "tester")
        first_path = self.store.root / first["path"]
        original = first_path.read_text(encoding="utf-8")
        second = self.store.append_record("diagnostic", {"value": 2}, "tester")
        self.assertNotEqual(first["path"], second["path"])
        self.assertEqual(first_path.read_text(encoding="utf-8"), original)

    def test_held_out_packet_cannot_be_scored_early(self) -> None:
        with self.assertRaises(RuntimeError):
            self.workflow.draft_transfer_score()

    def test_indeterminate_expectation_cannot_warrant_contradiction(self) -> None:
        self.approve_first_two_steps()
        expectation = self.workflow.draft_expectation()
        expectation["strength"] = "indeterminate"
        self.workflow.lock_expectation(expectation)
        contradiction = self.workflow.draft_contradiction()
        contradiction["classification"] = "contradiction"
        with self.assertRaises(ValueError):
            self.workflow.adjudicate_contradiction(contradiction)
        self.assertEqual(self.store.state, "expectation_locked")

    def test_public_case_contains_only_declared_shareable_material(self) -> None:
        self.assertEqual(self.case.manifest["sensitivity"], "public_synthetic")
        self.assertEqual(self.case.manifest["license"], "CC0-1.0")
        case_files = [path for path in self.case.root.rglob("*") if path.is_file()]
        self.assertTrue(case_files)
        self.assertTrue(all(path.suffix == ".json" for path in case_files))

    def test_cached_demo_reaches_export_and_report_matches_records(self) -> None:
        other_output = Path(self.temp.name) / "complete"
        complete = run_demo(ROOT, other_output)
        self.assertEqual(complete.state, "exported")
        self.assertEqual(complete.event_count(), 8)
        report = (complete.root / "report.md").read_text(encoding="utf-8")
        expectation = complete.latest_record("expectation")["payload"]
        reconstruction = complete.latest_record("reconstruction")["payload"]
        self.assertIn(expectation["integrated_expectation"], report)
        self.assertIn(reconstruction["selected_mechanism"], report)
        self.assertTrue(complete.latest_record("expectation")["payload"]["locked"])


if __name__ == "__main__":
    unittest.main()
