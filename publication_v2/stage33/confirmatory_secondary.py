"""Descriptive secondary analyses of the confirmatory run (protocol Section 6, items 5 and 7).

Written after the run, from the frozen protocol's list of secondary analyses. It is descriptive
only: no hypothesis tests, no change to the primary analysis. Inputs are verified by SHA-256
through ``confirmatory.load``.

Outputs: volatility interaction (item 5), computation time (item 7), plus skill-switch activation
and safety/accounting counters for every controller.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from .confirmatory import load

KEY = ('uncontrolled', 'deterministic', 'adaptive', 'stochastic', 'stochastic_skill')
SAFETY = ('soc_constraint_violations', 'power_constraint_violations',
          'simultaneous_charge_discharge_events', 'grid_limit_violations', 'optimisation_failures',
          'adapter_rejections')


def secondary(results):
    by = defaultdict(list)
    for row in results:
        by[(row['forecast'], row['volatility'], row['controller'])].append(row)
    forecasts = list(dict.fromkeys(r['forecast'] for r in results))
    volatilities = sorted({r['volatility'] for r in results})
    controllers = list(dict.fromkeys(r['controller'] for r in results))

    volatility = {}
    for f in forecasts:
        for v in volatilities:
            volatility[f'{f}|{v}'] = {
                c: float(np.mean([r['metrics']['total_ramp_exceedance_kw'] for r in by[(f, v, c)]]))
                for c in KEY}

    timing, switch, safety = {}, {}, {}
    for c in controllers:
        rows = [r for r in results if r['controller'] == c]
        times = np.array([r['computation_time_s_mean'] for r in rows])
        timing[c] = {'median_ms': float(1e3 * np.median(times)), 'mean_ms': float(1e3 * times.mean()), 'p95_ms': float(1e3 * np.quantile(times, .95)),
                     'max_ms': float(1e3 * times.max())}
        safety[c] = {k: int(sum(r['metrics'][k] for r in rows)) for k in SAFETY}
        safety[c]['max_energy_residual_kwh'] = float(max(abs(r['metrics']['energy_accounting_residual_kwh'])
                                                         for r in rows))
        if c.startswith('stochastic_skill'):
            for f in forecasts:
                counts = defaultdict(int)
                for r in rows:
                    if r['forecast'] == f:
                        for status, n in r['decision_status_counts'].items():
                            counts[status] += n
                total = sum(counts.values())
                switch[f'{c}|{f}'] = round(counts.get('skill_gated', 0) / total, 4) if total else None
    return {'volatility_mean_exceedance_kw': volatility, 'computation_time': timing,
            'skill_gated_fraction_of_decisions': switch, 'safety_totals': safety}


def render(s):
    lines = ['# Stage 3.3 confirmatory: descriptive secondary analyses', '',
             'Descriptive only (protocol Section 6, items 5 and 7); no tests. Inputs verified by SHA-256.', '',
             '## Volatility interaction: mean exceedance per scenario (kW)', '',
             '| Forecast | Volatility | ' + ' | '.join(KEY) + ' |', '|---|---|' + '---|' * len(KEY)]
    for key, row in s['volatility_mean_exceedance_kw'].items():
        f, v = key.split('|')
        lines.append(f'| {f} | {v} | ' + ' | '.join(f'{row[c]:.0f}' for c in KEY) + ' |')
    gated = s['skill_gated_fraction_of_decisions']
    variants = list(dict.fromkeys(k.split('|')[0] for k in gated))
    forecasts = list(dict.fromkeys(k.split('|')[1] for k in gated))
    lines += ['', '## Skill switch: fraction of decisions gated to idle', '',
              '| Variant | ' + ' | '.join(forecasts) + ' |']
    lines.append('|---|' + '---|' * len(forecasts))
    for c in variants:
        lines.append(f'| {c} | ' + ' | '.join(f"{gated[f'{c}|{f}']:.2f}"
                                             for f in forecasts) + ' |')
    lines += ['', '## Computation time per decision (ms)', '', 'Wall-clock time per decision, averaged within each episode. Mean and max are inflated by operating-system standby during the run (deviation D2); use the median and p95.', '', '| Controller | median | p95 | mean | max |', '|---|---|---|---|---|']
    for c, t in s['computation_time'].items():
        lines.append(f"| {c} | {t['median_ms']:.1f} | {t['p95_ms']:.1f} | {t['mean_ms']:.1f} | {t['max_ms']:.1f} |")
    lines += ['', '## Safety and accounting totals (all scenarios)', '',
              '| Controller | ' + ' | '.join(SAFETY) + ' | max energy residual (kWh) |',
              '|---|' + '---|' * (len(SAFETY) + 1)]
    for c, t in s['safety_totals'].items():
        lines.append(f'| {c} | ' + ' | '.join(str(t[k]) for k in SAFETY) + f" | {t['max_energy_residual_kwh']:.2e} |")
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('run', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    _, results = load(args.run)
    s = secondary(results)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'secondary.json').write_bytes((json.dumps(s, indent=1) + '\n').encode())
    (args.out / 'SECONDARY.md').write_bytes(render(s).encode())
    print(render(s))


if __name__ == '__main__':
    main()
