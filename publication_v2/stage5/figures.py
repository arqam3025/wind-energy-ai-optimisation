"""Stage 5 publication figure: second-site (Penmanshiel) efficiency of the graded switch.

Reads only tracked ``tests.json`` summaries.
Panel (a): sealed 2023–2024, neighbour forecast; exceedance reduction (week-block 95% CI) against
battery throughput for every controller.
Panel (b): the same axes; binary switch P -> graded switch G in each Penmanshiel period
(2021 development, 2022 validation, 2023–2024 sealed).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

from publication_v2.stage4.figures import INK, MUTED, SURFACE  # noqa: E402

BLUE, ORANGE, GRID = '#2a78d6', '#e8853d', '#e6e6e3'
RESULTS = Path(__file__).resolve().parent / 'results'
PERIODS = (('2021 development', 'penmanshiel_dev_2021/tests.json', '#9aa4ae', (-9, -3)),
           ('2022 validation', 'penmanshiel_validation_2022/tests.json', '#59636e', (7, -3)),
           ('2023–24 sealed', 'penmanshiel_sealed/run_record/tests.json', INK, (7, -3)))
# controller -> (label, marker, filled, label offset in points)
CONTROLLERS = {
    'heuristic': ('Heuristic', 'v', False, (6, -3)),
    'adaptive': ('Adaptive MPC', '^', False, (-30, 8)),
    'stochastic': ('Stochastic MPC', 's', False, (6, 4)),
    'stochastic_skill': ('P: binary switch', 'o', False, (8, -12)),
    'graded_mpc': ('G: graded switch'+chr(10)+'(proposed)', 'o', True, (7, 14)),
    'lowpass_fast': ('Low-pass filter', 'D', False, (-9, 2)),
    'graded_lowpass': ('Graded'+chr(10)+'low-pass', 'D', True, (-8, -3)),
}


def _rows(path: Path):
    return {(r['forecast'], r['controller']): r for r in json.loads(path.read_text(encoding='utf-8'))['descriptive']}


def figure(results: Path, out: Path):
    plt.rcParams.update({'font.size': 9, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'xtick.color': MUTED,
                         'ytick.color': MUTED, 'axes.spines.top': False, 'axes.spines.right': False,
                         'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE})
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={'width_ratios': [1.25, 1]})
    sealed = _rows(results / PERIODS[-1][1])
    for c, (label, marker, filled, offset) in CONTROLLERS.items():
        r = sealed[('lightgbm_spatial', c)]
        x, y = r['throughput_kwh'], -r['change_vs_uncontrolled_pct']
        lo, hi = (-v for v in r['change_ci95_pct'][::-1])
        colour = BLUE if c in ('graded_mpc', 'stochastic_skill') else (ORANGE if 'lowpass' in c else INK)
        ax.errorbar(x, y, yerr=[[y - lo], [hi - y]], color=colour, lw=.9, capsize=2, zorder=2)
        ax.scatter(x, y, s=70 if c == 'graded_mpc' else 50, marker=marker, color=colour if filled else SURFACE,
                   edgecolors=colour, lw=1.4, zorder=3)
        ax.annotate(label, (x, y), textcoords='offset points', xytext=offset, fontsize=7.5, color=INK,
                    ha='right' if offset[0] < 0 else ('center' if offset[0] == 0 else 'left'))
    ax.set_xlim(0, 650)
    ax.set_ylim(0, 9)
    ax.set_xlabel('Battery throughput (kWh per 8-h episode)')
    ax.set_ylabel('Exceedance reduction vs no battery (%)')
    ax.set_title('(a) Penmanshiel sealed 2023–2024, neighbour forecast', loc='left', fontsize=10, color=INK)
    ax.grid(color=GRID, lw=.6, zorder=0)
    ax.text(.98, .03, 'Bars: week-block 95% CI. Blue: MPC with skill switch; orange: filters.',
            transform=ax.transAxes, fontsize=7, color=MUTED, ha='right')
    for label, rel, colour, offset in PERIODS:
        rows = _rows(results / rel)
        p, g = rows[('lightgbm_spatial', 'stochastic_skill')], rows[('lightgbm_spatial', 'graded_mpc')]
        px, py = p['throughput_kwh'], -p['change_vs_uncontrolled_pct']
        gx, gy = g['throughput_kwh'], -g['change_vs_uncontrolled_pct']
        bx.annotate('', (gx, gy), (px, py), arrowprops=dict(arrowstyle='->', color=colour, lw=1.4,
                                                            shrinkA=5, shrinkB=5))
        bx.scatter(px, py, s=50, marker='o', color=SURFACE, edgecolors=colour, lw=1.4, zorder=3)
        bx.scatter(gx, gy, s=60, marker='o', color=colour, edgecolors=colour, lw=1.4, zorder=3)
        anchor = (gx, gy) if offset[0] < 0 else (px, py)   # negative offset: label the graded end, to its left
        bx.annotate(label, anchor, textcoords='offset points', xytext=offset, fontsize=7.5, color=INK,
                    ha='right' if offset[0] < 0 else 'left')
    bx.set_xlim(0, 220)
    bx.set_ylim(2, 4.5)
    bx.set_xlabel('Battery throughput (kWh per 8-h episode)')
    bx.set_ylabel('Exceedance reduction vs no battery (%)')
    bx.set_title('(b) Binary (○) → graded (●) switch, each period', loc='left', fontsize=10, color=INK)
    bx.grid(color=GRID, lw=.6, zorder=0)
    fig.tight_layout()
    out.mkdir(parents=True, exist_ok=True)
    for ext in ('png', 'pdf'):
        fig.savefig(out / f'fig7_second_site.{ext}', dpi=300, bbox_inches='tight')
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--results', type=Path, default=RESULTS)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    figure(args.results, args.out)


if __name__ == '__main__':
    main()
