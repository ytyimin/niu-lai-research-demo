"""Replay the authored Niu Lai illustration; no empirical AI effects are measured."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .case import CaseBundle
from .model import CachedModelAdapter
from .store import ProjectStore, payload_hash
from .workflow import Workflow


class BoundIllustrationAdapter(CachedModelAdapter):
    """Reject a cached output when the scientific input differs from its fixture."""
    def run(self, task, payload):
        contracts = json.loads((self.cache_root / 'input_hashes.json').read_text(encoding='utf-8'))
        if contracts.get(task) != payload_hash(payload):
            raise ValueError(f'Illustrative input changed for {task}; re-author and review the fixture')
        return super().run(task, payload)


def run_illustration(repository_root: Path, output: Path) -> ProjectStore:
    case = CaseBundle.load(repository_root / 'cases' / 'niu_lai')
    example = json.loads((case.root / 'illustration.json').read_text(encoding='utf-8'))
    store = ProjectStore.create(output, case.case_id)
    flow = Workflow(case, store, BoundIllustrationAdapter(case.root / 'reference_outputs'))
    actor = 'scripted_illustration_not_independent_reviewer'
    flow.approve_puzzle(example['observed_pattern'], example['evidence_ids'], example['rival_descriptions'], actor)
    flow.approve_literature_map(example['selected_source_ids'], actor)
    flow.lock_expectation(flow.draft_expectation(), actor)
    flow.adjudicate_contradiction(flow.draft_contradiction(), actor)
    flow.lock_reconstruction(flow.draft_reconstruction(), actor)
    parts = ['# Niu Lai illustrative workflow', '',
        'Authored workflow outputs. The separate survival review provides retrospective derivations; neither run measures historical AI benefit.', '',
        'Transfer is NOT EVALUATED: no independent held-out evidence was supplied.', '']
    for record in ('puzzle','literature_map','expectation','contradiction','reconstruction'):
        parts += ['## '+record.replace('_',' ').capitalize(), '',
                  '```json', json.dumps(store.latest_record(record)['payload'],ensure_ascii=False,indent=2), '```', '']
    parts += ['## Evidentiary status', '',
        'The original case summary already described participation and exhibitor disagreement. ',
        'Its original AI provenance is unknown and no pre-assistance checkpoint was supplied. ',
        'The sequential survival review may establish alternative derivations despite that missing history; it does not reconstruct original discovery.']
    (output / 'illustrative_report.md').write_text('\n'.join(parts)+'\n',encoding='utf-8')
    (output / 'status.json').write_text(json.dumps({
        'kind':'authored_illustration', 'state':store.state, 'transfer':'not_evaluated',
        'ai_benefit_estimate':None, 'reason':'Original discovery history is unknown; conditional survival is evaluated separately'
    },indent=2)+'\n',encoding='utf-8')
    return store


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('runs/niu-lai'))
    args=parser.parse_args()
    store=run_illustration(Path(__file__).resolve().parents[1],args.output)
    print(f'Illustration saved: {store.root}; state={store.state}; transfer=not evaluated; AI benefit=unestimated')

if __name__=='__main__':
    main()
