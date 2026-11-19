"""Dispatch service core: one battery decision from a window of released history.

This module is the production entry point to the research controllers. It contains no control
logic of its own; it calls the exact functions used in the pre-registered studies:

1. the client's history (interval ends, realised power, issued six-horizon forecasts) becomes a
   ``Series`` on a contiguous 10-minute grid;
2. ``stage4.closed_loop.bundle_at`` builds the forecast bundle for the newest interval: rolling
   split-conformal intervals and the released skill score, from targets strictly before the
   decision;
3. the selected controller (same decider and configuration as in the studies) returns a decision;
4. ``stage31.evaluation.validate_plan`` checks the plan against the battery model before release.

If the history cannot support a valid bundle (too short, gaps, missing forecasts), the bundle is
``None`` and the controllers fail closed: the battery stays idle and the reason is reported.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import UTC, timedelta

import numpy as np
import pandas as pd

from publication_v2.stage4.closed_loop import STEP, Series, bundle_at
from publication_v2.stage5.experiment import REGISTRY
from publication_v2.stage5.switches import GradedConfig, weight
from publication_v2.stage31.battery import BatteryConfig, transition
from publication_v2.stage31.controllers import MPCConfig, decide
from publication_v2.stage31.evaluation import validate_plan
from publication_v2.stage33.controller import decide_stochastic, released_skill_score
from publication_v2.stage33.experiment import STOCHASTIC_VARIANTS

HORIZONS = 6
# bundle_at looks back at most 4 x 48 origins plus the six-step horizon; longer history is ignored.
MAX_LOOKBACK = 4 * 48 + HORIZONS + 2
MIN_HISTORY = 40
MAX_HISTORY = 2000


@dataclass(frozen=True)
class ControllerSpec:
    name: str
    description: str
    decider: object
    config: object
    one_step: bool
    role: str


def _spec(name, description, role):
    if name in REGISTRY:
        decider, config = REGISTRY[name]
    elif name in STOCHASTIC_VARIANTS:
        decider, config = decide_stochastic, STOCHASTIC_VARIANTS[name]
    else:
        decider, config = decide, MPCConfig()
    one_step = name == 'heuristic' or bool(getattr(decider, 'one_step', False))
    return ControllerSpec(name, description, decider, config, one_step, role)


CONTROLLERS = {
    s.name: s
    for s in (
        _spec('graded_mpc', 'Stochastic MPC with the plan scaled by the graded forecast-skill weight', 'proposed'),
        _spec(
            'stochastic_skill',
            'Stochastic MPC behind the binary forecast-skill switch (threshold 0.10)',
            'proposed (Stage 4)',
        ),
        _spec('stochastic', 'Scenario-based stochastic MPC (MILP), no skill switch', 'comparator'),
        _spec('adaptive', 'MPC with conformal box margins (worst-case per step)', 'comparator'),
        _spec('lowpass_fast', 'Forecast-driven low-pass filter with SOC feedback (industry-style)', 'baseline'),
        _spec('graded_lowpass', 'Low-pass filter scaled by the graded forecast-skill weight', 'baseline'),
        _spec('heuristic', 'One-step ramp-following rule', 'baseline'),
        _spec('uncontrolled', 'No battery action', 'reference'),
    )
}
DEFAULT_CONTROLLER = 'graded_mpc'


class HistoryError(ValueError):
    """The request history is malformed (not a contiguous, ordered 10-minute UTC grid)."""


def _times(values) -> pd.DatetimeIndex:
    times = pd.DatetimeIndex(pd.to_datetime(list(values), utc=False))
    if times.tz is None:
        raise HistoryError('interval_end values must carry a timezone (UTC recommended)')
    times = times.tz_convert('UTC').as_unit('ns')
    if len(times) < 2:
        return times
    steps = np.diff(times.asi8)
    if not (steps == STEP // timedelta(microseconds=1) * 1_000).all():
        raise HistoryError('history must be strictly increasing on a contiguous 10-minute grid with no gaps')
    return times


def make_series(interval_ends, realised_kw, forecasts_kw, name='api') -> Series:
    """Validate and align raw history arrays into a research ``Series``."""
    n = len(interval_ends)
    if not MIN_HISTORY <= n <= MAX_HISTORY:
        raise HistoryError(f'history must contain between {MIN_HISTORY} and {MAX_HISTORY} intervals, got {n}')
    if len(realised_kw) != n or len(forecasts_kw) != n:
        raise HistoryError('interval_end, realised_kw and forecast_kw must have the same length')
    times = _times(interval_ends)
    realised = np.array([np.nan if v is None else float(v) for v in realised_kw], dtype=float)
    predictions = np.full((n, HORIZONS), np.nan)
    for i, row in enumerate(forecasts_kw):
        if row is None:
            continue
        if len(row) != HORIZONS:
            raise HistoryError(f'forecast_kw rows must have {HORIZONS} values (10..60 min)')
        predictions[i] = [np.nan if v is None else float(v) for v in row]
    if np.isinf(realised).any() or np.isinf(predictions).any():
        raise HistoryError('infinite values are not allowed')
    keep = slice(max(0, n - MAX_LOOKBACK), n)  # identical bundle, less work
    return Series(times[keep], realised[keep], predictions[keep], name)


def dispatch(
    series: Series,
    energy_kwh: float,
    previous_grid_kw: float,
    controller: str = DEFAULT_CONTROLLER,
    battery: BatteryConfig | None = None,
) -> dict:
    """Decide the battery action for the newest interval of ``series`` (decision time = its end)."""
    if controller not in CONTROLLERS:
        raise KeyError(f'unknown controller {controller!r}; choose one of {sorted(CONTROLLERS)}')
    battery = BatteryConfig() if battery is None else battery
    lo, hi = battery.capacity_kwh * battery.min_soc, battery.capacity_kwh * battery.max_soc
    if not (math.isfinite(energy_kwh) and lo - 1e-6 <= energy_kwh <= hi + 1e-6):
        raise ValueError(f'battery_energy_kwh must be within the SOC window [{lo:.0f}, {hi:.0f}] kWh')
    if not math.isfinite(previous_grid_kw):
        raise ValueError('previous_grid_kw must be finite')
    spec = CONTROLLERS[controller]
    k = len(series.times) - 1
    decision_time = series.times[k].to_pydatetime()
    started = time.perf_counter()
    bundle = bundle_at(series, k)
    action = spec.decider(controller, bundle, decision_time, energy_kwh, previous_grid_kw, battery, spec.config)
    validate_plan(action.plan, battery, energy_kwh, 1 if spec.one_step else MPCConfig().horizon_steps)
    elapsed_ms = (time.perf_counter() - started) * 1000
    skill = released_skill_score(bundle) if bundle is not None else None
    graded = isinstance(spec.config, GradedConfig)
    plan = action.plan or {}
    return {
        'decision_time': decision_time.astimezone(UTC).isoformat(),
        'controller': controller,
        'charge_kw': float(action.charge_kw),
        'discharge_kw': float(action.discharge_kw),
        'net_battery_kw': float(action.discharge_kw - action.charge_kw),
        'energy_after_kwh': float(transition(battery, energy_kwh, action.charge_kw, action.discharge_kw)),
        'forecast_available': bundle is not None,
        'skill_score': skill,
        'skill_weight': (weight(skill, spec.config) if bundle is not None else 0.0) if graded else None,
        'forecast_kw': list(bundle.point_kw) if bundle is not None else None,
        'interval_lower_kw': list(bundle.lower_kw) if bundle is not None else None,
        'interval_upper_kw': list(bundle.upper_kw) if bundle is not None else None,
        'status': action.status,
        'solver_status': action.solver_status,
        'fallback': bool(action.fallback),
        'optimization_failed': bool(action.optimization_failed),
        'reason': action.fallback_reason or action.solver_message or None,
        'computation_ms': elapsed_ms,
        'plan': {key: [float(v) for v in plan[key]] for key in ('charge_kw', 'discharge_kw', 'energy_kwh') if key in plan},
    }
