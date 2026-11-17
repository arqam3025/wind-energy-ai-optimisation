"""Stage 4 analysis: paired contrasts on real data with dependence-aware inference.

Consecutive 8-hour episodes are serially dependent, so the unit of inference is the ISO WEEK.
- Paired episode differences are averaged within each week.
- Tests are one-sided Wilcoxon signed-rank tests on the weekly means (minus the margin).
- 95% CIs come from a moving-week block bootstrap: weeks resampled with replacement, seed fixed.

P denotes the proposed controller ``stochastic_skill`` (prespecified switch threshold 0.10).
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

SEED, BOOT = 20261117, 4000
PRIMARY = 'stochastic_skill'
EXC, THR = 'total_ramp_exceedance_kw', 'total_throughput_kwh'

# (id, forecast, metric, left, right, margin as a fraction of U or None, description)
TESTS = (
    ('R1', 'lightgbm_spatial', EXC, PRIMARY, 'uncontrolled', None, 'P reduces exceedance vs no battery'),
    ('R2', 'lightgbm_spatial', THR, PRIMARY, 'adaptive', None, 'P uses less throughput than adaptive MPC'),
    ('R3', 'persistence', EXC, PRIMARY, 'uncontrolled', .05, 'no material harm (margin 5% of U)'),
    ('R4', 'lightgbm', EXC, PRIMARY, 'uncontrolled', .05, 'no material harm (margin 5% of U)'),
)


def index(results):
    table = defaultdict(dict)
    for r in results:
        table[(r['forecast'], r['controller'])][r['start']] = r
    return table


def paired(table, forecast, metric, left, right):
    a, b = table[(forecast, left)], table[(forecast, right)]
    if set(a) != set(b):
        raise ValueError('unpaired episodes')
    starts = sorted(a)
    diff = np.array([a[s]['metrics'][metric] - b[s]['metrics'][metric] for s in starts])
    weeks = pd.to_datetime(starts, utc=True).tz_convert(None).to_period('W-SUN').astype(str)
    return diff, np.asarray(weeks)


def weekly(diff, weeks):
    frame = pd.DataFrame({'d': diff, 'w': weeks}).groupby('w')['d']
    return frame.mean().to_numpy(), frame.sum().to_numpy(), frame.size().to_numpy()


def block_ci(diff, weeks, seed=SEED, boot=BOOT):
    _, sums, counts = weekly(diff, weeks)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(sums), size=(boot, len(sums)))
    means = sums[idx].sum(1) / counts[idx].sum(1)
    return float(np.quantile(means, .025)), float(np.quantile(means, .975))


def ratio_ci(diff, base, weeks, seed=SEED, boot=BOOT):
    """Week-block bootstrap CI of the percentage change sum(diff)/sum(base) (bounded below by -100%)."""
    frame = pd.DataFrame({'d': diff, 'b': base, 'w': weeks}).groupby('w')[['d', 'b']].sum()
    d, b = frame['d'].to_numpy(), frame['b'].to_numpy()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(boot, len(d)))
    ratios = 100 * d[idx].sum(1) / b[idx].sum(1)
    return float(np.quantile(ratios, .025)), float(np.quantile(ratios, .975))


def holm(ps):
    order = np.argsort(ps)
    adjusted, running = np.empty(len(ps)), 0.
    for rank, i in enumerate(order):
        running = max(running, min(1., (len(ps) - rank) * ps[i]))
        adjusted[i] = running
    return adjusted


def primary_tests(results):
    table = index(results)
    rows = []
    for tid, forecast, metric, left, right, fraction, text in TESTS:
        diff, weeks = paired(table, forecast, metric, left, right)
        u = float(np.mean([r['metrics'][EXC] for r in table[(forecast, 'uncontrolled')].values()]))
        margin = 0. if fraction is None else fraction * u
        means, _, _ = weekly(diff, weeks)
        p = float(wilcoxon(means - margin, alternative='less', zero_method='zsplit').pvalue)
        lo, hi = block_ci(diff, weeks)
        rows.append({'test': tid, 'forecast': forecast, 'metric': metric, 'contrast': f'{left} - {right}',
                     'description': text, 'episodes': int(len(diff)), 'weeks': int(len(means)),
                     'U_kw': u, 'margin': margin, 'mean_difference': float(diff.mean()),
                     'ci95_block_bootstrap': [lo, hi], 'p_one_sided': p})
    for row, adjusted in zip(rows, holm([r['p_one_sided'] for r in rows])):
        row['p_holm'] = float(adjusted)
        row['supported'] = bool(adjusted < .05)
    return rows


def descriptive(results):
    table = index(results)
    out = []
    for (forecast, controller), runs in table.items():
        starts = sorted(runs)
        exc = np.array([runs[s]['metrics'][EXC] for s in starts])
        thr = np.array([runs[s]['metrics'][THR] for s in starts])
        base = np.array([table[(forecast, 'uncontrolled')][s]['metrics'][EXC] for s in starts])
        diff, weeks = exc - base, np.asarray(pd.to_datetime(starts, utc=True).tz_convert(None).to_period('W-SUN').astype(str))
        lo, hi = ratio_ci(diff, base, weeks)
        gated = sum(runs[s]['decision_status_counts'].get('skill_gated', 0) for s in starts)
        decisions = sum(sum(runs[s]['decision_status_counts'].values()) for s in starts)
        out.append({'forecast': forecast, 'controller': controller, 'episodes': len(starts),
                    'exceedance_kw': float(exc.mean()), 'throughput_kwh': float(thr.mean()),
                    'change_vs_uncontrolled_pct': float(100 * diff.mean() / base.mean()),
                    'change_ci95_pct': [lo, hi],
                    'reduction_per_mwh': float(-diff.mean() / thr.mean() * 1000) if thr.mean() > 0 else None,
                    'violations': float(np.mean([runs[s]['metrics']['ramp_violations'] for s in starts])),
                    'skill_gated_fraction': gated / decisions if decisions else 0.,
                    'safety_violations': int(sum(runs[s]['metrics'][k] for s in starts for k in (
                        'soc_constraint_violations', 'power_constraint_violations',
                        'simultaneous_charge_discharge_events'))),
                    'solver_failures': int(sum(runs[s]['metrics']['optimisation_failures'] for s in starts))})
    return out


def render(tests, rows, record):
    lines = ['# Stage 4 real-data results', '',
             f"Episodes: {record['episodes']} (paired across all forecasts and controllers). "
             'Inference unit: ISO week; Wilcoxon on weekly means; CIs from a week-block bootstrap.', '',
             '## Primary tests (Holm, one-sided, alpha 0.05)', '',
             '| Test | Forecast | Contrast | Margin | Mean diff [95% CI] | weeks | p (Holm) | Supported |',
             '|---|---|---|---|---|---|---|---|']
    for t in tests:
        lo, hi = t['ci95_block_bootstrap']
        lines.append(f"| {t['test']} | {t['forecast']} | {t['contrast']} ({t['metric'].split('_')[1]}) | {t['margin']:.1f} | "
                     f"{t['mean_difference']:+.1f} [{lo:+.1f}, {hi:+.1f}] | {t['weeks']} | {t['p_holm']:.2e} | "
                     f"{'yes' if t['supported'] else 'no'} |")
    lines += ['', '## All controllers', '',
              '| Forecast | Controller | Exceedance kW/ep | Change vs none [95% CI] | Throughput kWh/ep | kW per MWh | Idle (switch) | Safety viol. | Solver failures |',
              '|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        lo, hi = r['change_ci95_pct']
        eff = '' if r['reduction_per_mwh'] is None else f"{r['reduction_per_mwh']:.0f}"
        lines.append(f"| {r['forecast']} | {r['controller']} | {r['exceedance_kw']:.1f} | {r['change_vs_uncontrolled_pct']:+.1f}% "
                     f"[{lo:+.1f}, {hi:+.1f}] | {r['throughput_kwh']:.0f} | {eff} | {r['skill_gated_fraction']:.2f} | "
                     f"{r['safety_violations']} | {r['solver_failures']} |")
    return '\n'.join(lines) + '\n'


def forecast_skill(out: Path) -> dict:
    """Skill of each forecast over all decision times with complete forecasts and labels (secondary)."""
    data = np.load(out / 'series.npz')
    y = data['realised']
    n, h = len(y), 6
    labels = np.column_stack([np.r_[y[i + 1:], np.full(i + 1, np.nan)] for i in range(h)])
    result = {}
    names = [k[5:] for k in data.files if k.startswith('pred_')]
    common = np.isfinite(labels).all(1) & np.isfinite(y)
    for name in names:
        common &= np.isfinite(data[f'pred_{name}']).all(1)
    anchor = y[common][:, None]
    obs = labels[common]
    true_ramp = obs - np.column_stack([anchor[:, 0], obs[:, :-1]])
    big = np.abs(true_ramp) > 200
    for name in names:
        pred = data[f'pred_{name}'][common]
        pr = pred - np.column_stack([anchor[:, 0], pred[:, :-1]])
        corr = float(np.corrcoef(pr[big], true_ramp[big])[0, 1]) if np.std(pr[big]) > 0 else 0.
        result[name] = {'decisions': int(common.sum()), 'mae_kw': np.abs(pred - obs).mean(0).round(1).tolist(),
                        'skill_vs_persistence': float(1 - ((pred - obs) ** 2).sum() / ((anchor - obs) ** 2).sum()),
                        'ramp_correlation_abs_ramp_gt_200': corr}
    return result


def render_skill(skill: dict) -> str:
    lines = ['', '## Forecast skill on the evaluation period (secondary)', '',
             '| Forecast | Decisions | MAE 10â€¦60 min (kW) | Skill vs persistence | Ramp correlation |', '|---|---|---|---|---|']
    for name, s in skill.items():
        lines.append(f"| {name} | {s['decisions']} | {' '.join(f'{v:.0f}' for v in s['mae_kw'])} | "
                     f"{s['skill_vs_persistence']:+.3f} | {s['ramp_correlation_abs_ramp_gt_200']:+.2f} |")
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('results', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    record = json.loads(args.results.read_text(encoding='utf-8'))
    tests, rows = primary_tests(record['results']), descriptive(record['results'])
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'tests.json').write_bytes((json.dumps({'tests': tests, 'descriptive': rows}, indent=1) + '\n').encode())
    text = render(tests, rows, record)
    if (args.results.parent / 'series.npz').exists():
        skill = forecast_skill(args.results.parent)
        (args.out / 'forecast_skill.json').write_bytes((json.dumps(skill, indent=1) + chr(10)).encode())
        text += render_skill(skill)
    (args.out / 'REPORT.md').write_bytes(text.encode())
    print(text)


if __name__ == '__main__':
    main()
