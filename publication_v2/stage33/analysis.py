"""Paired statistical summaries for experiment-matrix results (synthetic only).

Unit of analysis = scenario (seed x forecast x volatility); controllers are
paired within a scenario. Reports per-controller totals and, for prespecified
contrasts, the mean paired difference with a seeded percentile-bootstrap 95% CI
and a two-sided Wilcoxon signed-rank p-value (descriptive on development seeds).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
from statistics import mean

from scipy.stats import wilcoxon

METRICS = ('total_ramp_exceedance_kw', 'ramp_violations', 'total_throughput_kwh')
CONTRASTS = (('stochastic', 'uncontrolled'), ('stochastic', 'adaptive'), ('stochastic', 'fixed_margin'),
             ('stochastic', 'deterministic'), ('stochastic', 'stochastic_no_gate'),
             ('stochastic', 'stochastic_terminal'), ('stochastic', 'point_band_gate'))


def bootstrap_ci(values, *, draws=10000, seed=20261114):
    rng = random.Random(seed)
    n = len(values)
    stats = sorted(mean(rng.choices(values, k=n)) for _ in range(draws))
    return stats[int(.025 * draws)], stats[int(.975 * draws) - 1]


def paired(results, left, right, metric, group):
    index = {(r['scenario'], r['controller']): r for r in results if r['forecast'] == group}
    scenarios = sorted({s for s, _ in index})
    diffs = [index[(s, left)]['metrics'][metric] - index[(s, right)]['metrics'][metric]
             for s in scenarios if (s, left) in index and (s, right) in index]
    if not diffs:
        return None
    nonzero = [d for d in diffs if d != 0]
    p = wilcoxon(nonzero).pvalue if len(nonzero) >= 2 else None
    low, high = bootstrap_ci(diffs)
    return {'n': len(diffs), 'mean_difference': mean(diffs), 'ci95': [low, high],
            'wilcoxon_p': None if p is None else float(p),
            'left_better': sum(d < 0 for d in diffs), 'ties': len(diffs) - len(nonzero)}


def summarise(results):
    groups = sorted({r['forecast'] for r in results}, key=lambda g: [r['forecast'] for r in results].index(g))
    controllers = sorted({r['controller'] for r in results}, key=lambda c: [r['controller'] for r in results].index(c))
    out = {}
    for g in groups:
        rows = [r for r in results if r['forecast'] == g]
        totals = {c: {m: sum(r['metrics'][m] for r in rows if r['controller'] == c) for m in METRICS}
                  for c in controllers}
        diag = [r['forecast_diagnostics'] for r in rows if r['controller'] == controllers[0]]
        out[g] = {'scenarios': len(diag), 'totals': totals,
                  'mae30_kw': mean(d['per_horizon']['30']['mae_kw'] for d in diag),
                  'marginal_coverage': mean(mean(v['empirical_coverage'] for v in d['per_horizon'].values()) for d in diag),
                  'joint_coverage': mean(d['joint_six_horizon_coverage'] for d in diag),
                  'contrasts': {f'{a}-{b}': {m: paired(results, a, b, m, g) for m in METRICS}
                                for a, b in CONTRASTS if a in controllers and b in controllers}}
    return out


def render(summary):
    lines = []
    for g, s in summary.items():
        lines.append(f"\n## {g}  (n={s['scenarios']}, MAE30={s['mae30_kw']:.0f} kW, "
                     f"marginal cov={s['marginal_coverage']:.2f}, joint={s['joint_coverage']:.2f})")
        lines.append(f"{'controller':20s} {'exceed kW':>10s} {'viol':>5s} {'thru kWh':>9s}")
        for c, t in s['totals'].items():
            lines.append(f"{c:20s} {t['total_ramp_exceedance_kw']:10.0f} {t['ramp_violations']:5d} {t['total_throughput_kwh']:9.0f}")
        for name, metrics in s['contrasts'].items():
            e, q = metrics['total_ramp_exceedance_kw'], metrics['total_throughput_kwh']
            fmt = lambda x: 'n/a' if x is None else f"{x['mean_difference']:+.0f} [{x['ci95'][0]:+.0f},{x['ci95'][1]:+.0f}]" + \
                ('' if x['wilcoxon_p'] is None else f" p={x['wilcoxon_p']:.3f}")
            lines.append(f"  {name:32s} d_exceed {fmt(e):34s} d_thru {fmt(q)}")
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('results', type=Path)
    args = parser.parse_args(argv)
    data = json.loads(args.results.read_text(encoding='utf-8'))
    print(f"study_role={data['study_role']}  git={data['environment']['git_head']}  dirty={data['environment']['git_dirty']}")
    print(render(summarise(data['results'])))


if __name__ == '__main__':
    main()
