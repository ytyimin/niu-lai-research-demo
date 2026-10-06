"""Run the complete cached demonstration from the command line."""

from __future__ import annotations

import argparse
from pathlib import Path

from .case import CaseBundle
from .model import CachedModelAdapter
from .report import write_markdown
from .store import ProjectStore
from .workflow import Workflow


PUZZLE = (
    "After the organization introduced an additional central approval requirement, "
    "regional teams resolved service disruptions faster and with more lateral coordination."
)


def run_demo(repository_root: Path, output: Path) -> ProjectStore:
    case = CaseBundle.load(repository_root / "cases" / "demo_case")
    store = ProjectStore.create(output, case.case_id)
    workflow = Workflow(
        case,
        store,
        CachedModelAdapter(repository_root / "cached_outputs"),
    )

    workflow.approve_puzzle(
        PUZZLE,
        ["E1", "E2", "E3", "E4"],
        [
            "The apparent speed increase may reflect easier incidents rather than changed coordination.",
            "The central approval may have become ceremonial rather than constraining.",
        ],
    )
    workflow.approve_literature_map(["T1", "T2"])
    workflow.lock_expectation(workflow.draft_expectation())
    workflow.adjudicate_contradiction(workflow.draft_contradiction())
    workflow.lock_reconstruction(workflow.draft_reconstruction())
    workflow.score_transfer(workflow.draft_transfer_score())
    report_path = write_markdown(store, case.manifest["title"])
    workflow.mark_exported(str(report_path.relative_to(store.root)))
    return store


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runs/demo"),
        help="New output directory; the command refuses to overwrite a prior run.",
    )
    args = parser.parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    store = run_demo(repository_root, args.output)
    print(f"Demo completed: {store.root}")
    print(f"Final state: {store.state}")
    print(f"Report: {store.root / 'report.md'}")


if __name__ == "__main__":
    main()
