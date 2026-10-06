from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path
from contradiction_workflow import CaseBundle, CachedModelAdapter, ProjectStore, Workflow
from contradiction_workflow.backtest import make_plan, read, summarize, validate_ledger, exclusion_closure, removal_trace
from contradiction_workflow.niu_lai_demo import BoundIllustrationAdapter, run_illustration

ROOT=Path(__file__).resolve().parents[1]


class ContributionAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.plan=make_plan(ROOT/'cases/niu_lai',self.base/'plan')
        self.data=read(self.base/'plan/assessments_template.json')
        self.data['review_mode']='claim_audit'
        self.ledger=self.plan['ledger']

    def row(self, cid='I1', rid='without_A1', status='recovered_equivalent'):
        return {'removal_id':rid,'claim_id':cid,'status':status,
                'basis':'bounded_model_replay','support_with':'supported',
                'support_without':'supported' if status=='recovered_equivalent' else 'partially_supported',
                'quality_without_vs_with':'unchanged','retained_input_ids':['E0'],
                'reason':'Synthetic test judgment; no empirical interpretation.',
                'evidence_refs':['synthetic-test-input','synthetic-test-output'],
                'replay_protocol':{'model_snapshot':'synthetic-fixture','settings':{'temperature':0},
                                   'input_hash':'a'*64,'output_hash':'b'*64,'search_budget':{'max_calls':1},'completed':True}}

    def test_descendants_include_approval_records_but_preserve_sources(self):
        excluded=exclusion_closure(self.ledger,['A3'])
        self.assertEqual(excluded,{'A3','D3','A4','A5','D5'})
        self.assertNotIn('E0',excluded);self.assertNotIn('T0',excluded)
        with self.assertRaises(FileExistsError): make_plan(ROOT/'cases/niu_lai',self.base/'plan')

    def test_independent_attachment_route_survives_all_ai_removals(self):
        trace=next(r for r in self.plan['removal_traces'] if r['removal_id']=='without_recorded_AI')
        claim=next(c for c in trace['claims'] if c['claim_id']=='I1')
        self.assertEqual(claim['surviving_declared_routes'],[['E0']])
        self.assertIn('T0',trace['retained_node_ids'])
        self.assertEqual(self.plan['historical_attribution'],'indeterminate')
        self.assertNotIn('assignments',self.plan)

    def test_joint_removal_exposes_redundant_routes(self):
        ledger=copy.deepcopy(self.ledger)
        ledger['claims']=[{'claim_id':'R','text':'Synthetic redundant claim','routes':[['A1'],['A2']]}]
        for nodes in [['A1'],['A2']]:
            self.assertEqual(removal_trace(ledger,{'removal_id':'x','node_ids':nodes})['claims'][0]['trace_status'],'declared_route_remains')
        both=removal_trace(ledger,{'removal_id':'x','node_ids':['A1','A2']})
        self.assertEqual(both['claims'][0]['trace_status'],'no_declared_route_remains')

    def test_cycle_unknown_dependency_and_source_deletion_rejected(self):
        for mode in ['cycle','unknown','source_removal']:
            ledger=copy.deepcopy(self.ledger)
            if mode=='cycle': ledger['nodes'][0]['depends_on']=['A1']
            elif mode=='unknown': ledger['nodes'][0]['depends_on']=['missing']
            else: ledger['removals'][0]['node_ids']=['T0']
            with self.assertRaises(ValueError): validate_ledger(ledger)

    def test_empty_form_and_missing_routes_never_become_outcome_data(self):
        result=summarize(self.plan,self.data)
        self.assertEqual(result['status'],'not_estimated_no_assessments')
        self.assertIsNone(result['historical_ai_benefit_estimate'])
        for r in result['removals'].values():
            self.assertEqual(r['missing_assessments'],5)
            self.assertEqual(sum(r['assessment_counts'].values()),0)
            self.assertIsNone(r['non_recovery_fraction'])
        self.assertIn('I5',result['removals']['without_A3']['claims_without_declared_route'])

    def test_excluded_inputs_and_unknown_assessment_ids_rejected(self):
        self.data['data_kind']='illustrative_fixture'
        for change in [{'retained_input_ids':['A1']},{'claim_id':'unknown'},{'removal_id':'unknown'}]:
            row=self.row();row.update(change);self.data['assessments']=[row]
            with self.assertRaises(ValueError): summarize(self.plan,self.data)

    def test_graph_loss_or_incomplete_replay_cannot_establish_non_recovery(self):
        self.data['data_kind']='illustrative_fixture'
        for basis in ['insufficient_evidence','documented_independent_derivation']:
            row=self.row(status='not_recovered_within_budget');row['basis']=basis
            self.data['assessments']=[row]
            with self.assertRaises(ValueError): summarize(self.plan,self.data)
        row=self.row(status='not_recovered_within_budget');row['replay_protocol']['completed']=False
        self.data['assessments']=[row]
        with self.assertRaises(ValueError): summarize(self.plan,self.data)

    def test_partial_assessments_leave_fraction_undefined(self):
        self.data['data_kind']='illustrative_fixture';self.data['assessments']=[self.row(status='not_recovered_within_budget')]
        r=summarize(self.plan,self.data)['removals']['without_A1']
        self.assertEqual(r['not_recovered_claim_ids'],['I1'])
        self.assertEqual(r['missing_assessments'],4)
        self.assertIsNone(r['non_recovery_fraction'])

    def test_complete_bounded_assessment_reports_denominator_and_quality_separately(self):
        self.data['data_kind']='illustrative_fixture'
        rows=[self.row(cid=c['claim_id']) for c in self.ledger['claims']]
        rows[0].update(status='not_recovered_within_budget',support_without='unsupported',quality_without_vs_with='worsens')
        rows[1].update(status='weakened',support_without='partially_supported',quality_without_vs_with='improves')
        self.data['assessments']=rows
        result=summarize(self.plan,self.data);r=result['removals']['without_A1']
        self.assertEqual(r['non_recovery_fraction'],1/5)
        self.assertEqual(r['fraction_denominator'],5)
        self.assertEqual(r['assessment_counts']['weakened'],1)
        self.assertEqual(r['quality_without_vs_with']['improves'],1)
        self.assertIsNone(result['historical_ai_benefit_estimate'])
        self.assertEqual(result['historical_attribution'],'indeterminate')

    def test_equivalence_requires_support_and_plan_integrity(self):
        self.data['data_kind']='illustrative_fixture';self.data['assessments']=[self.row()]
        self.data['assessments'][0]['support_without']='unsupported'
        with self.assertRaises(ValueError): summarize(self.plan,self.data)
        altered=copy.deepcopy(self.plan);altered['ledger']['baseline']['pre_assistance_checkpoint_available']=True
        with self.assertRaises(ValueError): summarize(altered,self.data)
        self.data['assessments']=[self.row(),self.row()]
        with self.assertRaises(ValueError): summarize(self.plan,self.data)

    def test_indeterminate_or_independent_route_is_not_bounded_non_recovery(self):
        self.data['data_kind']='illustrative_fixture'
        row=self.row();row['basis']='documented_independent_derivation';row.pop('replay_protocol')
        self.data['assessments']=[row]
        r=summarize(self.plan,self.data)['removals']['without_A1']
        self.assertEqual(r['assessment_counts']['recovered_equivalent'],1)
        self.assertEqual(r['supported_claims_assessed_in_bounded_replay'],0)
        row.update(status='indeterminate',basis='insufficient_evidence',support_without='unverifiable',quality_without_vs_with='indeterminate',retained_input_ids=[],evidence_refs=[])
        r=summarize(self.plan,self.data)['removals']['without_A1']
        self.assertEqual(r['assessment_counts']['indeterminate'],1)
        self.assertIsNone(r['non_recovery_fraction'])

    def test_neutral_packet_excludes_case_identity_and_focal_outcomes(self):
        case=CaseBundle.load(ROOT/'cases/niu_lai')
        text=json.dumps(case.expectation_packet(['BSR2010'])).lower()
        for token in ['niu','lai','2026','rmb','polariz','memes','ticket purchasing','held_out']:
            self.assertNotIn(token,text)

    def test_case_replay_stops_without_transfer_evidence(self):
        store=run_illustration(ROOT,self.base/'run')
        self.assertEqual(store.state,'reconstruction_locked')
        case=CaseBundle.load(ROOT/'cases/niu_lai')
        flow=Workflow(case,store,BoundIllustrationAdapter(case.root/'reference_outputs'))
        with self.assertRaises(RuntimeError): flow.draft_transfer_score()
        self.assertIsNone(read(self.base/'run/status.json')['ai_benefit_estimate'])

    def test_case_disallows_live_adapter_and_changed_cached_inputs(self):
        case=CaseBundle.load(ROOT/'cases/niu_lai')
        store=ProjectStore.create(self.base/'run',case.case_id)
        with self.assertRaises(ValueError): Workflow(case,store,object())
        adapter=BoundIllustrationAdapter(case.root/'reference_outputs')
        packet=case.expectation_packet(['BSR2010'])
        adapter.run('expectation',packet)
        packet['neutral_context']['focal_outcome']='outcome leakage'
        with self.assertRaises(ValueError): adapter.run('expectation',packet)

    def test_unselected_source_links_and_changed_expectation_hash_rejected(self):
        case=CaseBundle.load(ROOT/'cases/demo_case')
        store=ProjectStore.create(self.base/'run',case.case_id)
        flow=Workflow(case,store,CachedModelAdapter(ROOT/'cached_outputs'))
        flow.approve_puzzle('A pattern',['E1'],[])
        flow.approve_literature_map(['T1'])
        with self.assertRaises(ValueError): flow.draft_expectation()  # Fixture also cites unselected T2.
        case2=CaseBundle.load(ROOT/'cases/niu_lai')
        s2=ProjectStore.create(self.base/'run2',case2.case_id)
        f2=Workflow(case2,s2,BoundIllustrationAdapter(case2.root/'reference_outputs'))
        f2.approve_puzzle('A pattern',['N1'],[]);f2.approve_literature_map(['BSR2010'])
        draft=f2.draft_expectation();draft['allowed_input_hash']='0'*64
        with self.assertRaises(ValueError): f2.lock_expectation(draft)

if __name__=='__main__':
    unittest.main()
