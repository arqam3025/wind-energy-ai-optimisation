"""Paper figures and tables from a confirmatory (or rehearsal) run directory.

Descriptive only: inferential results come from confirmatory_analysis.py. Every
figure uses paired scenario means with seeded bootstrap 95% CIs. Identity is
never colour-alone: each series also has a marker, line style and direct label.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

from .analysis import bootstrap_ci  # noqa: E402
from .confirmatory import GRADIENT_ONLY, SKILFUL, UNSKILLED, load  # noqa: E402

INK, MUTED, GRID, SURFACE = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
SERIES = {  # fixed categorical order (reference palette slots 1-4), never cycled
    'stochastic_skill': ('Stochastic MPC + skill switch (proposed)', '#2a78d6', 'o', '-'),
    'stochastic': ('Stochastic MPC, no switch', '#eb6834', 's', '--'),
    'adaptive': ('Adaptive MPC (Stage 3.1)', '#1baf7a', '^', '-.'),
    'deterministic': ('Deterministic MPC (Stage 3.1)', '#eda100', 'D', ':'),
}
LABELS = {'uncontrolled': 'No battery', 'deterministic': 'Deterministic MPC', 'fixed_margin': 'Fixed-margin MPC',
          'adaptive': 'Adaptive MPC', 'heuristic': 'Heuristic', 'stochastic': 'Stochastic MPC',
          'stochastic_skill': 'Stochastic + switch (proposed)', 'stochastic_skill00': 'Switch threshold 0',
          'stochastic_skill05': 'Switch threshold 0.05', 'stochastic_skill20': 'Switch threshold 0.20',
          'stochastic_increments': 'Independent increments', 'stochastic_no_gate': 'No do-no-harm gate',
          'stochastic_terminal': 'Terminal SOC target', 'point_band_gate': 'Point forecast only'}
FORECAST_LABELS = {'oracle25': 'Oracle σ=25', 'oracle50': 'Oracle σ=50', 'oracle100': 'Oracle σ=100',
                   'oracle150': 'Oracle σ=150', 'oracle200': 'Oracle σ=200', 'persistence': 'Persistence',
                   'mean_reversion': 'Mean reversion', 'skill_combo': 'Skill combination',
                   'damped_trend': 'Damped trend'}
EXC, THR = 'total_ramp_exceedance_kw', 'total_throughput_kwh'


def _style():
    plt.rcParams.update({'font.size': 9, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'xtick.color': MUTED,
                         'ytick.color': MUTED, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': .6,
                         'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': SURFACE,
                         'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE, 'legend.frameon': False,
                         'font.family': 'DejaVu Sans'})


def _table(results):
    table = {}
    for row in results:
        table.setdefault((row['forecast'], row['seed'], row['volatility']), {})[row['controller']] = row
    return table


def _diffs(table, forecast, controller, metric, reference='uncontrolled'):
    keys = sorted(k for k in table if k[0] == forecast)
    return [table[k][controller]['metrics'][metric] - table[k][reference]['metrics'][metric] for k in keys]


def _mean_ci(values):
    low, high = bootstrap_ci(values, draws=4000)
    return mean(values), low, high


def _ratio_ci(table, forecast, controller, metric=EXC, draws=4000, seed=20261114):
    """Relative change of means, mean(controller)/mean(uncontrolled) - 1, with a paired
    scenario bootstrap; bounded below by -100% by construction."""
    import random
    keys = sorted(k for k in table if k[0] == forecast)
    pairs = [(table[k][controller]['metrics'][metric], table[k]['uncontrolled']['metrics'][metric]) for k in keys]
    ratio = lambda sample: sum(p for p, _ in sample) / sum(u for _, u in sample) - 1
    rng = random.Random(seed)
    stats = sorted(ratio(rng.choices(pairs, k=len(pairs))) for _ in range(draws))
    return ratio(pairs), stats[int(.025 * draws)], stats[int(.975 * draws) - 1]


def _save(fig, out, name):
    for ext in ('png', 'pdf'):
        fig.savefig(out / f'{name}.{ext}', dpi=300, bbox_inches='tight')
    plt.close(fig)


def fig_break_even(table, results, out):
    """Exceedance change vs no battery (% of uncontrolled) against forecast error (MAE30)."""
    oracles = SKILFUL + GRADIENT_ONLY
    mae = {f: mean(r['forecast_diagnostics']['per_horizon']['30']['mae_kw'] for r in results
                   if r['forecast'] == f and r['controller'] == 'uncontrolled') for f in oracles}
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.axhline(0, color=MUTED, lw=1)
    ax.text(min(mae.values()), 3, 'no battery (0%)', color=MUTED, ha='left', va='bottom', fontsize=8)
    offsets = dict(zip(SERIES, (-4.5, -1.5, 1.5, 4.5)))  # small horizontal dodge so error bars do not overlap
    for controller, (label, colour, marker, style) in SERIES.items():
        xs, ys, lo, hi = [], [], [], []
        for f in oracles:
            m, l, h = _ratio_ci(table, f, controller)
            xs.append(mae[f] + offsets[controller]); ys.append(100 * m)
            lo.append(100 * (m - l)); hi.append(100 * (h - m))
        ax.errorbar(xs, ys, yerr=[lo, hi], color=colour, lw=2, ls=style, marker=marker, ms=6, mec=SURFACE,
                    mew=1.2, elinewidth=1, capsize=2, label=label)
    ax.set_xlabel('Forecast error, 30-minute MAE (kW)  [oracle σ = 25, 50, 100, 150, 200 kW]')
    ax.set_ylabel('Change in ramp exceedance\nvs no battery (%)')
    ax.legend(loc='upper left', fontsize=8)
    ax.set_title('Battery benefit shrinks as forecast error grows', loc='left', color=INK, fontsize=10)
    _save(fig, out, 'fig1_break_even')


def fig_tradeoff(table, out):
    """Mean throughput vs mean exceedance per controller, one panel per skilful condition."""
    # Identity by marker shape (one accent colour for the proposed controller), so clustered points
    # never need colliding text labels.
    markers = {'heuristic': ('Heuristic', 'v'), 'deterministic': ('Deterministic MPC', 'D'),
               'fixed_margin': ('Fixed-margin MPC', 'P'), 'adaptive': ('Adaptive MPC (Stage 3.1)', '^'),
               'stochastic': ('Stochastic MPC, no switch', 's'),
               'stochastic_skill': ('Stochastic MPC + skill switch (proposed)', 'o')}
    fig, axes = plt.subplots(1, len(SKILFUL), figsize=(9.6, 3.9), sharey=True)
    for ax, f in zip(axes, SKILFUL):
        keys = [k for k in table if k[0] == f]
        for c, (label, marker) in markers.items():
            x = mean(table[k][c]['metrics'][THR] for k in keys)
            y = mean(table[k][c]['metrics'][EXC] for k in keys)
            primary = c == 'stochastic_skill'
            # proposed drawn underneath (larger) so an identical comparator stays visible on top
            ax.plot(x, y, marker=marker, ms=11 if primary else 7, color='#2a78d6' if primary else MUTED,
                    mfc='#2a78d6' if primary else 'none', mec='#2a78d6' if primary else MUTED, mew=1.4,
                    ls='none', zorder=2 if primary else 3, label=label)
        ax.set_xlim(left=0)
        ax.set_title(FORECAST_LABELS[f], loc='left', fontsize=9, color=INK)
        ax.set_xlabel('Battery throughput (kWh / episode)')
    axes[0].set_ylabel('Ramp exceedance (kW / episode)')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', ncol=3, fontsize=8, bbox_to_anchor=(.5, -.02))
    fig.suptitle('Ramp exceedance vs battery throughput (lower-left is better)', x=.01, ha='left', fontsize=10)
    _save(fig, out, 'fig2_tradeoff')


def fig_no_harm(table, out, margin_fraction=.05):
    """Exceedance change vs no battery under forecasts without skill, with the H3 margin."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    width = .2
    for i, (controller, (label, colour, marker, _)) in enumerate(SERIES.items()):
        for j, f in enumerate(UNSKILLED):
            m, l, h = _mean_ci(_diffs(table, f, controller, EXC))
            x = j + (i - 1.5) * width
            ax.bar(x, m, width * .9, color=colour, label=label if j == 0 else None, zorder=2)
            ax.errorbar(x, m, yerr=[[m - l], [h - m]], color=INK, lw=1, capsize=2, zorder=3)
    for j, f in enumerate(UNSKILLED):
        margin = margin_fraction * mean(table[k]['uncontrolled']['metrics'][EXC] for k in table if k[0] == f)
        ax.hlines(margin, j - .45, j + .45, colors=INK, linestyles='--', lw=1)
    ax.axhline(0, color=MUTED, lw=1)
    ax.set_xticks(range(len(UNSKILLED)), [FORECAST_LABELS[f] for f in UNSKILLED])
    ax.set_ylabel('Change in ramp exceedance\nvs no battery (kW / episode)')
    ax.set_title('Forecasts without skill: harm relative to no battery (dashed = 5% no-harm margin)',
                 loc='left', fontsize=10)
    ax.legend(fontsize=7.5, ncol=2, loc='upper center', bbox_to_anchor=(.5, -.12))
    _save(fig, out, 'fig3_no_harm')


