from __future__ import annotations
import copy
import tempfile
import unittest
from pathlib import Path
from contradiction_workflow.backtest import make_plan, read, summarize
from contradiction_workflow.survival_demo import run_survival_review

ROOT = Path(__file__).resolve().parents[1]


class SequentialSurvivalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.plan = make_plan(ROOT / 'cases/niu_lai', self.base / 'plan')
        self.review = read(ROOT / 'cases/niu_lai/retrospective_survival_review.json')
        self.review['plan_hash'] = self.plan['plan_hash']

    def test_retrospective_survival_is_allowed_without_historical_checkpoints(self):
        self.assertFalse(self.plan['ledger']['baseline']['pre_assistance_checkpoint_available'])
        result = summarize(self.plan, self.review)
        branch = result['removals']['without_recorded_AI']
        self.assertEqual(branch['survival_fraction'], 1)
        self.assertEqual(branch['survival_denominator'], 5)
        self.assertEqual(branch['final_step_status'], 'recovered_equivalent')
        self.assertEqual(result['historical_attribution'], 'indeterminate')
        self.assertEqual(result['data_kind'], 'authored_survival_review')
        self.assertIsNone(result['historical_ai_benefit_estimate'])

    def test_replacement_routes_can_restore_outcomes_missing_from_original_graph(self):
        result = summarize(self.plan, self.review)
        branch = result['removals']['without_recorded_AI']
        self.assertIn('I3', branch['claims_without_declared_route'])
        self.assertIn('I3', branch['surviving_equivalent_claim_ids'])
        self.assertEqual(branch['step_progression'][3]['upstream_derivation_ids'], ['R3'])
        self.assertTrue(any(r['removal_id']=='without_steps_1_to_4' for r in self.plan['removal_traces']))

    def test_unknown_forward_and_cross_branch_dependencies_are_rejected(self):
        for parent in ['missing', 'R5']:
            review = copy.deepcopy(self.review)
            review['assessments'][2]['upstream_derivation_ids'] = [parent]
            review['assessments'][2]['upstream_outcomes_used'] = {parent: 'A claimed outcome'}
            with self.assertRaises(ValueError): summarize(self.plan, review)
        review = copy.deepcopy(self.review)
        review['assessments'][0]['removal_id'] = 'without_A1'
        with self.assertRaises(ValueError): summarize(self.plan, review)

    def test_weakened_upstream_scope_cannot_be_silently_restored(self):
        review = copy.deepcopy(self.review)
        first = review['assessments'][0]
        first.update(status='weakened', support_without='partially_supported', replacement_outcome='Only the reported participation component is retained.')
        with self.assertRaises(ValueError): summarize(self.plan, review)
        for row in review['assessments']:
            if 'R1' in row.get('upstream_outcomes_used', {}):
                row['upstream_outcomes_used']['R1'] = first['replacement_outcome']
        result = summarize(self.plan, review)
        self.assertEqual(result['removals']['without_recorded_AI']['assessment_counts']['weakened'], 1)
        # Record consistency is verified; substantive adequacy still needs review.

    def test_unresolved_outcome_cannot_be_used_but_a_direct_route_remains_possible(self):
        review = copy.deepcopy(self.review)
        row = review['assessments'][3]
        row.update(status='indeterminate', basis='insufficient_evidence', support_without='unverifiable',
                   quality_without_vs_with='indeterminate', upstream_derivation_ids=[], upstream_outcomes_used={})
        with self.assertRaises(ValueError): summarize(self.plan, review)
        final = review['assessments'][4]
        final['upstream_derivation_ids'].remove('R4')
        final['upstream_outcomes_used'].pop('R4')
        final['derivation'] = 'Synthetic direct-route test: the retained participation observations and awareness rival motivate a question without requiring the unresolved compatibility judgment.'
        result = summarize(self.plan, review)
        branch = result['removals']['without_recorded_AI']
        self.assertEqual(branch['final_step_status'], 'recovered_equivalent')
        self.assertIsNone(branch['survival_fraction'])

    def test_bounded_qualitative_search_can_record_limited_non_recovery(self):
        data = read(self.base / 'plan/assessments_template.json')
        data.update(data_kind='illustrative_fixture', review_mode='claim_audit')
        row = copy.deepcopy(self.review['assessments'][1])
        row.update(status='not_recovered_within_budget', basis='bounded_search_review',
                   support_without='unverifiable', upstream_derivation_ids=[], upstream_outcomes_used={},
                   search_protocol={'corpus_boundary':'Synthetic test corpus', 'procedure':'Inspect all indexed source notes', 'search_budget':'One complete pass', 'completed':True})
        data['assessments'] = [row]
        result = summarize(self.plan, data)
        self.assertEqual(result['removals']['without_recorded_AI']['not_recovered_claim_ids'], ['I2'])
        row['search_protocol']['completed'] = False
        with self.assertRaises(ValueError): summarize(self.plan, data)

    def test_demonstration_is_reproducible_and_labeled_as_authored(self):
        result = run_survival_review(ROOT, self.base / 'demo')
        self.assertEqual(result['data_kind'], 'authored_survival_review')
        report = (self.base / 'demo/report.md').read_text()
        self.assertIn('R5', report)
        self.assertIn('conjecture', report)
        self.assertIn('Historical uncertainty does not automatically', report)
        with self.assertRaises(FileExistsError): run_survival_review(ROOT, self.base / 'demo')


if __name__ == '__main__':
    unittest.main()
