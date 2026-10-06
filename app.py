"""A session-isolated Niu Lai walkthrough for the OS proposal."""
from __future__ import annotations
import json
import os
from pathlib import Path
from uuid import uuid4
import streamlit as st
from contradiction_workflow import CaseBundle, ProjectStore, Workflow
from contradiction_workflow.browser_demo import RECORD_TITLES, audit_archive, write_browser_report
from contradiction_workflow.niu_lai_demo import BoundIllustrationAdapter
from contradiction_workflow.survival_demo import run_survival_review

ROOT = Path(__file__).resolve().parent
CASE = CaseBundle.load(ROOT / "cases" / "niu_lai")
EXAMPLE = json.loads((CASE.root / "illustration.json").read_text(encoding="utf-8"))
SOURCES = json.loads((CASE.root / "source_verification.json").read_text(encoding="utf-8"))
ACTOR = "demo_visitor_approving_authored_reference"
STAGES = ["case_created", "puzzle_approved", "literature_map_approved",
          "expectation_locked", "contradiction_adjudicated", "reconstruction_locked"]
STAGE_NAMES = ["1 · Preserve the puzzle", "2 · Map the literature", "3 · Lock the expectation",
               "4 · Assess the relationship", "5 · Propose and test", "Five steps complete"]

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def change_view(view: str) -> None:
    st.session_state["demo_view"] = view

def advance() -> None:
    for key in ("expectation_draft", "contradiction_draft", "reconstruction_draft"):
        st.session_state.pop(key, None)
    st.rerun()

def bullet_list(items) -> None:
    for item in items:
        st.markdown(f"- {item}")

def evidence_cards() -> None:
    for item in CASE.evidence_items():
        with st.expander(f"{item['evidence_id']} · {item['text']}"):
            st.write(item["text"])
            st.caption(item["verification"])
            for source_id in item["source_ids"]:
                source = SOURCES["sources"][source_id]
                if source.startswith("https://"):
                    st.markdown(f"[{source_id}]({source})")
                else:
                    st.caption(f"{source_id}: {source}")

def downloads(store: ProjectStore) -> None:
    report_path = write_browser_report(store)
    left, right = st.columns(2)
    with left:
        st.download_button("Download workflow report", report_path.read_text(encoding="utf-8"),
                           file_name="Niu-Lai-workflow-report.md", mime="text/markdown",
                           key="workflow_report_download")
    with right:
        st.download_button("Download audit ZIP", audit_archive(store),
                           file_name="Niu-Lai-session-audit.zip", mime="application/zip",
                           key="audit_download")
    st.caption("Download your records before leaving. Refreshing the page starts a new session; hosted files are temporary.")

