"""Stage 4 publication figure: real-data (Kelmarsh 2023-2024) controller results.

Reads only the checksummed ``tests.json`` of a completed run. Panel (a): change in ramp
exceedance versus no battery, with week-block 95% CIs, per controller and real forecast.
Panel (b): exceedance reduction against battery throughput for the neighbour-turbine forecast.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

INK, MUTED, SURFACE = '#1f2328', '#59636e', '#fcfcfa'
FORECASTS = {'persistence': ('Persistence', '#9aa4ae'), 'lightgbm': ('LightGBM (Stage 2 features)', '#e8853d'),
             'lightgbm_spatial': ('LightGBM + neighbour turbines', '#2a78d6')}
CONTROLLERS = {'fixed_margin': 'Fixed-margin MPC', 'adaptive': 'Adaptive MPC', 'stochastic': 'Stochastic MPC',
               'stochastic_skill': 'Stochastic MPC + skill switch\n(proposed)', 'deterministic': 'Deterministic MPC',
               'heuristic': 'Heuristic'}
MARKERS = {'fixed_margin': 'P', 'adaptive': '^', 'stochastic': 's', 'stochastic_skill': 'o', 'deterministic': 'D',
           'heuristic': 'v'}


def figure(tests_path: Path, out: Path):
    rows = json.loads(tests_path.read_text(encoding='utf-8'))['descriptive']
    get = {(r['forecast'], r['controller']): r for r in rows}
    plt.rcParams.update({'font.size': 9, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'xtick.color': MUTED,
                         'ytick.color': MUTED, 'axes.spines.top': False, 'axes.spines.right': False,
                         'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE})
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={'width_ratios': [1.35, 1]})
    names = list(CONTROLLERS)
    width = .26
    for j, (forecast, (label, colour)) in enumerate(FORECASTS.items()):
        for i, c in enumerate(names):
            r = get[(forecast, c)]
            m, (lo, hi) = r['change_vs_uncontrolled_pct'], r['change_ci95_pct']
            y = i + (j - 1) * width
            ax.barh(y, m, width * .9, color=colour, label=label if i == 0 else None, zorder=2)
            ax.errorbar(m, y, xerr=[[m - lo], [hi - m]], color=INK, lw=.8, capsize=1.5, zorder=3)
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_yticks(range(len(names)), [CONTROLLERS[c] for c in names])
    ax.invert_yaxis()
    ax.set_xlabel('Change in ramp exceedance vs no battery (%)')
    ax.set_title('(a) Real forecasts, Kelmarsh 2023–2024', loc='left', fontsize=10, color=INK)
    perfect = get[('perfect', 'stochastic_skill')]['change_vs_uncontrolled_pct']
    ax.text(.02, .02, f'Perfect forecast (privileged): {perfect:.1f}% for the proposed controller',
            transform=ax.transAxes, fontsize=7.5, color=MUTED)
    ax.legend(loc='upper center', bbox_to_anchor=(.45, -.16), ncol=3, fontsize=7.5, frameon=False)
    for c in ('fixed_margin', 'adaptive', 'stochastic', 'stochastic_skill'):
        r = get[('lightgbm_spatial', c)]
        proposed = c == 'stochastic_skill'
        bx.scatter(r['throughput_kwh'], -r['change_vs_uncontrolled_pct'], s=90 if proposed else 55, marker=MARKERS[c],
                   color='#2a78d6' if proposed else 'none', edgecolors='#2a78d6' if proposed else INK, lw=1.3, zorder=3)
        bx.annotate(CONTROLLERS[c].replace('\n', ' '), (r['throughput_kwh'], -r['change_vs_uncontrolled_pct']),
                    textcoords='offset points', xytext=(6, -10 if c == 'adaptive' else 4), fontsize=7.5, color=INK)
    bx.set_xlim(0, 900)
    bx.set_ylim(0, 10)
    bx.set_xlabel('Battery throughput (kWh per 8-h episode)')
    bx.set_ylabel('Exceedance reduction (%)')
    bx.set_title('(b) Reduction vs battery use (neighbour forecast)', loc='left', fontsize=10, color=INK)
    bx.grid(color='#e6e6e3', lw=.6, zorder=0)
    fig.tight_layout()
    out.mkdir(parents=True, exist_ok=True)
    for ext in ('png', 'pdf'):
        fig.savefig(out / f'fig6_real_data.{ext}', dpi=300, bbox_inches='tight')
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('tests', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    figure(args.tests, args.out)


if __name__ == '__main__':
    main()
