"""Prespecified confirmatory analysis (see docs/STAGE33_CONFIRMATORY_PROTOCOL.md).

Unit: scenario = (seed, volatility) within a forecast condition, pooled over the
three volatility levels (n = 150 per condition). All tests are paired, one-sided
Wilcoxon signed-rank tests; non-inferiority tests shift the paired differences by
the margin. Thirteen primary tests are Holm-adjusted together at alpha = 0.05.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median

from scipy.stats import wilcoxon

from .analysis import bootstrap_ci, render, summarise
from .confirmatory import PRIMARY, SKILFUL, UNSKILLED, load

ALPHA = .05
NI_FRACTION = .10     # H2b margin = 10% of mean uncontrolled exceedance per scenario in the condition
ORIGINAL_NI_FRACTION = .05  # first-draft H2b margin, reported as a secondary analysis (protocol Section 5)
H3_FRACTION = .05     # H3 (no harm) margin = 5%, unchanged from the first draft
EXCEEDANCE, THROUGHPUT = 'total_ramp_exceedance_kw', 'total_throughput_kwh'


def _index(results):
    table = {}
    for row in results:
        key = (row['forecast'], row['seed'], row['volatility'])
        table.setdefault(key, {})[row['controller']] = row['metrics']
    return table


def _paired(table, forecast, left, right, metric):
    keys = sorted(k for k in table if k[0] == forecast)
    return [table[k][left][metric] - table[k][right][metric] for k in keys]


def _one_sided_less(values):
    if all(v == 0 for v in values):
        return 1.
    return float(wilcoxon(values, alternative='less').pvalue)


def holm(pvalues):
    order = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    adjusted, running = [0.] * len(pvalues), 0.
    for rank, i in enumerate(order):
        running = max(running, min(1., (len(pvalues) - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def primary_tests(results, primary=PRIMARY, ni_fraction=NI_FRACTION, h3_fraction=H3_FRACTION):
    table = _index(results)
    tests = []

    def add(name, forecast, diffs, margin, description):
        shifted = [d - margin for d in diffs]
        low, high = bootstrap_ci(diffs)
        tests.append({'test': name, 'forecast': forecast, 'n': len(diffs), 'description': description,
                      'margin': margin, 'mean_difference': mean(diffs), 'median_difference': median(diffs),
                      'ci95_mean_difference': [low, high], 'left_better': sum(d < 0 for d in diffs),
                      'p_one_sided': _one_sided_less(shifted)})

    for f in SKILFUL + UNSKILLED:
        keys = [k for k in table if k[0] == f]
        reference = mean(table[k]['uncontrolled'][EXCEEDANCE] for k in keys)
        margin = (ni_fraction if f in SKILFUL else h3_fraction) * reference
        if f in SKILFUL:
            add('H1', f, _paired(table, f, primary, 'uncontrolled', EXCEEDANCE), 0.,
                'exceedance: primary < uncontrolled')
            add('H2a', f, _paired(table, f, primary, 'adaptive', THROUGHPUT), 0.,
                'throughput: primary < Stage 3.1 adaptive')
            add('H2b', f, _paired(table, f, primary, 'adaptive', EXCEEDANCE), margin,
                'exceedance non-inferiority: primary - adaptive < margin')
        else:
            add('H3', f, _paired(table, f, primary, 'uncontrolled', EXCEEDANCE), margin,
                'no harm: primary - uncontrolled < margin')
    for test, adjusted in zip(tests, holm([t['p_one_sided'] for t in tests])):
        test['p_holm'] = adjusted
        test['supported'] = adjusted < ALPHA
    return tests


def report(completed, results):
    tests = primary_tests(results)
    lines = ['# Stage 3.3 confirmatory results', '',
             f"Study role: {completed['study_role']}  ",
             f"Protocol SHA-256: `{completed['protocol_sha256']}`  ",
             f"Code commit: `{completed['git_head']}`  ",
             f"Runs: {len(results)}", '', '## Primary hypotheses (Holm-adjusted, one-sided, alpha 0.05)', '',
             '| Test | Forecast | n | Margin | Mean diff [95% CI] | Median | p | p (Holm) | Supported |',
             '|---|---|---|---|---|---|---|---|---|']
    for t in tests:
        lines.append(f"| {t['test']} | {t['forecast']} | {t['n']} | {t['margin']:.1f} | "
                     f"{t['mean_difference']:+.1f} [{t['ci95_mean_difference'][0]:+.1f}, {t['ci95_mean_difference'][1]:+.1f}] | "
                     f"{t['median_difference']:+.1f} | {t['p_one_sided']:.2e} | {t['p_holm']:.2e} | "
                     f"{'yes' if t['supported'] else 'no'} |")
    original = [t for t in primary_tests(results, ni_fraction=ORIGINAL_NI_FRACTION) if t['test'] == 'H2b']
    lines += ['', '## Secondary: H2b at the originally drafted 5% margin (unadjusted; see protocol Section 5)', '',
              '| Forecast | Margin | Mean diff | p (one-sided, unadjusted) |', '|---|---|---|---|']
    for t in original:
        lines.append(f"| {t['forecast']} | {t['margin']:.1f} | {t['mean_difference']:+.1f} | {t['p_one_sided']:.2e} |")
    lines += ['', '## Secondary (descriptive, pooled over volatility)', '', '```', render(summarise(results)), '```']
    for test in tests:
        test['secondary_h2b_original_margin'] = None
    for t in original:
        next(x for x in tests if x['test'] == 'H2b' and x['forecast'] == t['forecast'])[
            'secondary_h2b_original_margin'] = {k: t[k] for k in ('margin', 'mean_difference', 'p_one_sided')}
    return tests, '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    completed, results = load(args.run_dir)
    tests, text = report(completed, results)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'primary_tests.json').write_text(json.dumps(tests, indent=1), encoding='utf-8')
    (args.out / 'REPORT.md').write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
