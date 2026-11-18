"""Stage 5 analysis (second site): primary tests for the graded-switch controller G.

The inference machinery of Stage 4 is reused: ISO-week units, one-sided Wilcoxon on weekly
means, a week-block bootstrap and Holm correction. Only the hypothesis list differs.

G = ``graded_mpc`` (stochastic MPC scaled by the graded skill weight); P = ``stochastic_skill``
(binary switch, the Stage 4 controller).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

from publication_v2.stage4.analysis import (EXC, THR, block_ci, descriptive, forecast_skill, holm, index, paired,
                                            render_skill, weekly)

G, P = 'graded_mpc', 'stochastic_skill'
SPATIAL = 'lightgbm_spatial'
# (id, forecast, metric, left, right, margin as a fraction of U or None, description)
TESTS = (
    ('S1', SPATIAL, EXC, G, 'uncontrolled', None, 'G reduces ramp exceedance vs no battery'),
    ('S2', SPATIAL, THR, G, P, None, 'G uses less throughput than the binary-switch controller P'),
    ('S3', SPATIAL, EXC, G, P, .01, 'G exceedance non-inferior to P (margin 1% of U)'),
    ('S4', SPATIAL, THR, G, 'adaptive', None, 'G uses less throughput than adaptive MPC'),
    ('S5', 'persistence', EXC, G, 'uncontrolled', .05, 'no material harm without skill (margin 5% of U)'),
    ('S6', 'lightgbm', EXC, G, 'uncontrolled', .05, 'no material harm with a weak forecast (margin 5% of U)'),
)


def primary_tests(results, tests=TESTS):
    table = index(results)
    rows = []
    for tid, forecast, metric, left, right, fraction, text in tests:
        diff, weeks = paired(table, forecast, metric, left, right)
        u = float(np.mean([r['metrics'][EXC] for r in table[(forecast, 'uncontrolled')].values()]))
        margin = 0. if fraction is None else fraction * u
        means, _, _ = weekly(diff, weeks)
        p = float(wilcoxon(means - margin, alternative='less', zero_method='zsplit').pvalue)
        lo, hi = block_ci(diff, weeks)
        rows.append({'test': tid, 'forecast': forecast, 'metric': metric, 'contrast': f'{left} - {right}',
                     'description': text, 'episodes': int(len(diff)), 'weeks': int(len(means)), 'U_kw': u,
                     'margin': margin, 'mean_difference': float(diff.mean()), 'ci95_block_bootstrap': [lo, hi],
                     'p_one_sided': p})
    for row, adjusted in zip(rows, holm([r['p_one_sided'] for r in rows])):
        row['p_holm'], row['supported'] = float(adjusted), bool(adjusted < .05)
    return rows


def render(tests, rows, record, title):
    lines = [f'# {title}', '', f"Episodes: {record['episodes']} (paired). Inference unit: ISO week; Wilcoxon on weekly "
             'means; CIs from a week-block bootstrap; Holm across all primary tests.', '',
             '## Primary tests', '', '| Test | Forecast | Claim | Margin | Mean diff [95% CI] | weeks | p (Holm) | Supported |',
             '|---|---|---|---|---|---|---|---|']
    for t in tests:
        lo, hi = t['ci95_block_bootstrap']
        lines.append(f"| {t['test']} | {t['forecast']} | {t['description']} | {t['margin']:.1f} | "
                     f"{t['mean_difference']:+.1f} [{lo:+.1f}, {hi:+.1f}] | {t['weeks']} | {t['p_holm']:.2e} | "
                     f"{'yes' if t['supported'] else 'no'} |")
    lines += ['', '## All controllers', '', '| Forecast | Controller | Change vs none [95% CI] | Throughput kWh/ep | '
              'Reduction per 100 kWh | Idle (binary switch) | Safety viol. |', '|---|---|---|---|---|---|---|']
    for r in rows:
        if r['controller'] == 'uncontrolled':
            continue
        lo, hi = r['change_ci95_pct']
        eff = -r['change_vs_uncontrolled_pct'] / r['throughput_kwh'] * 100 if r['throughput_kwh'] > 1 else 0.
        lines.append(f"| {r['forecast']} | {r['controller']} | {r['change_vs_uncontrolled_pct']:+.2f}% [{lo:+.2f}, {hi:+.2f}] | "
                     f"{r['throughput_kwh']:.0f} | {eff:.2f}% | {r['skill_gated_fraction']:.2f} | {r['safety_violations']} |")
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('results', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--title', default='Stage 5 second-site results')
    args = parser.parse_args(argv)
    record = json.loads(args.results.read_text(encoding='utf-8'))
    tests, rows = primary_tests(record['results']), descriptive(record['results'])
    args.out.mkdir(parents=True, exist_ok=True)
    text = render(tests, rows, record, args.title)
    if (args.results.parent / 'series.npz').exists():
        skill = forecast_skill(args.results.parent)
        text += render_skill(skill)
        (args.out / 'forecast_skill.json').write_bytes((json.dumps(skill, indent=1) + chr(10)).encode())
    (args.out / 'tests.json').write_bytes((json.dumps({'tests': tests, 'descriptive': rows}, indent=1) + chr(10)).encode())
    (args.out / 'REPORT.md').write_bytes(text.encode())
    print(text)


if __name__ == '__main__':
    main()
