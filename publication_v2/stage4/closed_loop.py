"""Closed-loop battery ramp control on real Kelmarsh data (Stage 4).

The Stage 3.1 and Stage 3.3 controllers, battery model and scoring are reused unchanged. Only the
source of forecasts and realised power changes:

* forecasts come from a model fitted on earlier years (``fit_year_max``) and applied to causal
  features (``features.py``);
* conformal intervals are rolling split-conformal: the last ``WINDOW`` released absolute residuals
  per horizon, using the finite-sample rank ceil((n+1)(1-alpha)), the same rule as Stage 2/3.2;
* the released skill score uses the same released residual pairs:
  SS = 1 - sum(forecast error^2) / sum(persistence error^2), pooled over horizons, where the
  persistence anchor is the released value at the origin (as in ``stage32.adapter.released_skill``).

Order per decision d: build the bundle from data whose interval ends at or before d, seal the
action, then release the realised interval ending at d + 10 min. Episodes with any missing input
are skipped and counted, never imputed.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd

from publication_v2.protocol import HORIZONS
from publication_v2.stage31.battery import BatteryConfig, transition, grid_export, ramp_metrics
from publication_v2.stage31.controllers import MPCConfig, decide
from publication_v2.stage31.evaluation import TOLERANCE, summarize_trace, validate_plan
from publication_v2.stage31.forecast import ForecastBundle
from publication_v2.stage33.controller import decide_stochastic
from publication_v2.stage33.experiment import STOCHASTIC_VARIANTS

ALPHA, WINDOW, MIN_SAMPLES = .1, 48, 30
STEPS, TAIL = 48, 6
H = len(HORIZONS)
STEP = timedelta(minutes=10)
CONTROLLERS = ('uncontrolled', 'heuristic', 'deterministic', 'fixed_margin', 'adaptive',
               'stochastic', 'stochastic_skill')


@dataclass(frozen=True)
class Series:
    """Aligned arrays on one continuous interval-end grid."""
    times: pd.DatetimeIndex     # interval ends
    realised: np.ndarray        # y at each interval end (NaN if missing)
    predictions: np.ndarray     # (n, 6) forecast issued at each time (NaN if features missing)
    name: str


def _rank_quantile(scores, alpha=ALPHA):
    rank = math.ceil((len(scores) + 1) * (1 - alpha))
    if rank > len(scores):
        return None
    return float(np.sort(scores)[rank - 1])


def bundle_at(series: Series, k: int):
    """ForecastBundle for decision index k (time = series.times[k]), or None if inputs are missing."""
    point = series.predictions[k]
    if not np.isfinite(point).all():
        return None
    decision = series.times[k].to_pydatetime()
    y = series.realised
    lowers, uppers, newest, f_sq, p_sq, pairs = [], [], [], 0., 0., 0
    per = {}
    for i, h in enumerate(HORIZONS):
        # Origins j whose target (index j + i + 1) ends strictly before decision k (the Stage 3.1
        # validator and the Stage 3.2 adapter both require target < decision for calibration).
        last = k - (i + 1) - 1
        lo = max(0, last - 4 * WINDOW)
        js = np.arange(lo, last + 1)
        obs, pred, anchor = y[js + i + 1], series.predictions[js, i], y[js]
        ok = np.isfinite(obs) & np.isfinite(pred) & np.isfinite(anchor)
        js, obs, pred, anchor = js[ok][-WINDOW:], obs[ok][-WINDOW:], pred[ok][-WINDOW:], anchor[ok][-WINDOW:]
        if len(js) < MIN_SAMPLES:
            return None
        q = _rank_quantile(np.abs(obs - pred))
        if q is None:
            return None
        p = float(max(0., point[i]))
        lowers.append(max(0., p - q))
        uppers.append(p + q)
        newest.append(series.times[js[-1] + i + 1].to_pydatetime())
        fs, ps = float(((pred - obs) ** 2).sum()), float(((anchor - obs) ** 2).sum())
        per[str(h)] = {'n': int(len(js)), 'mse_forecast': fs / len(js), 'mse_persistence': ps / len(js)}
        f_sq, p_sq, pairs = f_sq + fs, p_sq + ps, pairs + len(js)
    score = None if p_sq <= 0 else 1. - f_sq / p_sq
    provenance = json.dumps({'source': f'KELMARSH_REAL_{series.name}', 'released_skill': {
        'reference': 'persistence (released value at origin)', 'pairs': pairs,
        'pooled_skill_score': score, 'per_horizon': per}}, sort_keys=True)
    points = tuple(float(max(0., v)) for v in point)
    bundle = ForecastBundle(issue_time=decision, point_kw=points, lower_kw=tuple(lowers), upper_kw=tuple(uppers),
                            alpha=ALPHA, provenance=provenance, available_at=decision,
                            target_times=tuple(decision + STEP * (i + 1) for i in range(H)),
                            model_available_at=decision, calibration_newest_target_times=tuple(newest),
                            calibration_available_ats=tuple(newest), uncertainty_kind='CONFORMAL_MARGINAL')
    bundle.validate(decision)
    return bundle


def eligible(series: Series, k0: int) -> bool:
    """All realised values for the episode and its scoring tail exist, and every bundle can be built."""
    y = series.realised[k0:k0 + STEPS + TAIL + 1]
    if len(y) < STEPS + TAIL + 1 or not np.isfinite(y).all():
        return False
    return all(bundle_at(series, k) is not None for k in range(k0, k0 + STEPS))


def run_episode(series: Series, k0: int, controller: str, *, battery: BatteryConfig | None = None,
                config: MPCConfig | None = None):
    battery = BatteryConfig() if battery is None else battery
    config = MPCConfig() if config is None else config
    if controller in STOCHASTIC_VARIANTS:
        decider, decider_config = decide_stochastic, STOCHASTIC_VARIANTS[controller]
    else:
        decider, decider_config = decide, config
    energy = battery.initial_energy_kwh
    previous_grid = float(series.realised[k0])
    rows, statuses = [], {}
    for k in range(k0, k0 + STEPS):
        decision = series.times[k].to_pydatetime()
        bundle = bundle_at(series, k)
        action = decider(controller, bundle, decision, energy, previous_grid, battery, decider_config)
        plan_residual = validate_plan(action.plan, battery, energy, 1 if controller == 'heuristic' else config.horizon_steps)
        actual = float(series.realised[k + 1])  # released only after the action is sealed
        next_energy = transition(battery, energy, action.charge_kw, action.discharge_kw)
        grid = grid_export(actual, action.charge_kw, action.discharge_kw)
        ramp, excess = ramp_metrics(grid, previous_grid, config.ramp_limit_kw)
        rows.append({'decision_time': decision.isoformat(), 'interval_end': (decision + STEP).isoformat(),
                     'wind_kw': actual, 'previous_grid_kw': previous_grid, 'grid_kw': grid,
                     'charge_kw': action.charge_kw, 'discharge_kw': action.discharge_kw,
                     'energy_before_kwh': energy, 'energy_after_kwh': next_energy,
                     'ramp_kw': ramp, 'ramp_exceedance_kw': excess, 'forecast_fault': None if bundle else 'MISSING',
                     'status': action.status, 'solver_status': action.solver_status,
                     'optimization_failed': action.optimization_failed, 'fallback': action.fallback,
                     'fallback_reason': action.fallback_reason, 'computation_time_s': action.computation_time_s,
                     'plan_energy_residual_kwh': plan_residual})
        statuses[action.status] = statuses.get(action.status, 0) + 1
        energy, previous_grid = next_energy, grid
    metrics = summarize_trace(rows, battery, config)
    if any(metrics[k] for k in ('soc_constraint_violations', 'power_constraint_violations',
                                'simultaneous_charge_discharge_events')):
        raise ValueError('A physical battery safety invariant failed')
    if abs(metrics['energy_accounting_residual_kwh']) > TOLERANCE:
        raise ValueError('Physical conservation failed')
    return {'start': series.times[k0].isoformat(), 'forecast': series.name, 'controller': controller,
            'metrics': metrics, 'decision_status_counts': statuses,
            'computation_time_s_median': float(np.median([r['computation_time_s'] for r in rows]))}
