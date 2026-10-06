"""Replay the authored five-step retrospective survival review without model calls."""
from __future__ import annotations
import argparse
from pathlib import Path
from .backtest import make_plan, read, write, summarize, report_text


def run_survival_review(repository_root: Path, output: Path):
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite a survival review: {output}')
    case = repository_root / 'cases' / 'niu_lai'
    plan = make_plan(case, output / 'plan')
    assessment = read(case / 'retrospective_survival_review.json')
    assessment['plan_hash'] = plan['plan_hash']
    result = summarize(plan, assessment)
    write(output / 'assessments.json', assessment)
    write(output / 'summary.json', result)
    (output / 'report.md').write_text(report_text(result), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run_survival_review(Path(__file__).resolve().parents[1], args.output)
    branch = result['removals']['without_recorded_AI']
    print(f"Authored survival review: {len(branch['surviving_equivalent_claim_ids'])}/{branch['registered_claims']} qualified outcomes survive under the declared corpus. Historical discovery attribution remains {result['historical_attribution']}.")


if __name__ == '__main__':
    main()
