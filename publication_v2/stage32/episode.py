"""Closed-loop synthetic episode: stream -> adapter -> unchanged Stage 3.1 MPC -> plant.

Order per interval i: issue packet at decision time -> adapter validation ->
controller decision sealed -> realised interval mean released -> plant update.
Rejected or missing packets reach the controller as ``None`` and therefore take
the Stage 3.1 zero-dispatch safety fallback; nothing is repaired or imputed.
Scoring reuses Stage 3.1 accounting so integrated and standalone results share
one metric definition. Synthetic-only: no dataset, fitted model or admission.
"""
from __future__ import annotations

from datetime import timedelta
import math

from publication_v2.protocol import HORIZONS
from publication_v2.stage31.battery import BatteryConfig, transition, grid_export, ramp_metrics
from publication_v2.stage31.controllers import CONTROLLERS, MPCConfig, decide
from publication_v2.stage31.evaluation import (TOLERANCE, canonical_sha256, jsonable,
                                               summarize_trace, validate_plan)
from .adapter import adapt_forecast
from .synthetic import START, STEP, ScenarioSpec, SyntheticStream, forcing

TAIL = 5  # prespecified scoring tail so every issued 60-minute target is realised


def _realised(spec, wind, index):
    value = forcing(spec, index) if wind is None else wind(index)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('Realised synthetic wind must be finite and nonnegative')
    return float(value)


def run_episode(spec: ScenarioSpec, controller: str, *, battery: BatteryConfig | None = None,
                config: MPCConfig | None = None, wind=None, policy=None,
                decider=None, decider_config=None):
    """Run one causal episode.

    ``decider`` optionally replaces the Stage 3.1 ``decide`` (same signature,
    called with ``decider_config``); scoring always uses ``config`` (an
    MPCConfig) so every controller is measured against one ramp definition.

    ``wind`` optionally replaces the realised outcome source (index -> kW) for
    counterfactual leakage tests; it is only ever called AFTER the decision for
    that interval is sealed, and the forecast stream only sees released values.
    """
    if not isinstance(spec, ScenarioSpec):
        raise ValueError('ScenarioSpec required')
    if decider is None and controller not in CONTROLLERS:
        raise ValueError('Unknown controller')
    battery = BatteryConfig(initial_soc=spec.initial_soc) if battery is None else battery
    config = MPCConfig() if config is None else config
    if decider is None:
        decider, decider_config = decide, config
    stream = SyntheticStream(spec)
    energy = battery.initial_energy_kwh
    previous_grid = stream.initial_history_kw[-1]
    rows, plans, issued, adapter_log = [], [], [], []
    for index in range(spec.steps):
        decision_time = START + STEP * index
        packet = stream.packet(index)
        if packet is None:
            adaptation, bundle, fault = None, None, 'MISSING_PACKET'
        else:
            adaptation = adapt_forecast(packet, decision_time, stream.registry, policy=policy)
            bundle = adaptation.bundle if adaptation.accepted else None
            fault = None if adaptation.accepted else adaptation.rejection_code
        adapter_log.append({'decision_time': decision_time.isoformat(), 'accepted': bundle is not None,
                            'rejection_code': fault,
                            'packet_sha256': None if packet is None else canonical_sha256(packet)})
        action = decider(controller, bundle, decision_time, energy, previous_grid, battery, decider_config)
        plan_residual = validate_plan(action.plan, battery, energy, 1 if controller == 'heuristic' else config.horizon_steps)
        if action.plan is not None and (abs(action.charge_kw - action.plan['charge_kw'][0]) > TOLERANCE
                                        or abs(action.discharge_kw - action.plan['discharge_kw'][0]) > TOLERANCE):
            raise ValueError('Applied action is not the first planned move')
        if bundle is not None:
            issued.append((index, bundle))
        # The realised interval is released only after the action is sealed.
        actual = _realised(spec, wind, index)
        next_energy = transition(battery, energy, action.charge_kw, action.discharge_kw)
        grid = grid_export(actual, action.charge_kw, action.discharge_kw)
        ramp, excess = ramp_metrics(grid, previous_grid, config.ramp_limit_kw)
        rows.append({'decision_time': decision_time.isoformat(),
                     'interval_end': (decision_time + STEP).isoformat(),
                     'wind_kw': actual, 'previous_grid_kw': previous_grid, 'grid_kw': grid,
                     'charge_kw': action.charge_kw, 'discharge_kw': action.discharge_kw,
                     'energy_before_kwh': energy, 'energy_after_kwh': next_energy,
                     'ramp_kw': ramp, 'ramp_exceedance_kw': excess,
                     'forecast_sha256': canonical_sha256(jsonable(bundle)), 'forecast_fault': fault,
                     'status': action.status, 'solver_status': action.solver_status,
                     'optimization_failed': action.optimization_failed, 'fallback': action.fallback,
                     'fallback_reason': action.fallback_reason,
                     'computation_time_s': action.computation_time_s,
                     'plan_energy_residual_kwh': plan_residual})
        plans.append(jsonable(action.plan))
        stream.observe(index, actual)
        energy, previous_grid = next_energy, grid
    realised = {i: _realised(spec, wind, i) for i in range(spec.steps + TAIL)}
    for index in range(spec.steps, spec.steps + TAIL):
        stream.observe(index, realised[index])
    metrics = summarize_trace(rows, battery, config)
    if any(metrics[k] for k in ('soc_constraint_violations', 'power_constraint_violations',
                                'simultaneous_charge_discharge_events')):
        raise ValueError('A physical battery safety invariant failed')
    if (abs(metrics['energy_accounting_residual_kwh']) > TOLERANCE
            or metrics['maximum_energy_update_residual_kwh'] > TOLERANCE
            or metrics['maximum_power_balance_residual_kw'] > TOLERANCE):
        raise ValueError('Physical conservation failed')
    metrics.update(adapter_rejections=sum(not r['accepted'] for r in adapter_log))
    return {'data_kind': 'SYNTHETIC_ONLY', 'development_stage': 'STAGE32_SYNTHETIC_INTEGRATION',
            'scenario': spec.name, 'controller': controller, 'seed': spec.seed,
            'spec': jsonable(spec), 'scenario_sha256': stream.scenario_sha256,
            'wind_sha256': canonical_sha256([rows[i]['wind_kw'] for i in range(len(rows))]),
            'battery': jsonable(battery), 'mpc_config': jsonable(config), 'controller_config': jsonable(decider_config), 'metrics': metrics,
            'forecast_diagnostics': forecast_diagnostics(issued, realised),
            'adapter_log': adapter_log, 'rows': rows, 'plans': plans}


