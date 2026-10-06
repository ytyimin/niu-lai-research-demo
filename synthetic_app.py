"""Browser interface for the theory–evidence reconciliation workflow prototype."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from contradiction_workflow import CachedModelAdapter, CaseBundle, ProjectStore, Workflow
from contradiction_workflow.report import write_markdown


ROOT = Path(__file__).resolve().parent
CASE = CaseBundle.load(ROOT / "cases" / "demo_case")
RUN_DIR = Path(os.getenv("CONTRADICTION_RUN_DIR", ROOT / "runs" / "browser"))


def get_store() -> ProjectStore:
    if not (RUN_DIR / "project.json").exists():
        return ProjectStore.create(RUN_DIR, CASE.case_id)
    return ProjectStore(RUN_DIR)


def get_workflow() -> Workflow:
    return Workflow(
        CASE,
        get_store(),
        CachedModelAdapter(ROOT / "cached_outputs"),
    )


def advance_notice() -> None:
    st.success("Record approved and state advanced.")
    st.rerun()


st.set_page_config(page_title="Theory–Evidence Reconciliation AI Workflow", layout="wide")
st.title("Theory–Evidence Reconciliation AI Workflow")
st.caption(
    "A small, auditable demonstration of expectation locking, contradiction adjudication, "
    "and prospective transfer testing."
)

store = get_store()
workflow = get_workflow()
st.sidebar.subheader("Demonstration status")
st.sidebar.code(store.state)
st.sidebar.write(f"Run directory: `{RUN_DIR}`")
st.sidebar.write("Model: cached reviewed outputs")

if store.state == "case_created":
    st.header("Step 1 · Preserve the puzzle")
    st.write(
        "The evidence below is synthetic. Describe the pattern before attaching a theoretical explanation."
    )
    for item in CASE.evidence_items():
        st.markdown(f"**{item['evidence_id']} — {item['source_type']}**")
        st.write(item["text"])
    observed = st.text_area(
        "Low-inference observed pattern",
        value=(
            "After the organization introduced an additional central approval requirement, "
            "regional teams resolved service disruptions faster and with more lateral coordination."
        ),
        height=100,
    )
    rivals = st.text_area(
        "Rival descriptions, one per line",
        value=(
            "The incidents may simply have become easier.\n"
            "The central approval may have become ceremonial rather than constraining."
        ),
        height=90,
    )
    if st.button("Approve puzzle", type="primary"):
        workflow.approve_puzzle(
            observed,
            [item["evidence_id"] for item in CASE.evidence_items()],
            [line.strip() for line in rivals.splitlines() if line.strip()],
        )
        advance_notice()

elif store.state == "puzzle_approved":
    st.header("Step 2 · Map the theoretical search space")
    st.write(
        "This prototype uses a deliberately small synthetic corpus. The production artifact would record real searches, exclusions, and gaps."
    )
    options = list(CASE.theory_sources)
    selected = st.multiselect(
        "Theory sources",
        options=options,
        default=options,
        format_func=lambda source_id: f"{source_id}: {CASE.theory_sources[source_id]['title']}",
    )
    for source_id in selected:
        source = CASE.theory_sources[source_id]
        with st.expander(source["title"]):
            for passage in source["passages"]:
                st.markdown(f"**{passage['passage_id']}** — {passage['text']}")
    if st.button("Approve literature map", type="primary"):
        workflow.approve_literature_map(selected)
        advance_notice()

elif store.state == "literature_map_approved":
    st.header("Step 3 · Generate and lock theoretical expectations")
    st.info(
        "The expectation adapter receives only the neutral context and selected theory sources. "
        "The puzzle, focal evidence, and held-out evidence are not passed to it."
    )
    st.subheader("Neutral context available to the model")
    st.json(CASE.neutral_context)
    if st.button("Generate expectation and challenge"):
        st.session_state["expectation_draft"] = workflow.draft_expectation()
    draft = st.session_state.get("expectation_draft")
    if draft:
        st.subheader("Draft expectation ledger")
        st.json(draft)
        if st.button("Approve and lock expectation", type="primary"):
            workflow.lock_expectation(draft)
            st.session_state.pop("expectation_draft", None)
            advance_notice()

elif store.state == "expectation_locked":
    st.header("Step 4 · Establish the contradiction")
    left, right = st.columns(2)
    with left:
        st.subheader("Locked expectation")
        st.json(store.latest_record("expectation")["payload"])
    with right:
        st.subheader("Observed evidence")
        st.json(CASE.evidence)
    if st.button("Compare expectation and evidence"):
        st.session_state["contradiction_draft"] = workflow.draft_contradiction()
    draft = st.session_state.get("contradiction_draft")
    if draft:
        st.subheader("Draft contradiction record")
        classification = st.selectbox(
            "Human classification",
            ["contradiction", "qualification", "compatibility", "unresolved"],
            index=["contradiction", "qualification", "compatibility", "unresolved"].index(
                draft["classification"]
            ),
        )
        draft = {**draft, "classification": classification}
        st.json(draft)
        if st.button("Adjudicate relationship", type="primary"):
            workflow.adjudicate_contradiction(draft)
            st.session_state.pop("contradiction_draft", None)
            advance_notice()

elif store.state == "contradiction_adjudicated":
    st.header("Step 5 · Reconstruct and commit transfer predictions")
    st.json(store.latest_record("contradiction")["payload"])
    if st.button("Generate reconstruction"):
        st.session_state["reconstruction_draft"] = workflow.draft_reconstruction()
    draft = st.session_state.get("reconstruction_draft")
    if draft:
        st.subheader("Candidate reconstruction and prospective commitments")
        st.json(draft)
        if st.button("Lock reconstruction and predictions", type="primary"):
            workflow.lock_reconstruction(draft)
            st.session_state.pop("reconstruction_draft", None)
            advance_notice()

elif store.state == "reconstruction_locked":
    st.header("Step 5 · Open held-out evidence and score transfer")
    st.warning("The prospective predictions are locked. The held-out packet is now visible.")
    st.subheader("Locked predictions")
    st.json(
        store.latest_record("reconstruction")["payload"][
            "prospective_transfer_predictions"
        ]
    )
    st.subheader("Held-out evidence")
    st.json(CASE.held_out_evidence)
    if st.button("Compare predictions with held-out evidence"):
        st.session_state["transfer_draft"] = workflow.draft_transfer_score()
    draft = st.session_state.get("transfer_draft")
    if draft:
        st.json(draft)
        if st.button("Approve transfer score", type="primary"):
            workflow.score_transfer(draft)
            st.session_state.pop("transfer_draft", None)
            advance_notice()

elif store.state == "transfer_scored":
    st.header("Export the audit trail")
    st.write(
        "The readable report is generated from the versioned machine records rather than maintained separately."
    )
    if st.button("Generate report and finish", type="primary"):
        report_path = write_markdown(store, CASE.manifest["title"])
        workflow.mark_exported(str(report_path.relative_to(store.root)))
        advance_notice()

elif store.state == "exported":
    st.header("Demonstration complete")
    report_path = store.root / "report.md"
    st.success(f"The project reached `{store.state}` with {store.event_count()} logged events.")
    st.download_button(
        "Download readable report",
        data=report_path.read_text(encoding="utf-8"),
        file_name="contradiction_workflow_report.md",
        mime="text/markdown",
    )
    st.markdown(report_path.read_text(encoding="utf-8"))
