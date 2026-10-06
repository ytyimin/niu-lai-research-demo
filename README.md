# Niu Lai: Theory–Evidence Reconciliation Demo

**The default browser demo uses the Niu Lai case.** It walks reviewers through
five approval steps, the authored sequential survival review, and downloadable
audit records. It uses the supplied fixed reference outputs and requires no API
key. Each browser session has its own run.

- [Deploy from GitHub to Streamlit Community Cloud](DEPLOY_GITHUB.md)
- [Five-minute reviewer walkthrough](DEMO_WALKTHROUGH.md)
- [Browser adaptation and validation status](BROWSER_VALIDATION.txt)

Live demo: add your deployed Streamlit URL here after deployment.

This is a browser adaptation of prototype software version 0.4.0. The supplied
case data, scientific workflow, reference fixtures, and survival judgments are
unchanged. The final Niu Lai reconstruction remains a conjecture and proposed
test; transfer is not evaluated.

This repository is a minimal, runnable proof of concept for a human-directed qualitative theorizing workflow. Its purpose is not to automate interpretation. It demonstrates whether software can preserve an empirical puzzle, generate a source-grounded theoretical expectation behind an information boundary, lock that expectation before contradiction analysis, and retain a reviewable trail of human and model decisions.

The repository accompanies the proposal *An AI-Enabled Abductive Theorizing Loop for Qualitative Research: From Empirical Puzzles to Theoretical Reconstruction*. It is intentionally small enough for reviewers to inspect. Version 0.4.0 adds a sequential outcome-survival backtest adapted from Liang and Lu (2026), Creative Ownership in the Age of AI. It tests whether a supported outcome can be derived after removing AI contributions and follows replacement derivations through all five steps. A missing original process history limits discovery attribution but does not block retrospective survival assessment.

## Quickest reproducible run

The cached reference workflow uses only the Python standard library and makes no network or model calls.

```bash
python -m contradiction_workflow.demo --output runs/my-first-run
```

The command refuses to overwrite a prior run. On completion, open `runs/my-first-run/report.md`. The same folder contains versioned JSON records and an append-only `events.jsonl` audit history.

Run the acceptance tests with:

```bash
python -m unittest discover -s tests -v
```

## Niu Lai illustration and backtest

Run the authored example through reconstruction locking:

```bash
python -m contradiction_workflow.niu_lai_demo --output runs/niu-lai
```

Open `runs/niu-lai/illustrative_report.md`. Each step illustrates one point: preserve the descriptive pattern, find a relevant theoretical qualification, lock a qualified expectation, decline an unwarranted contradiction, and specify a candidate mechanism with a discriminating test. The attachment already describes participation and is not evidence that AI discovered it. The run stops at `reconstruction_locked`; transfer is **not evaluated** because no independent held-out observations were supplied.

Run the authored retrospective survival review:

```bash
python -m contradiction_workflow.survival_demo --output runs/niu-lai-survival
```

Open `runs/niu-lai-survival/report.md`. The review withdraws all five candidate AI contributions and supplies an alternative derivation for each qualified outcome. Later outcomes refer to the supported replacements from earlier steps. The retained corpus includes the supplied case note and the verified theory note; the review does not establish independent discovery of that source by the original researcher. Step 5 survives as a conjecture and proposed test.

The evaluator may know the target outcome. Independence concerns whether the argument follows from retained premises without relying on the removed contribution. The full target cannot be used as a premise for itself. Historical discovery, substantive quality, and conditional survival remain separate.

Prepare a new specification and empty assessment form:

```bash
python -m contradiction_workflow.backtest plan --case cases/niu_lai --output runs/niu-lai-plan
python -m contradiction_workflow.backtest summarize --plan runs/niu-lai-plan/plan.json --assessments runs/niu-lai-plan/assessments_template.json --output runs/niu-lai-unassessed
```

The planner defines eleven individual, joint, and cumulative removals and excludes old descendants. It does not assume that a missing graph route means the outcome is lost. New retrospective derivations can establish replacement routes. The summary validates step order, branch membership, retained premises, and the exact upstream scope used. Empty forms remain unestimated.

See `evaluation/backtest_protocol.md`. `examples/sequential_survival/` contains the authored review and its traceable report; `examples/unassessed/` shows the empty-form result. Neither is an observation of an unaided historical research process. The complete review record is not an admissible Step 3 generation packet.

## Browser demonstration

The default `app.py` now presents the Niu Lai case and its sequential survival
review. Create an environment, install Streamlit, and launch it:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows Command Prompt, activate with `.venv\Scripts\activate.bat`.
The deployment guide includes browser-only GitHub upload instructions.

