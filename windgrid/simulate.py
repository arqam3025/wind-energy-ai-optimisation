"""Closed-loop replay through the dispatch service, on the bundled sample or any ``Series``.

Each step calls ``service.dispatch`` with only the history a real client would have at that
moment, applies the action to the battery model, then reveals the next realised interval. The
scoring uses the research metric code, so a replay reproduces ``stage4.closed_loop.run_episode``
exactly (a test checks this).
"""

from __future__ import annotations

from functools import cache, lru_cache
from importlib import resources

import numpy as np
import pandas as pd

from publication_v2.stage4.closed_loop import STEPS, Series, eligible
from publication_v2.stage31.battery import BatteryConfig, grid_export, ramp_metrics, transition
from publication_v2.stage31.controllers import MPCConfig
from publication_v2.stage31.evaluation import summarize_trace

from . import service

SAMPLE_FORECASTS = ('lightgbm_spatial', 'persistence')
FORECAST_LABELS = {'lightgbm_spatial': 'LightGBM + neighbour turbines', 'persistence': 'Persistence (no skill)'}


@lru_cache(maxsize=1)
def load_sample() -> dict:
    """The bundled Penmanshiel February 2022 sample as research ``Series`` objects, by forecast."""
    with resources.files('windgrid.data').joinpath('penmanshiel_2022_sample.npz').open('rb') as handle:
        data = np.load(handle)
        times = pd.DatetimeIndex(pd.to_datetime(data['times'], unit='ns', utc=True))
        realised = data['realised'].copy()
        return {name: Series(times, realised, data[f'pred_{name}'].copy(), name) for name in SAMPLE_FORECASTS}


def episode_starts(series: Series) -> list[int]:
    """Eligible 8-hour episode starts (00:00, 08:00, 16:00 UTC), as in the studies."""
    return [k for k, t in enumerate(series.times) if t.minute == 0 and t.hour in (0, 8, 16) and eligible(series, k)]


@cache
def sample_episode_starts(forecast: str) -> tuple[int, ...]:
    """Eligible episode starts of the bundled sample, cached per forecast."""
    return tuple(episode_starts(load_sample()[forecast]))


def replay(
    series: Series, k0: int, controller: str = service.DEFAULT_CONTROLLER, battery: BatteryConfig | None = None
) -> dict:
    """One 8-hour episode driven decision-by-decision through the service."""
    battery = BatteryConfig() if battery is None else battery
    config = MPCConfig()
    energy, previous_grid = battery.initial_energy_kwh, float(series.realised[k0])
    rows = []
    for k in range(k0, k0 + STEPS):
        lo = max(0, k + 1 - service.MAX_LOOKBACK)
        window = Series(series.times[lo : k + 1], series.realised[lo : k + 1], series.predictions[lo : k + 1], series.name)
        decision = service.dispatch(window, energy, previous_grid, controller, battery)
        charge, discharge = decision['charge_kw'], decision['discharge_kw']
        actual = float(series.realised[k + 1])  # revealed only after the decision
        next_energy = transition(battery, energy, charge, discharge)
        grid = grid_export(actual, charge, discharge)
        ramp, excess = ramp_metrics(grid, previous_grid, config.ramp_limit_kw)
        rows.append(
            {
                'decision_time': decision['decision_time'],
                'wind_kw': actual,
                'previous_grid_kw': previous_grid,
                'grid_kw': grid,
                'charge_kw': charge,
                'discharge_kw': discharge,
                'energy_before_kwh': energy,
                'energy_after_kwh': next_energy,
                'ramp_kw': ramp,
                'ramp_exceedance_kw': excess,
                'skill_score': decision['skill_score'],
                'skill_weight': decision['skill_weight'],
                'status': decision['status'],
                'computation_ms': decision['computation_ms'],
                'computation_time_s': decision['computation_ms'] / 1000,
                'fallback': decision['fallback'],
                'optimization_failed': decision['optimization_failed'],
                'forecast_fault': None if decision['forecast_available'] else 'MISSING',
            }
        )
        energy, previous_grid = next_energy, grid
    return {
        'start': series.times[k0].isoformat(),
        'forecast': series.name,
        'controller': controller,
        'metrics': summarize_trace(rows, battery, config),
        'trace': rows,
    }


def compare(
    controllers=tuple(service.CONTROLLERS), forecast: str = 'lightgbm_spatial', limit: int | None = None
) -> pd.DataFrame:
    """Every listed controller on the same sample episodes; one row per controller."""
    series = load_sample()[forecast]
    starts = sample_episode_starts(forecast)[:limit]
    totals = []
    for controller in controllers:
        runs = [replay(series, k0, controller)['metrics'] for k0 in starts]
        totals.append(
            {
                'controller': controller,
                'episodes': len(runs),
                'ramp_exceedance_kw': float(np.mean([m['total_ramp_exceedance_kw'] for m in runs])),
                'ramp_violations': float(np.mean([m['ramp_violations'] for m in runs])),
                'throughput_kwh': float(np.mean([m['total_throughput_kwh'] for m in runs])),
            }
        )
    table = pd.DataFrame(totals).set_index('controller')
    base = table.loc['uncontrolled', 'ramp_exceedance_kw'] if 'uncontrolled' in table.index else np.nan
    table['change_vs_uncontrolled_pct'] = 100 * (table['ramp_exceedance_kw'] / base - 1)
    return table