def fig_ablation(table, out):
    """Each variant minus the proposed controller, pooled over the skilful conditions."""
    variants = ['stochastic', 'stochastic_skill00', 'stochastic_skill05', 'stochastic_skill20', 'stochastic_no_gate',
                'stochastic_terminal', 'point_band_gate', 'stochastic_increments']
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4), sharey=True)
    for ax, metric, title in ((axes[0], EXC, 'Δ ramp exceedance (kW / episode)'),
                              (axes[1], THR, 'Δ battery throughput (kWh / episode)')):
        for i, v in enumerate(variants):
            diffs = []
            for f in SKILFUL:
                diffs += _diffs(table, f, v, metric, reference='stochastic_skill')
            m, l, h = _mean_ci(diffs)
            ax.barh(i, m, .6, color='#2a78d6', zorder=2)
            ax.errorbar(m, i, xerr=[[m - l], [h - m]], color=INK, lw=1, capsize=2, zorder=3)
        ax.axvline(0, color=MUTED, lw=1)
        ax.set_xlabel(title)
    axes[0].set_yticks(range(len(variants)), [LABELS[v] for v in variants])
    axes[0].invert_yaxis()
    fig.suptitle('Ablations: variant minus proposed controller (skilful forecasts; positive = worse)',
                 x=.01, ha='left', fontsize=10)
    _save(fig, out, 'fig4_ablation')