The three views are **Guided workflow**, **Survival review**, and **Sources &
audit**. Finish the five approval steps before running the separate survival
review. The interface retains the reference judgment of compatibility and
stops the scientific workflow at `reconstruction_locked`. It never invents
held-out evidence or a transfer score.

Each session uses `runs/browser/<session-id>/`. Set `CONTRADICTION_RUN_DIR` to
change the parent directory. **Start a new demo** creates a fresh run and clears
only the visitor's current interface state; prior run records are not deleted.
A page refresh creates a fresh session. Download records before leaving because
hosted files are temporary. The original single-user synthetic interface is
preserved separately as `synthetic_app.py` for local reference use.

The interface intentionally keeps the supplied scientific inputs and judgments
fixed. Its bound adapter rejects changed inputs rather than replaying an
unmatched cached result. Source and audit views expose the supplied provenance
and source-verification limits; live sources are not rechecked by the app.

## What the prototype demonstrates

The workflow begins with a researcher-approved puzzle record and a small literature map. During Step 3, `CaseBundle.expectation_packet()` returns only the neutral context and selected theory sources. The expectation adapter never receives the puzzle record, focal evidence, observed result, or held-out transfer packet. The allowed packet is hashed and recorded with the locked expectation.

After a researcher approves the expectation and its challenge pass, the state machine permits the focal evidence to enter contradiction analysis. The researcher—not the model—classifies the relationship as contradiction, qualification, compatibility, or unresolved. Reconstruction begins only after that decision. Transfer predictions are then locked before held-out evidence becomes available.

Each approved record is validated against a public Draft 2020-12 JSON Schema, saved as a new version, and referenced by a state-transition event. The readable Markdown report is generated from these machine records.

## Repository guide

`contradiction_workflow/` contains the workflow engine, state store, schema validator, model adapters, report generator, and command-line demonstration. `app.py` is the Niu Lai browser interface, and `synthetic_app.py` preserves the original local synthetic interface. `cases/demo_case/` contains one public synthetic case, `cached_outputs/` contains reviewed deterministic outputs, and `schemas/` contains the record contracts. `tests/` implements the acceptance checks. `evaluation/` specifies retrospective derivations, sequential propagation, individual and joint removals, and separate judgments of dependence, quality, and historical discovery.

## Model access

Cached replay is the authoritative reference mode. It lets reviewers reproduce the state transitions and records without credentials, cost, or dependence on a changing model API.

`OllamaAdapter` provides a small example of a local, OpenAI-independent live-model connection. It is marked experimental because a production release needs task-specific prompts, schema-constrained generation, model/version documentation, repeated-run diagnostics, and review of each backend. The current acceptance suite evaluates the cached scientific demonstration rather than claiming that an arbitrary local model will reproduce the reviewed outputs.

## Deliberate limits

This is not a literature-search engine, qualitative coding system, causal estimator, or autonomous theorist. It has small curated packets, file-based session storage and no authentication or durable account-based storage. Step 1 and Step 2 suggestions remain authored examples. The backtest excludes old dependent records and validates newly supplied replacement derivations. It does not certify the truth of an argument or the completeness of a historical trace. Bounded model replay requires separate configuration and substantive review. These limits keep the Stage 1 proof of concept focused on expectation construction, information separation, locking, contradiction adjudication, prospective transfer, and a reviewable contribution record.

Before a real submission, replace placeholder citation metadata, verify the license, publish an immutable release, report clean-install results, and document which components and model backends have actually been tested.

## License and citation

The software retains the MIT License. Only the original synthetic case and synthetic theory notes retain CC0-1.0. The Niu Lai case note, external reporting, and published theory retain their respective rights. The new packet includes short attributed paraphrases and source links, not private correspondence or full articles. Verify sources and permissions before public dissemination. Update `CITATION.cff` with the authors and repository identifier before public release.

## Case provenance and limits

`cases/niu_lai/` contains the evidence, neutral context, theory note, source-verification ledger, attachment baseline, and illustrative contribution records. Its cached outputs are authored fixtures, not sampled model outputs, and their complete input hashes are checked before replay. Its manifest prohibits live model calls through the workflow. The generic prototype is not a security sandbox. Changing inputs while replaying an unchanged cache is not a valid removal replay.

The attachment contains no original process history. Retrospective survival can still be assessed under declared inputs, while claims about the researcher’s actual discovery process remain limited. The narrative was already visible during preparation, so later paragraphs are not an independent holdout. Prospective checkpoints can strengthen historical attribution in future applications.

Liang, A., and Lu, J. (2026). Creative Ownership in the Age of AI. arXiv:2602.12270v1. https://doi.org/10.48550/arXiv.2602.12270. The adaptation concerns removal of assistance; it does not implement training-data unlearning or import the closure-operator theorems into a finite human–AI study.
