# Instructions for sequential survival review

1. Register the target outcome at each of the five steps. Define substantive equivalence in terms of mechanism, relationship, assumptions, scope, and evidence.
2. Declare the retained-input policy. List the evidence and eligible sources, including whether their original availability is documented or assumed for the backtest. Preserve process histories where available.
3. Identify AI contributions for individual, joint, or cumulative removal. Invalidate their old descendants. The software computes this exclusion from the declared graph.
4. Construct and review replacement derivations. The evaluator may know the target. Each argument must establish its conclusion from eligible premises; the target and removed suggestion cannot serve as their own premises.
5. Code `recovered_equivalent`, `weakened`, `not_recovered_within_budget`, or `indeterminate`. Missing historical logs alone do not require an indeterminate survival judgment. Uncheckable support or an unsupported inference does.
6. For each surviving or weakened replacement, supply `derivation_id`, `replacement_outcome`, `derivation`, `retained_input_ids`, and evidence references. List earlier replacement IDs in `upstream_derivation_ids` and copy the exact claims used into `upstream_outcomes_used`.
7. Carry established replacements forward in step order. References to another removal branch, a later step, an unresolved outcome, or a silently strengthened upstream claim are rejected. A direct derivation can proceed without an unrelated unresolved earlier outcome.
8. Assess quality separately. Retain weakened claims, corrections, improved alternatives, reviewer disagreement, and practical costs. Report historical discovery attribution separately from survival.

Use `assessments_template.json` with `review_mode: sequential_survival`. Its plan hash binds the form to the frozen inputs. `not_collected` is for empty forms; `authored_survival_review` labels a worked methodological judgment; `illustrative_fixture` is for software tests; `observed_audit` is for externally documented substantive assessments. None of these labels supplies an unaided historical counterfactual automatically.

A retrospective derivation does not require a search failure or a model call. `bounded_search_review` and `bounded_model_replay` require explicit procedures, limits, and completion evidence when reporting finite non-recovery. Empty or failed work must not be counted as failure of attainability.

Software validates record consistency. Reviewers assess whether the argument is sound, the sources support it, and no removed premise has been concealed in prose. Hashes do not certify those substantive judgments.