def fig_coverage(results, out):
    """Empirical marginal coverage per horizon and joint six-horizon coverage per forecaster."""
    forecasts = SKILFUL + GRADIENT_ONLY + UNSKILLED
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    horizons = ['10', '20', '30', '40', '50', '60']
    marginal = [mean(mean(r['forecast_diagnostics']['per_horizon'][h]['empirical_coverage'] for h in horizons)
                     for r in results if r['forecast'] == f and r['controller'] == 'uncontrolled') for f in forecasts]
    joint = [mean(r['forecast_diagnostics']['joint_six_horizon_coverage']
                  for r in results if r['forecast'] == f and r['controller'] == 'uncontrolled') for f in forecasts]
    xs = range(len(forecasts))
    ax.bar([x - .2 for x in xs], marginal, .38, color='#2a78d6', label='Marginal (mean over horizons)', zorder=2)
    ax.bar([x + .2 for x in xs], joint, .38, color='#eb6834', label='Joint (all six horizons)', zorder=2, hatch='//',
           edgecolor=SURFACE)
    ax.axhline(.9, color=INK, ls='--', lw=1)
    ax.text(len(forecasts) - .5, .905, 'nominal 0.90', ha='right', va='bottom', fontsize=8, color=INK)
    ax.set_xticks(list(xs), [FORECAST_LABELS[f] for f in forecasts], rotation=35, ha='right')
    ax.set_ylim(0, 1.05)
    ax.set_ylabel('Empirical coverage')
    ax.set_title('Conformal intervals: marginal coverage holds, joint coverage does not', loc='left', fontsize=10)
    ax.legend(fontsize=8, loc='lower left', ncol=2, bbox_to_anchor=(0, 1.0))
    ax.set_title('Conformal intervals: marginal coverage holds, joint coverage does not', loc='left',
                 fontsize=10, pad=24)
    _save(fig, out, 'fig5_coverage')


def summary_table(table, results, out):
    """Per-condition, per-controller means with bootstrap CIs (CSV and Markdown)."""
    rows = []
    for f in SKILFUL + GRADIENT_ONLY + UNSKILLED:
        keys = [k for k in table if k[0] == f]
        for c in LABELS:
            exc = [table[k][c]['metrics'][EXC] for k in keys]
            thr = [table[k][c]['metrics'][THR] for k in keys]
            viol = [table[k][c]['metrics']['ramp_violations'] for k in keys]
            em, el, eh = _mean_ci(exc)
            rows.append({'forecast': f, 'controller': c, 'n': len(keys), 'exceedance_mean_kw': round(em, 1),
                         'exceedance_ci_low': round(el, 1), 'exceedance_ci_high': round(eh, 1),
                         'throughput_mean_kwh': round(mean(thr), 1), 'violations_mean': round(mean(viol), 2)})
    with open(out / 'table_summary.csv', 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    lines = ['| Forecast | Controller | Exceedance kW/episode [95% CI] | Throughput kWh | Violations |',
             '|---|---|---|---|---|']
    for r in rows:
        lines.append(f"| {FORECAST_LABELS[r['forecast']]} | {LABELS[r['controller']]} | {r['exceedance_mean_kw']:.0f} "
                     f"[{r['exceedance_ci_low']:.0f}, {r['exceedance_ci_high']:.0f}] | {r['throughput_mean_kwh']:.0f} | "
                     f"{r['violations_mean']:.1f} |")
    (out / 'table_summary.md').write_text('\n'.join(lines), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    completed, results = load(args.run_dir)
    args.out.mkdir(parents=True, exist_ok=True)
    _style()
    table = _table(results)
    fig_break_even(table, results, args.out)
    fig_tradeoff(table, args.out)
    fig_no_harm(table, args.out)
    fig_ablation(table, args.out)
    fig_coverage(results, args.out)
    summary_table(table, results, args.out)
    (args.out / 'SOURCE.json').write_text(json.dumps({k: completed[k] for k in
        ('study_role', 'protocol_sha256', 'git_head')}, indent=1), encoding='utf-8')
    print('figures written to', args.out)


if __name__ == '__main__':
    main()
