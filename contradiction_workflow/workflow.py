"""The five-step workflow and its human approval points."""

from __future__ import annotations

from typing import Any

from .case import CaseBundle
from .model import ModelAdapter
from .schema import validate_record
from .store import ProjectStore, payload_hash


ALLOWED_CONTRADICTION_CLASSES = {
    "contradiction",
    "qualification",
    "compatibility",
    "unresolved",
}


class Workflow:
    def __init__(
        self,
        case: CaseBundle,
        store: ProjectStore,
        model: ModelAdapter,
    ):
        if store.project["case_id"] != case.case_id:
            raise ValueError("Project and case identifiers differ")
        self.case = case
        self.store = store
        self.model = model
        if case.manifest.get("external_model_calls_allowed") is False and not getattr(model, "offline_only", False):
            raise ValueError("This case permits offline reference replay only")
        self.schema_root = case.root.parents[1] / "schemas"

    def _record(self, record_type: str, payload: dict[str, Any], actor: str) -> dict[str, Any]:
        validate_record(self.schema_root, record_type, payload)
        return self.store.append_record(record_type, payload, actor)

    def approve_puzzle(
        self,
        observed_pattern: str,
        evidence_ids: list[str],
        rival_descriptions: list[str],
        actor: str = "researcher",
    ) -> dict[str, Any]:
        valid_ids = {item["evidence_id"] for item in self.case.evidence_items()}
        if not observed_pattern.strip():
            raise ValueError("An observable pattern is required")
        if not evidence_ids or not set(evidence_ids) <= valid_ids:
            raise ValueError("Puzzle evidence links are missing or invalid")
        payload = {
            "observed_pattern": observed_pattern.strip(),
            "evidence_ids": evidence_ids,
            "rival_descriptions": rival_descriptions,
            "unresolved_data_quality": [],
            "approved": True,
        }
        ref = self._record("puzzle", payload, actor)
        self.store.transition("case_created", "puzzle_approved", actor, ref)
        return payload

    def approve_literature_map(
        self, selected_source_ids: list[str], actor: str = "researcher"
    ) -> dict[str, Any]:
        unknown = set(selected_source_ids) - self.case.theory_sources.keys()
        if not selected_source_ids or unknown:
            raise ValueError(f"Invalid source selection: {sorted(unknown)}")
        payload = {
            "corpus_boundary": self.case.manifest.get("corpus_boundary", "Synthetic theory notes bundled with the case"),
            "selected_source_ids": selected_source_ids,
            "inclusion_reasons": {
                source_id: self.case.manifest.get("source_inclusion_reasons", {}).get(
                    source_id, "Bears directly on coordination under formal control and time pressure"
                )
                for source_id in selected_source_ids
            },
            "rejected_source_ids": [],
            "coverage_gaps": [
                "The demonstration corpus is intentionally small and not representative"
            ],
            "approved": True,
        }
        ref = self._record("literature_map", payload, actor)
        self.store.transition(
            "puzzle_approved", "literature_map_approved", actor, ref
        )
        return payload

    def draft_expectation(self) -> dict[str, Any]:
        if self.store.state != "literature_map_approved":
            raise RuntimeError("Expectation generation is not available in this state")
        literature = self.store.latest_record("literature_map")["payload"]
        packet = self.case.expectation_packet(literature["selected_source_ids"])
        expectation = self.model.run("expectation", packet)
        challenge = self.model.run("challenge", packet)
        self._validate_source_links(expectation)
        return {
            **expectation,
            "challenge": challenge,
            "selected_source_ids": literature["selected_source_ids"],
            "allowed_input_hash": payload_hash(packet),
            "allowed_input_keys": sorted(packet.keys()),
        }

    def lock_expectation(
        self, draft: dict[str, Any], actor: str = "researcher"
    ) -> dict[str, Any]:
        self._validate_source_links(draft)
        literature = self.store.latest_record("literature_map")["payload"]
        selected = literature["selected_source_ids"]
        packet = self.case.expectation_packet(selected)
        if draft.get("selected_source_ids") != selected or draft.get("allowed_input_hash") != payload_hash(packet):
            raise ValueError("Expectation inputs differ from the approved source packet")
        if draft.get("allowed_input_keys") != sorted(packet):
            raise ValueError("Expectation input keys do not match the permitted packet")
        if draft.get("strength") not in {"determinate", "qualified", "indeterminate"}:
            raise ValueError("Expectation strength is invalid")
        payload = {**draft, "locked": True}
        ref = self._record("expectation", payload, actor)
        self.store.transition(
            "literature_map_approved", "expectation_locked", actor, ref
        )
        return payload

    def draft_contradiction(self) -> dict[str, Any]:
        if self.store.state != "expectation_locked":
            raise RuntimeError("Lock the expectation before contradiction analysis")
        payload = {
            "expectation": self.store.latest_record("expectation")["payload"],
            "puzzle": self.store.latest_record("puzzle")["payload"],
            "evidence": self.case.evidence,
        }
        return self.model.run("contradiction", payload)

    def adjudicate_contradiction(
        self, draft: dict[str, Any], actor: str = "researcher"
    ) -> dict[str, Any]:
        classification = draft.get("classification")
        if classification not in ALLOWED_CONTRADICTION_CLASSES:
            raise ValueError("Contradiction classification is invalid")
        expectation_strength = self.store.latest_record("expectation")["payload"][
            "strength"
        ]
        if expectation_strength == "indeterminate" and classification == "contradiction":
            raise ValueError(
                "An indeterminate theoretical expectation cannot warrant a contradiction"
            )
        valid_ids = {item["evidence_id"] for item in self.case.evidence_items()}
        if not set(draft.get("evidence_ids", [])) <= valid_ids:
            raise ValueError("Contradiction record contains invalid evidence links")
        payload = {**draft, "human_adjudicated": True}
        ref = self._record("contradiction", payload, actor)
        self.store.transition(
            "expectation_locked", "contradiction_adjudicated", actor, ref
        )
        return payload

    def draft_reconstruction(self) -> dict[str, Any]:
        if self.store.state != "contradiction_adjudicated":
            raise RuntimeError("Adjudicate the contradiction before reconstruction")
        payload = {
            "contradiction": self.store.latest_record("contradiction")["payload"],
            "evidence": self.case.evidence,
        }
        return self.model.run("reconstruction", payload)

    def lock_reconstruction(
        self, draft: dict[str, Any], actor: str = "researcher"
    ) -> dict[str, Any]:
        predictions = draft.get("prospective_transfer_predictions", [])
        if not predictions:
            raise ValueError("At least one prospective transfer prediction is required")
        payload = {**draft, "locked": True, "held_out_opened": False}
        ref = self._record("reconstruction", payload, actor)
        self.store.transition(
            "contradiction_adjudicated", "reconstruction_locked", actor, ref
        )
        return payload

    def draft_transfer_score(self) -> dict[str, Any]:
        if self.store.state != "reconstruction_locked":
            raise RuntimeError("Lock transfer predictions before opening held-out evidence")
        if not self.case.held_out_items():
            raise RuntimeError("No independent held-out evidence is available; transfer remains not evaluated")
        payload = {
            "predictions": self.store.latest_record("reconstruction")["payload"][
                "prospective_transfer_predictions"
            ],
            "held_out_evidence": self.case.held_out_evidence,
        }
        return self.model.run("transfer", payload)

    def score_transfer(
        self, draft: dict[str, Any], actor: str = "researcher"
    ) -> dict[str, Any]:
        if self.store.state != "reconstruction_locked" or not self.case.held_out_items():
            raise RuntimeError("Transfer requires a locked reconstruction and independent evidence")
        valid_ids = {item["evidence_id"] for item in self.case.held_out_items()}
        if not set(draft.get("held_out_evidence_ids", [])) <= valid_ids:
            raise ValueError("Transfer record contains invalid held-out evidence links")
        payload = {**draft, "human_reviewed": True}
        ref = self._record("transfer", payload, actor)
        self.store.transition(
            "reconstruction_locked", "transfer_scored", actor, ref
        )
        return payload

    def mark_exported(self, report_path: str, actor: str = "researcher") -> None:
        ref = self._record("export", {"report_path": report_path}, actor)
        self.store.transition("transfer_scored", "exported", actor, ref)

    def _validate_source_links(self, value: dict[str, Any]) -> None:
        selected = self.store.latest_record("literature_map")["payload"]["selected_source_ids"]
        valid_passages = {
            p["passage_id"] for sid in selected
            for p in self.case.theory_sources[sid].get("passages", [])
        }
        linked = set(value.get("source_passage_ids", []))
        if not linked:
            raise ValueError("Expectation has no source passage links")
        if not linked <= valid_passages:
            raise ValueError(f"Unknown source passage links: {sorted(linked - valid_passages)}")