def workflow_view(store: ProjectStore, flow: Workflow) -> None:
    stage = store.state
    if stage == "case_created":
        st.header("Step 1 · Preserve the puzzle")
        st.write("How can unfavorable evaluations coexist with ticket purchasing and public participation? Start with the reported pattern, keeping possible explanations open.")
        st.subheader("Observations in the supplied case packet")
        evidence_cards()
        st.subheader("Descriptive puzzle")
        st.write(EXAMPLE["observed_pattern"])
        st.subheader("Rival descriptions to keep open")
        bullet_list(EXAMPLE["rival_descriptions"])
        if st.button("Approve puzzle", type="primary"):
            flow.approve_puzzle(EXAMPLE["observed_pattern"], EXAMPLE["evidence_ids"], EXAMPLE["rival_descriptions"], ACTOR)
            advance()
    elif stage == "puzzle_approved":
        st.header("Step 2 · Map the theoretical search space")
        st.write("The retained theory note distinguishes awareness from evaluation.")
        for source_id in EXAMPLE["selected_source_ids"]:
            source = CASE.theory_sources[source_id]
            st.subheader(source["title"])
            st.caption(source["citation"])
            st.markdown(f"[Read the linked source]({source['url']})")
            for passage in source["passages"]:
                st.markdown(f"**{passage['passage_id']}** — {passage['text']}")
                st.caption(passage["locator"])
        st.subheader("Other directions for a future search")
        st.table(EXAMPLE["candidate_lenses"])
        st.info("This is one curated source and a set of candidate lenses. Independent source discovery and exhaustive literature coverage are not demonstrated.")
        if st.button("Approve literature map", type="primary"):
            flow.approve_literature_map(EXAMPLE["selected_source_ids"], ACTOR)
            advance()
    elif stage == "literature_map_approved":
        st.header("Step 3 · Construct and lock a qualified expectation")
        st.write("Only the neutral context and selected theory note reach the expectation adapter. The descriptive puzzle, focal observations, and survival review are excluded from that input.")
        with st.expander("Inspect the permitted expectation input"):
            st.json(CASE.expectation_packet(EXAMPLE["selected_source_ids"]))
        if st.button("Load reference expectation"):
            st.session_state["expectation_draft"] = flow.draft_expectation()
        draft = st.session_state.get("expectation_draft")
        if draft:
            st.subheader("Qualified expectation")
            st.write(draft["integrated_expectation"])
            for expectation in draft["expectations"]:
                st.markdown("**Assumptions**")
                bullet_list(expectation["assumptions"])
                st.markdown("**Boundary conditions**")
                bullet_list(expectation["boundary_conditions"])
            st.subheader("Challenge the expectation")
            st.write(draft["challenge"]["strongest_objection"])
            st.write(draft["challenge"]["scope_problem"])
            st.info(draft["challenge"]["recommended_resolution"])
            with st.expander("Full expectation and provenance record"):
                st.json(draft)
            if st.button("Approve and lock expectation", type="primary"):
                flow.lock_expectation(draft, ACTOR)
                advance()
    elif stage == "expectation_locked":
        st.header("Step 4 · Assess the theory–evidence relationship")
        left, right = st.columns(2)
        with left:
            st.subheader("Locked expectation")
            st.write(store.latest_record("expectation")["payload"]["integrated_expectation"])
        with right:
            st.subheader("Reported pattern")
            st.write(EXAMPLE["observed_pattern"])
        if st.button("Load relationship assessment"):
            st.session_state["contradiction_draft"] = flow.draft_contradiction()
        draft = st.session_state.get("contradiction_draft")
        if draft:
            st.subheader("Reference judgment: compatibility")
            st.write(draft["adjudication_reason"])
            st.markdown("**Strongest compatible account**")
            st.write(draft["strongest_non_contradictory_reading"])
            st.caption(draft["confidence"])
            with st.expander("Full relationship assessment"):
                st.json(draft)
            if st.button("Approve compatibility assessment", type="primary"):
                flow.adjudicate_contradiction(draft, ACTOR)
                advance()
    elif stage == "contradiction_adjudicated":
        st.header("Step 5 · Propose a mechanism and a discriminating test")
        st.write("The unresolved question is whether shared participation itself contributes value, beyond awareness, curiosity, and access.")
        if st.button("Load candidate reconstruction"):
            st.session_state["reconstruction_draft"] = flow.draft_reconstruction()
        draft = st.session_state.get("reconstruction_draft")
        if draft:
            st.subheader("Candidate mechanism")
            st.write(draft["selected_mechanism"])
            st.caption(draft["explanatory_gain"])
            left, right = st.columns(2)
            with left:
                st.markdown("**Rival accounts**")
                bullet_list(draft["rival_accounts"])
            with right:
                st.markdown("**Observations that would count against it**")
                bullet_list(draft["observations_against"])
            st.subheader("Commitments for a future comparison")
            for prediction in draft["prospective_transfer_predictions"]:
                st.markdown(f"**{prediction['prediction_id']}** — {prediction['claim']}")
            with st.expander("Full reconstruction, including unresolved questions"):
                st.json(draft)
            if st.button("Lock reconstruction and proposed tests", type="primary"):
                flow.lock_reconstruction(draft, ACTOR)
                advance()
    elif stage == "reconstruction_locked":
        st.header("Five-step walkthrough complete")
        st.success("A qualified expectation, compatibility assessment, and candidate reconstruction are now recorded.")
        st.warning("Transfer is NOT EVALUATED. The supplied case has no independent held-out evidence. The reconstruction remains a conjecture and proposed test.")
        st.write("Next, inspect whether the qualified outcomes can be derived after withdrawing the five candidate AI contributions.")
        st.button("Open survival review", type="primary", on_click=change_view, args=("Survival review",))
        downloads(store)

