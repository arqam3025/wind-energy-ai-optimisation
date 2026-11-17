"""Economic view (Stage 5, post-hoc descriptive): battery cost versus ramp exceedance avoided.

There is no market price for "ramp exceedance avoided", so the result is a BREAK-EVEN PENALTY:
the ramp penalty (EUR per kW of exceedance) at which a controller's battery cost equals the value
of the exceedance it avoids. A lower break-even means a more cost-effective controller.

Cost per episode = throughput x degradation cost + conversion losses x energy price, where

    degradation cost per kWh throughput = capex / (2 x cycle life x depth of discharge)

The factor 2 is there because throughput counts both charge and discharge. All assumptions are
explicit parameters, reported with a low/central/high range, and need sources in the paper
[CITE: Li-ion capex and cycle life; wholesale energy price]. This is not a hypothesis test.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

EPISODES_PER_YEAR = 3 * 365


@dataclass(frozen=True)
class Assumptions:
    capex_eur_per_kwh: float = 300.     # battery pack capital cost
    cycle_life: float = 6000.           # full equivalent cycles to end of life
    depth_of_discharge: float = .8
    energy_price_eur_per_mwh: float = 60.

    @property
    def degradation_eur_per_kwh(self):
        return self.capex_eur_per_kwh / (2 * self.cycle_life * self.depth_of_discharge)


SCENARIOS = {'low cost': Assumptions(150., 8000., .8, 40.), 'central': Assumptions(),
             'high cost': Assumptions(450., 4000., .8, 100.)}


def table(results, scenarios=SCENARIOS):
    runs = defaultdict(dict)
    for r in results:
        runs[(r['forecast'], r['controller'])][r['start']] = r['metrics']
    rows = []
    for (forecast, controller), episodes in sorted(runs.items()):
        if controller == 'uncontrolled':
            continue
        base = runs[(forecast, 'uncontrolled')]
        starts = sorted(episodes)
        avoided = float(np.mean([base[s]['total_ramp_exceedance_kw'] - episodes[s]['total_ramp_exceedance_kw'] for s in starts]))
        avoided_violations = float(np.mean([base[s]['ramp_violations'] - episodes[s]['ramp_violations'] for s in starts]))
        throughput = float(np.mean([episodes[s]['total_throughput_kwh'] for s in starts]))
        losses = float(np.mean([episodes[s]['conversion_loss_kwh'] for s in starts]))
        row = {'forecast': forecast, 'controller': controller, 'exceedance_avoided_kw': avoided,
               'violations_avoided': avoided_violations, 'throughput_kwh': throughput, 'losses_kwh': losses}
        for name, a in scenarios.items():
            cost = throughput * a.degradation_eur_per_kwh + losses * a.energy_price_eur_per_mwh / 1000
            row[f'cost_eur_{name}'] = cost
            row[f'annual_cost_eur_{name}'] = cost * EPISODES_PER_YEAR
            row[f'break_even_eur_per_kw_{name}'] = cost / avoided if avoided > 0 else None
        rows.append(row)
    return rows


def render(rows, title):
    lines = [f'# Economic view: {title}', '',
             'Post-hoc descriptive. Break-even = battery cost / exceedance avoided (EUR per kW of ramp exceedance). '
             'Lower is more cost-effective; "—" means no exceedance is avoided.', '',
             '| Assumption | Capex (EUR/kWh) | Cycle life | DoD | Energy (EUR/MWh) | Degradation (EUR/kWh throughput) |',
             '|---|---|---|---|---|---|']
    for name, a in SCENARIOS.items():
        lines.append(f'| {name} | {a.capex_eur_per_kwh:.0f} | {a.cycle_life:.0f} | {a.depth_of_discharge:.1f} | '
                     f'{a.energy_price_eur_per_mwh:.0f} | {a.degradation_eur_per_kwh:.4f} |')
    lines += ['', '| Forecast | Controller | Exceedance avoided (kW/episode) | Throughput (kWh) | Cost, central (EUR/episode) | '
              'Annual cost, central (EUR) | Break-even (EUR/kW), low / central / high |', '|---|---|---|---|---|---|---|']
    for r in rows:
        if r['forecast'] == 'perfect' and r['controller'] not in ('stochastic_skill', 'adaptive', 'stochastic'):
            continue
        be = ' / '.join('—' if r[f'break_even_eur_per_kw_{n}'] is None else f"{r[f'break_even_eur_per_kw_{n}']:.2f}"
                        for n in SCENARIOS)
        lines.append(f"| {r['forecast']} | {r['controller']} | {r['exceedance_avoided_kw']:.1f} | {r['throughput_kwh']:.0f} | "
                     f"{r['cost_eur_central']:.2f} | {r['annual_cost_eur_central']:,.0f} | {be} |")
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('results', type=Path, help='results JSON with a "results" list (Stage 4 or merged Stage 5)')
    parser.add_argument('--title', default='Kelmarsh')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    record = json.loads(args.results.read_text(encoding='utf-8'))
    rows = table(record['results'])
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'economics.json').write_bytes((json.dumps({'assumptions': {k: vars(v) for k, v in SCENARIOS.items()},
                                                            'rows': rows}, indent=1) + chr(10)).encode())
    text = render(rows, args.title)
    (args.out / 'ECONOMICS.md').write_bytes(text.encode())
    print(text)


if __name__ == '__main__':
    main()
