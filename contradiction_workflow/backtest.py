"""Backtest sequential outcome survival under declared contribution removals.

A graph records declared dependence; it does not reveal unrecorded human
knowledge. New retrospective derivations may establish replacement routes.
This module validates records and dependencies, not the truth of an argument.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path
from .case import CaseBundle
from .store import payload_hash

STATUSES = {'recovered_equivalent', 'weakened', 'not_recovered_within_budget', 'indeterminate'}
SUPPORT = {'supported', 'partially_supported', 'unsupported', 'unverifiable'}
QUALITY = {'improves', 'unchanged', 'worsens', 'indeterminate'}
KINDS = {'evidence', 'source', 'human_input', 'ai_contribution', 'derived_record'}
BASES = {'documented_independent_derivation', 'retrospective_derivation',
         'bounded_model_replay', 'bounded_search_review', 'insufficient_evidence'}
BOUNDED_BASES = {'bounded_model_replay', 'bounded_search_review'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def validate_ledger(ledger):
    if ledger.get('data_kind') not in {'authored_illustration', 'documented_process'}:
        raise ValueError('Declare the provenance of the contribution record')
    nodes = {n['node_id']: n for n in ledger['nodes']}
    if not nodes or len(nodes) != len(ledger['nodes']):
        raise ValueError('Unique nonempty node IDs are required')
    for node in nodes.values():
        if node['kind'] not in KINDS or not set(node['depends_on']) <= nodes.keys():
            raise ValueError('Invalid node kind or unknown dependency')
        if node['kind'] == 'ai_contribution' and node.get('step') not in range(1, 6):
            raise ValueError('An AI contribution requires its workflow step')
    active, done = set(), set()
    def visit(nid):
        if nid in active:
            raise ValueError('Contribution dependencies must be acyclic')
        if nid in done:
            return
        active.add(nid)
        for parent in nodes[nid]['depends_on']:
            visit(parent)
        active.remove(nid)
        done.add(nid)
    for nid in nodes:
        visit(nid)
    claims = ledger['claims']
    if not claims or len({c['claim_id'] for c in claims}) != len(claims):
        raise ValueError('Unique claim IDs are required')
    for claim in claims:
        if not claim['routes'] or any(not r or not set(r) <= nodes.keys() for r in claim['routes']):
            raise ValueError('Each declared derivation route requires known nodes')
    removals = ledger['removals']
    if len({r['removal_id'] for r in removals}) != len(removals):
        raise ValueError('Removal IDs must be unique')
    for removal in removals:
        if not removal['node_ids'] or any(nid not in nodes or nodes[nid]['kind'] != 'ai_contribution' for nid in removal['node_ids']):
            raise ValueError('A removal must identify recorded AI contributions')
    return nodes


def exclusion_closure(ledger, removed):
    """Remove every dependent record, including human edits of removed inputs."""
    nodes = validate_ledger(ledger)
    if not set(removed) <= nodes.keys():
        raise ValueError('Unknown removed node')
    excluded = set(removed)
    changed = True
    while changed:
        changed = False
        for nid, node in nodes.items():
            if nid not in excluded and excluded.intersection(node['depends_on']):
                excluded.add(nid)
                changed = True
    return excluded


def removal_trace(ledger, removal):
    nodes = validate_ledger(ledger)
    excluded = exclusion_closure(ledger, removal['node_ids'])
    return {
        'removal_id': removal['removal_id'],
        'removed_contribution_ids': removal['node_ids'],
        'excluded_node_ids': sorted(excluded),
        'excluded_descendant_ids': sorted(excluded - set(removal['node_ids'])),
        'retained_node_ids': sorted(nodes.keys() - excluded),
        'claims': [{
            'claim_id': c['claim_id'],
            'surviving_declared_routes': [r for r in c['routes'] if not excluded.intersection(r)],
            'trace_status': 'declared_route_remains' if any(not excluded.intersection(r) for r in c['routes']) else 'no_declared_route_remains',
        } for c in ledger['claims']],
        'interpretation': 'Structural consequences of the supplied graph only. A surviving route requires provenance and source review; no surviving route does not prove non-attainability.',
    }


def make_plan(case_root, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite an audit: {output}')
    case = CaseBundle.load(case_root)
    ledger = read(case.root / 'contribution_ledger.json')
    validate_ledger(ledger)
    if ledger['case_id'] != case.case_id:
        raise ValueError('Ledger and case identifiers differ')
    plan = {
        'schema_version': '0.4.0', 'status': 'removal_specification_not_outcome_data',
        'case_id': case.case_id, 'ledger': ledger,
        'source_hashes': {str(p.relative_to(case.root)): payload_hash(read(p)) for p in sorted(case.root.rglob('*.json'))},
        'removal_traces': [removal_trace(ledger, r) for r in ledger['removals']],
        'historical_attribution': 'indeterminate' if ledger['data_kind'] == 'authored_illustration' or not ledger['baseline']['pre_assistance_checkpoint_available'] else 'requires_provenance_and_substantive_review',
        'evaluation_question': 'Can each outcome be derived without the removed contributions under the declared retained inputs and procedures?',
        'retained_input_policy': ledger.get('retained_input_policy', 'Specify evidence, eligible sources, reasoning rules, and any search limits before assessment.'),
        'implementation': 'Missing historical checkpoints do not block retrospective survival assessment. The planner computes exclusions; reviewers supply and assess replacement derivations.',
    }
    plan['plan_hash'] = payload_hash(plan)
    write(output / 'plan.json', plan)
    write(output / 'assessments_template.json', {
        'schema_version': '0.4.0', 'plan_hash': plan['plan_hash'],
        'data_kind': 'not_collected', 'review_mode': 'sequential_survival', 'assessments': [],
        'record_contract': {
            'removal_id': 'A removal_id from plan.json', 'claim_id': 'A claim_id from the frozen ledger',
            'status': sorted(STATUSES),
            'basis': sorted(BASES),
            'support_with': sorted(SUPPORT), 'support_without': sorted(SUPPORT),
            'quality_without_vs_with': sorted(QUALITY),
            'retained_input_ids': 'Eligible retained node IDs used as direct premises; exclude removed inputs and their descendants',
            'derivation_id': 'Unique identifier for a supported replacement derivation',
            'replacement_outcome': 'Exact substantive claim and scope established on this removal branch',
            'derivation': 'Reviewable inferential steps from the retained premises to the replacement outcome',
            'upstream_derivation_ids': 'Earlier supported derivation IDs from this same removal branch, or [] for a direct route',
            'upstream_outcomes_used': 'Map each upstream ID to the exact replacement_outcome used, preserving weakened scope',
            'evidence_refs': 'Nonempty list of reviewable checkpoint, passage, and output references for a substantive assessment',
            'reason': 'Explanation of equivalence, support, provenance, and any uncertainty',
            'replay_protocol': 'For bounded_model_replay: model_snapshot, settings, input_hash, output_hash, search_budget, completed. Supply hashes of actual inputs/outputs and identify call, token, or time bounds.',
            'search_protocol': 'For bounded_search_review: corpus_boundary, procedure, search_budget, completed. A limited search can provide evidence of non-recovery, not impossibility.',
            'note': 'An evaluator may know the target. Independence concerns the premises and reasoning of the derivation. Missing historical records constrain discovery attribution, not eligibility for this test.',
        },
    })
    return plan


def validate_plan(plan):
    checked = dict(plan)
    saved = checked.pop('plan_hash', None)
    if saved != payload_hash(checked):
        raise ValueError('Frozen plan hash mismatch')
    validate_ledger(plan['ledger'])
    expected = [removal_trace(plan['ledger'], r) for r in plan['ledger']['removals']]
    if expected != plan['removal_traces']:
        raise ValueError('Removal traces do not match the frozen ledger')


def digest_ok(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def validate_derivations(plan, data, rows):
    """Check replacement routes and carry the exact established scope forward."""
    claims = {c['claim_id']: c for c in plan['ledger']['claims']}
    sequential = data.get('review_mode') == 'sequential_survival'
    if sequential and sorted(c.get('step', 0) for c in claims.values()) != [1, 2, 3, 4, 5]:
        raise ValueError('Sequential review requires one registered outcome at each of the five steps')
    derivations = {}
    for key, row in rows.items():
        if row['status'] not in {'recovered_equivalent', 'weakened'}:
            if row.get('upstream_derivation_ids'):
                raise ValueError('An unresolved or unrecovered outcome cannot form a replacement derivation')
            continue
        if sequential or row['basis'] == 'retrospective_derivation':
            for field in ['derivation_id', 'replacement_outcome', 'derivation']:
                if not isinstance(row.get(field), str) or not row[field].strip():
                    raise ValueError(f'A replacement route requires {field}')
            if row['support_without'] not in {'supported', 'partially_supported'}:
                raise ValueError('A surviving or weakened replacement needs evidentiary support')
            did = row['derivation_id']
            if did in derivations:
                raise ValueError('Derivation IDs must be unique')
            derivations[did] = (key, row)
    for did, (key, row) in derivations.items():
        upstream = row.get('upstream_derivation_ids', [])
        used = row.get('upstream_outcomes_used', {})
        if not isinstance(upstream, list) or len(set(upstream)) != len(upstream) or not isinstance(used, dict) or set(used) != set(upstream):
            raise ValueError('Specify each upstream derivation and its exact established outcome')
        for parent in upstream:
            if parent not in derivations:
                raise ValueError('Upstream outcome is missing, unresolved, or not a replacement derivation')
            pkey, prior = derivations[parent]
            if pkey[0] != key[0]:
                raise ValueError('Cannot import a derivation from another removal branch')
            if claims[pkey[1]].get('step', 0) >= claims[key[1]].get('step', 0):
                raise ValueError('Sequential dependencies must point to earlier steps')
            if used[parent] != prior['replacement_outcome']:
                raise ValueError('Downstream reasoning must preserve the exact upstream outcome and scope')
    return derivations


def summarize(plan, data):
    validate_plan(plan)
    if data.get('plan_hash') != plan['plan_hash']:
        raise ValueError('Assessments belong to a different frozen plan')
    kind = data.get('data_kind')
    if kind not in {'not_collected', 'observed_audit', 'illustrative_fixture', 'authored_survival_review'}:
        raise ValueError('Declare assessment data_kind')
    if kind == 'not_collected' and data.get('assessments'):
        raise ValueError('A not-collected form cannot contain assessments')
    if data.get('review_mode', 'claim_audit') not in {'claim_audit', 'sequential_survival'}:
        raise ValueError('Unknown review mode')
    claims = {c['claim_id']: c for c in plan['ledger']['claims']}
    removals = {r['removal_id']: r for r in plan['removal_traces']}
    rows = {}
    for row in data.get('assessments', []):
        key = (row['removal_id'], row['claim_id'])
        if key in rows or key[0] not in removals or key[1] not in claims:
            raise ValueError('Unknown or duplicate claim/removal assessment')
        if row.get('status') not in STATUSES or row.get('support_with') not in SUPPORT or row.get('support_without') not in SUPPORT or row.get('quality_without_vs_with') not in QUALITY:
            raise ValueError('Invalid assessment category')
        if not row.get('reason') or not isinstance(row.get('evidence_refs'), list):
            raise ValueError('Record a reason and explicit evidence references')
        inputs = row.get('retained_input_ids', [])
        if not isinstance(inputs, list) or not set(inputs) <= set(removals[key[0]]['retained_node_ids']):
            raise ValueError('Assessment reuses an excluded or unknown contribution')
        basis = row.get('basis')
        if basis not in BASES:
            raise ValueError('Invalid assessment basis')
        if row['status'] != 'indeterminate':
            if basis == 'insufficient_evidence' or not row['evidence_refs'] or not (inputs or row.get('upstream_derivation_ids')):
                raise ValueError('A substantive assessment requires evidence and eligible direct or upstream premises')
            if row['status'] == 'recovered_equivalent' and (row['support_with'] != 'supported' or row['support_without'] != 'supported'):
                raise ValueError('Equivalence requires supported claims on both routes')
            if row['status'] == 'not_recovered_within_budget' and basis not in BOUNDED_BASES:
                raise ValueError('Finite non-recovery requires a documented bounded search or replay; graph loss is insufficient')
        if basis == 'bounded_model_replay' and (row['status'] != 'indeterminate' or row['quality_without_vs_with'] != 'indeterminate'):
            protocol = row.get('replay_protocol', {})
            required = {'model_snapshot', 'settings', 'input_hash', 'output_hash', 'search_budget', 'completed'}
            if not required <= protocol.keys() or protocol['completed'] is not True or not protocol['model_snapshot'] or not protocol['search_budget'] or not digest_ok(protocol['input_hash']) or not digest_ok(protocol['output_hash']):
                raise ValueError('A completed bounded replay requires its configuration, bounds, and input/output hashes')
        if basis == 'bounded_search_review' and (row['status'] != 'indeterminate' or row['quality_without_vs_with'] != 'indeterminate'):
            protocol = row.get('search_protocol', {})
            if not {'corpus_boundary', 'procedure', 'search_budget', 'completed'} <= protocol.keys() or protocol['completed'] is not True or not all(protocol[k] for k in ['corpus_boundary', 'procedure', 'search_budget']):
                raise ValueError('A bounded search requires its corpus, procedure, limits, and completion status')
        if row['quality_without_vs_with'] != 'indeterminate' and (basis == 'insufficient_evidence' or not row['evidence_refs'] or not (inputs or row.get('upstream_derivation_ids'))):
            raise ValueError('Quality change requires substantive evidence')
        rows[key] = row
    validate_derivations(plan, data, rows)
    result = {
        'schema_version': '0.4.0', 'plan_hash': plan['plan_hash'], 'data_kind': kind,
        'review_mode': data.get('review_mode', 'claim_audit'),
        'status': 'not_estimated_no_assessments' if not rows else 'descriptive_contribution_audit',
        'historical_attribution': plan['historical_attribution'],
        'historical_ai_benefit_estimate': None,
        'retained_input_policy': plan['retained_input_policy'],
        'interpretation': 'Survival concerns derivability under declared inputs and procedures. Retrospective derivations may establish survival despite missing historical checkpoints. Historical discovery attribution, quality, and dependence remain separate; survival is not evidence that AI provided no practical benefit.',
        'removals': {},
    }
    for rid, removal in removals.items():
        observed = [rows[(rid, cid)] for cid in claims if (rid, cid) in rows]
        counts = Counter(r['status'] for r in observed)
        full_supported = [r for r in observed if r['support_with'] == 'supported']
        bounded = [r for r in full_supported if r['basis'] in BOUNDED_BASES and r['status'] != 'indeterminate']
        nonrecovered = [r['claim_id'] for r in bounded if r['status'] == 'not_recovered_within_budget']
        # Only a completely assessed, fixed claim set supports this descriptive
        # fraction. Missing history and graph exclusions never become failures.
        all_coded = len(observed) == len(claims)
        support_known = all(r['support_with'] != 'unverifiable' for r in observed)
        eligible_complete = all_coded and support_known and full_supported and len(bounded) == len(full_supported)
        survival_complete = all_coded and support_known and full_supported and all(r['status'] != 'indeterminate' for r in full_supported)
        surviving = [r['claim_id'] for r in full_supported if r['status'] == 'recovered_equivalent']
        progression = [{
            'step': c.get('step'), 'claim_id': cid,
            'status': rows.get((rid, cid), {}).get('status', 'not_assessed'),
            'basis': rows.get((rid, cid), {}).get('basis'),
            'replacement_outcome': rows.get((rid, cid), {}).get('replacement_outcome'),
            'derivation_id': rows.get((rid, cid), {}).get('derivation_id'),
            'upstream_derivation_ids': rows.get((rid, cid), {}).get('upstream_derivation_ids', []),
        } for cid, c in sorted(claims.items(), key=lambda item: item[1].get('step', 0))]
        result['removals'][rid] = {
            'registered_claims': len(claims), 'entered_assessments': len(observed),
            'missing_assessments': len(claims) - len(observed),
            'assessment_counts': {s: counts[s] for s in sorted(STATUSES)},
            'surviving_equivalent_claim_ids': surviving,
            'survival_fraction': len(surviving) / len(full_supported) if survival_complete else None,
            'survival_denominator': len(full_supported) if survival_complete else None,
            'step_progression': progression,
            'final_step_status': progression[-1]['status'],
            'quality_without_vs_with': dict(Counter(r['quality_without_vs_with'] for r in observed)),
            'claims_without_declared_route': [c['claim_id'] for c in removal['claims'] if c['trace_status'] == 'no_declared_route_remains'],
            'supported_claims_assessed_in_bounded_replay': sum(r['basis'] == 'bounded_model_replay' for r in bounded),
            'supported_claims_assessed_in_bounded_search': len(bounded),
            'not_recovered_claim_ids': nonrecovered,
            'non_recovery_fraction': len(nonrecovered) / len(full_supported) if eligible_complete else None,
            'fraction_denominator': len(full_supported) if eligible_complete else None,
            'fraction_note': 'Survival may be established by reviewed retrospective derivations. The non-recovery fraction additionally requires bounded assessments of every supported claim. Neither fraction is a historical AI-benefit or authorship percentage.',
        }
    result['assessments'] = list(rows.values())
    return result


def report_text(result):
    lines = ['# Sequential outcome survival backtest', '', f"Data kind: {result['data_kind']}",
             f"Status: {result['status']}", f"Historical attribution: {result['historical_attribution']}", '',
             result['interpretation'], '', 'Retained inputs: '+result['retained_input_policy'], '',
             '| Removal | Assessed | Survives | Weaker | Missing or indeterminate | Final step |',
             '| --- | ---: | ---: | ---: | ---: | --- |']
    for rid, r in result['removals'].items():
        counts = r['assessment_counts']
        lines.append(f"| {rid} | {r['entered_assessments']} | {counts['recovered_equivalent']} | {counts['weakened']} | {r['missing_assessments']+counts['indeterminate']} | {r['final_step_status']} |")
    for rid, r in result['removals'].items():
        if not r['entered_assessments']:
            continue
        lines += ['', '## '+rid, '', '| Step | Outcome | Assessment | Depends on replacement |', '| ---: | --- | --- | --- |']
        for step in r['step_progression']:
            lines.append(f"| {step['step']} | {step['claim_id']} | {step['status']} | {', '.join(step['upstream_derivation_ids']) or 'Direct retained premises'} |")
        for row in sorted([a for a in result['assessments'] if a['removal_id']==rid], key=lambda a: a['claim_id']):
            if row.get('derivation'):
                lines += ['', '### '+row['claim_id']+' '+row['derivation_id'], '', row['replacement_outcome'], '',
                          row['derivation'], '', 'Evidence: '+', '.join(row['evidence_refs']), '', 'Assessment: '+row['reason']]
    lines += ['', 'A missing route in the original graph does not prevent a new, independently supported derivation.',
              'Historical uncertainty does not automatically make outcome survival indeterminate.',
              'Authored survival reviews are methodological illustrations requiring substantive review. Counts do not establish unaided historical discovery, zero practical AI benefit, or an authorship share.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('plan')
    p.add_argument('--case', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('summarize')
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--assessments', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'plan':
        plan = make_plan(args.case, args.output)
        print(f"Specified {len(plan['removal_traces'])} contribution removals within one record; no outcome data generated.")
    else:
        if args.output.exists():
            raise FileExistsError('Refusing to overwrite an audit summary')
        result = summarize(read(args.plan), read(args.assessments))
        write(args.output / 'summary.json', result)
        (args.output / 'report.md').write_text(report_text(result), encoding='utf-8')
        print(result['status'])

if __name__ == '__main__':
    main()