def survival_view(store: ProjectStore) -> None:
    st.header("Sequential outcome survival review")
    st.write("Withdraw candidate AI contributions A1–A5 and their old dependent records. Retain the supplied case evidence and curated theory note, then trace replacement derivations through the five qualified outcomes.")
    if store.state != "reconstruction_locked":
        st.info("Complete the five-step walkthrough first, then run the separate retrospective review.")
        st.button("Return to guided workflow", on_click=change_view, args=("Guided workflow",))
        return
    output = store.root / "survival_review"
    summary_path = output / "summary.json"
    if not summary_path.exists():
        st.caption("This runs the supplied authored assessment through the prototype's validation and summary code. It makes no model calls.")
        if st.button("Run authored survival review", type="primary"):
            run_survival_review(ROOT, output)
            st.rerun()
        return
    result = read_json(summary_path)
    branch = result["removals"]["without_recorded_AI"]
    left, right = st.columns(2)
    with left:
        st.metric("Qualified outcomes recovered in authored review", f"{len(branch['surviving_equivalent_claim_ids'])} / {branch['registered_claims']}")
    with right:
        assessed = sum(value["entered_assessments"] > 0 for value in result["removals"].values())
        st.metric("Removal scenarios with assessments", f"{assessed} / {len(result['removals'])}")
    st.warning("These are authored methodological judgments under a fixed corpus. They do not establish independent discovery, a causal mechanism, or an amount of practical AI benefit.")
    st.caption("The joint removal of A1–A5 is assessed. The other removal scenarios remain unassessed.")
    st.subheader("Replacement derivations")
    st.table([{
        "Step": row["step"], "Outcome": row["claim_id"], "Replacement": row["derivation_id"],
        "Earlier replacements used": ", ".join(row["upstream_derivation_ids"]) or "Direct retained premises",
        "Judgment": "Recovered at the qualified scope" if row["status"] == "recovered_equivalent" else row["status"],
    } for row in branch["step_progression"]])
    for assessment in result["assessments"]:
        with st.expander(f"{assessment['claim_id']} · {assessment['replacement_outcome']}"):
            st.markdown("**Alternative derivation**")
            st.write(assessment["derivation"])
            st.markdown("**Scope of the judgment**")
            st.write(assessment["reason"])
            st.caption("Evidence: " + "; ".join(assessment["evidence_refs"]))
            if assessment.get("upstream_outcomes_used"):
                st.markdown("**Earlier outcomes used, at their stated scope**")
                st.json(assessment["upstream_outcomes_used"])
    with st.expander("All removal scenarios and the complete report"):
        st.markdown((output / "report.md").read_text(encoding="utf-8"))
    st.download_button("Download survival review", (output / "report.md").read_text(encoding="utf-8"),
                       file_name="Niu-Lai-survival-review.md", mime="text/markdown")
    downloads(store)

def audit_view(store: ProjectStore) -> None:
    st.header("Sources and audit records")
    st.write(CASE.manifest["provenance"])
    st.caption(CASE.manifest["license"])
    st.caption(f"The supplied source-verification ledger is dated {SOURCES['checked_on']}; this demo does not recheck live sources.")
    evidence_cards()
    with st.expander("Source-verification ledger"):
        st.json(SOURCES)
    with st.expander("Case manifest"):
        st.json(CASE.manifest)
    with st.expander("Reference-output provenance"):
        st.json(read_json(CASE.root / "reference_outputs" / "provenance.json"))
    st.subheader("Approved records in this session")
    for record, title in RECORD_TITLES.items():
        if (store.records_root / record).exists():
            with st.expander(title):
                st.json(store.latest_record(record))
    with st.expander(f"Audit events · {store.event_count()} recorded"):
        st.code(store.events_path.read_text(encoding="utf-8"), language="json")
    if store.state == "reconstruction_locked":
        downloads(store)
    else:
        st.download_button("Download current audit ZIP", audit_archive(store),
                           file_name="Niu-Lai-session-audit.zip", mime="application/zip")

st.set_page_config(page_title="Niu Lai · Theory–Evidence Reconciliation", layout="wide")
if st.sidebar.button("Start a new demo"):
    st.session_state.clear()
    st.rerun()
if "demo_run_id" not in st.session_state:
    st.session_state["demo_run_id"] = uuid4().hex
run_parent = Path(os.getenv("CONTRADICTION_RUN_DIR", str(ROOT / "runs" / "browser")))
run_dir = run_parent / st.session_state["demo_run_id"]
store = ProjectStore(run_dir) if (run_dir / "project.json").exists() else ProjectStore.create(run_dir, CASE.case_id)
flow = Workflow(CASE, store, BoundIllustrationAdapter(CASE.root / "reference_outputs"))
st.sidebar.title("Niu Lai case")
step = STAGES.index(store.state)
st.sidebar.progress(step / 5)
st.sidebar.write(STAGE_NAMES[step])
view = st.sidebar.radio("Explore", ["Guided workflow", "Survival review", "Sources & audit"], key="demo_view")
st.sidebar.caption("Each browser session has its own run. Starting a new demo preserves the old run's records on the current host.")
st.title("Niu Lai: from puzzle to proposed test")
st.caption("Theory–evidence reconciliation · An authored case walkthrough for the OS proposal")
st.info("Reference replay · The supplied outputs and judgments are fixed. Buttons record your review progress; no live AI model is called and no API key is needed.")
if view == "Guided workflow":
    workflow_view(store, flow)
elif view == "Survival review":
    survival_view(store)
else:
    audit_view(store)