def forecast_diagnostics(issued, realised):
    """Per-horizon point error and EMPIRICAL marginal interval coverage.

    Descriptive only: a short dependent synthetic episode cannot certify the
    nominal level, and per-horizon marginal coverage is not joint trajectory
    coverage. Joint (all-six-horizons) coverage is reported separately.
    """
    per = {h: {'n': 0, 'abs_error': 0., 'covered': 0, 'width': 0.} for h in HORIZONS}
    joint_n = joint_hits = 0
    for index, bundle in issued:
        hits = []
        for j, h in enumerate(HORIZONS):
            actual = realised[index + j]  # target interval i+j ends at decision + h minutes
            if bundle.target_times[j] != START + STEP * (index + j + 1):
                raise ValueError('Forecast target does not map to realised interval')
            entry = per[h]
            entry['n'] += 1
            entry['abs_error'] += abs(bundle.point_kw[j] - actual)
            hit = bundle.lower_kw[j] - TOLERANCE <= actual <= bundle.upper_kw[j] + TOLERANCE
            entry['covered'] += hit
            entry['width'] += bundle.upper_kw[j] - bundle.lower_kw[j]
            hits.append(hit)
        joint_n += 1
        joint_hits += all(hits)
    alpha = issued[0][1].alpha if issued else None
    return {'nominal_marginal_coverage': None if alpha is None else 1 - alpha,
            'interpretation': 'descriptive synthetic diagnostics; not a coverage guarantee',
            'per_horizon': {str(h): {'n': e['n'],
                                     'mae_kw': e['abs_error'] / e['n'] if e['n'] else None,
                                     'empirical_coverage': e['covered'] / e['n'] if e['n'] else None,
                                     'mean_width_kw': e['width'] / e['n'] if e['n'] else None}
                            for h, e in per.items()},
            'joint_six_horizon_coverage': joint_hits / joint_n if joint_n else None,
            'joint_n': joint_n}


def run_comparison(spec: ScenarioSpec, *, controllers=CONTROLLERS, **kwargs):
    """All controllers on one identical, action-independent forecast stream."""
    runs = [run_episode(spec, name, **kwargs) for name in controllers]
    reference = [r['forecast_sha256'] for r in runs[0]['rows']]
    if any([r['forecast_sha256'] for r in run['rows']] != reference for run in runs):
        raise ValueError('Comparators did not receive identical forecasts')
    return runs
