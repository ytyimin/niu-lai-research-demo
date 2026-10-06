"""Real Streamlit AppTest checks; skipped only when the optional UI is absent."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
try:
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError as exc:
    if exc.name != "streamlit":
        raise
    AppTest = None

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipIf(AppTest is None, "Install requirements.txt to run Streamlit interface checks")
class StreamlitDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        env = patch.dict("os.environ", {"CONTRADICTION_RUN_DIR": str(self.base)})
        env.start()
        self.addCleanup(env.stop)

    def start(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
        self.assertEqual(len(app.exception), 0)
        return app

    def click(self, app, label):
        next(button for button in app.button if button.label == label).click().run()
        self.assertEqual(len(app.exception), 0)

    def project(self, app):
        return json.loads((self.base / app.session_state["demo_run_id"] / "project.json").read_text())

    def test_full_walkthrough_survival_review_and_audit(self):
        app = self.start()
        app.sidebar.radio[0].set_value("Survival review").run()
        self.assertEqual(len(app.exception), 0)
        self.assertFalse(any(button.label == "Run authored survival review" for button in app.button))
        self.click(app, "Return to guided workflow")
        for label in (
            "Approve puzzle", "Approve literature map", "Load reference expectation",
            "Approve and lock expectation", "Load relationship assessment",
            "Approve compatibility assessment", "Load candidate reconstruction",
            "Lock reconstruction and proposed tests",
        ):
            self.click(app, label)
        run = self.base / app.session_state["demo_run_id"]
        self.assertEqual(self.project(app)["state"], "reconstruction_locked")
        self.assertTrue(any("NOT EVALUATED" in item.value for item in app.warning))
        self.assertIn("NOT EVALUATED", (run / "illustrative_report.md").read_text())
        self.click(app, "Open survival review")
        self.click(app, "Run authored survival review")
        summary = json.loads((run / "survival_review" / "summary.json").read_text())
        self.assertEqual(len(summary["removals"]["without_recorded_AI"]["surviving_equivalent_claim_ids"]), 5)
        self.assertEqual([m.value for m in app.metric], ["5 / 5", "1 / 11"])
        app.sidebar.radio[0].set_value("Sources & audit").run()
        self.assertEqual(len(app.exception), 0)
        self.assertFalse((run / "records" / "transfer").exists())

    def test_sessions_and_restart_do_not_share_or_delete_records(self):
        first = self.start()
        first_id = first.session_state["demo_run_id"]
        self.click(first, "Approve puzzle")
        before = (self.base / first_id / "events.jsonl").read_bytes()
        second = self.start()
        self.assertNotEqual(first_id, second.session_state["demo_run_id"])
        self.assertEqual(self.project(second)["state"], "case_created")
        self.click(first, "Start a new demo")
        self.assertNotEqual(first_id, first.session_state["demo_run_id"])
        self.assertEqual(self.project(first)["state"], "case_created")
        self.assertEqual((self.base / first_id / "events.jsonl").read_bytes(), before)
