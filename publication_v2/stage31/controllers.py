"""Synthetic research MPC. Interval envelopes are not joint-coverage guarantees.

All powers are AC-side kW; shared battery commands are open-loop within a plan.
The implemented risk cost is a SUM OF PER-STEP worst-box ramp envelopes, not
an exact worst-total-trajectory objective, CVaR, or a chance constraint.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from numbers import Real
from time import perf_counter
from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from .battery import BatteryConfig, PhysicalError, transition
from .forecast import ForecastBundle

CONTROLLERS = ('uncontrolled', 'deterministic', 'fixed_margin', 'adaptive', 'heuristic')
NUMERICAL_TOLERANCE = 1e-7


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise ValueError(f'{name} must be a finite real number')
    return float(value)


@dataclass(frozen=True)
class MPCConfig:
    horizon_steps: int = 6
    ramp_limit_kw: float = 200.0
    ramp_weight: float = 1.0
    throughput_weight: float = 0.05
    soc_margin_weight: float = 0.05
    uncertainty_weight: float = 0.5
    terminal_weight: float = 0.1
    fixed_margin_kw: float = 200.0
    soc_buffer_fraction: float = 0.05
    terminal_soc: float = 0.65
    solver_time_limit_s: float = 5.0
    solver_mip_rel_gap: float = 1e-8
    grid_min_kw: float | None = None
    grid_max_kw: float | None = None

    def __post_init__(self) -> None:
        if isinstance(self.horizon_steps, bool) or not isinstance(self.horizon_steps, int) or self.horizon_steps != 6:
            raise ValueError('This Stage 2-compatible implementation requires six horizon steps')
        for name in ('ramp_limit_kw', 'solver_time_limit_s'):
            if _number(getattr(self, name), name) <= 0:
                raise ValueError(f'{name} must be positive')
        for name in ('ramp_weight', 'throughput_weight', 'soc_margin_weight', 'uncertainty_weight',
                     'terminal_weight', 'fixed_margin_kw', 'soc_buffer_fraction', 'solver_mip_rel_gap'):
            if _number(getattr(self, name), name) < 0:
                raise ValueError(f'{name} must be nonnegative')
        if not any(getattr(self, n) > 0 for n in _WEIGHT_NAMES):
            raise ValueError('At least one objective weight must be positive')
        if not 0 <= _number(self.terminal_soc, 'terminal_soc') <= 1:
            raise ValueError('terminal_soc must be a fraction in [0,1]')
        for name in ('grid_min_kw', 'grid_max_kw'):
            if getattr(self, name) is not None:
                _number(getattr(self, name), name)
        if self.grid_min_kw is not None and self.grid_max_kw is not None and self.grid_min_kw > self.grid_max_kw:
            raise ValueError('grid_min_kw exceeds grid_max_kw')


_WEIGHT_NAMES = ('ramp_weight', 'throughput_weight', 'soc_margin_weight', 'uncertainty_weight', 'terminal_weight')


@dataclass(frozen=True)
class Decision:
    charge_kw: float
    discharge_kw: float
    controller: str
    status: str
    solver_status: int | None
    solver_message: str
    computation_time_s: float
    optimization_failed: bool
    fallback: bool
    fallback_reason: str | None
    plan: dict | None


def _context(battery: BatteryConfig, config: MPCConfig, energy: float,
             previous_grid: float, decision_time: datetime) -> None:
    transition(battery, energy, 0.0, 0.0)
    _number(previous_grid, 'previous_grid_kw')
    if not isinstance(decision_time, datetime) or decision_time.tzinfo is None or decision_time.utcoffset() is None:
        raise ValueError('decision_time must be timezone aware')
    if config.soc_buffer_fraction > (battery.max_soc - battery.min_soc) / 2:
        raise ValueError('SOC operating-margin buffer would invert the preferred band')
    if not battery.min_soc <= config.terminal_soc <= battery.max_soc:
        raise ValueError('terminal_soc must lie within the physical battery SOC limits')


def _fallback(controller: str, start: float, reason: str, *, optimization_failed: bool,
              solver_status: int | None = None, message: str = '') -> Decision:
    # Zero dispatch preserves every valid battery state. It does NOT certify
    # arbitrary external grid bounds when wind itself makes them infeasible.
    return Decision(0.0, 0.0, controller, 'fallback', solver_status, message,
                    perf_counter() - start, optimization_failed, True, reason, None)


def _forecast_arrays(controller: str, forecast: ForecastBundle, config: MPCConfig):
    point = np.asarray(forecast.point_kw, dtype=float)
    if controller == 'deterministic':
        lower, upper = point.copy(), point.copy()
    elif controller == 'fixed_margin':
        lower = np.maximum(0.0, point - config.fixed_margin_kw)
        upper = point + config.fixed_margin_kw
    else:
        lower = np.asarray(forecast.lower_kw, dtype=float)
        upper = np.asarray(forecast.upper_kw, dtype=float)
    return point, lower, upper


def _formulate(point, lower, upper, energy, previous_grid, battery, config):
    h = config.horizon_steps
    size = 8 * h + 1
    groups = {name: np.arange(i * h, (i + 1) * h) for i, name in enumerate(
        ('charge', 'discharge', 'energy', 'mode', 'nominal_excess', 'worst_excess', 'low_margin', 'high_margin'))}
    terminal = 8 * h
    c = np.zeros(size)
    lb = np.zeros(size)
    ub = np.full(size, np.inf)
    integrality = np.zeros(size, dtype=int)
    ub[groups['charge']] = battery.max_charge_kw
    ub[groups['discharge']] = battery.max_discharge_kw
    lb[groups['energy']] = battery.min_energy_kwh
    ub[groups['energy']] = battery.max_energy_kwh
    ub[groups['mode']] = 1.0
    integrality[groups['mode']] = 1
    usable = battery.usable_energy_kwh
    dt = battery.delta_t_hours
    c[groups['charge']] = c[groups['discharge']] = config.throughput_weight * dt / usable
    c[groups['nominal_excess']] = config.ramp_weight / (h * config.ramp_limit_kw)
    c[groups['worst_excess']] = config.uncertainty_weight / (h * config.ramp_limit_kw)
    c[groups['low_margin']] = c[groups['high_margin']] = config.soc_margin_weight / (h * usable)
    c[terminal] = config.terminal_weight / usable
    rows, lows, highs = [], [], []

    def add(coefficients, low=-np.inf, high=np.inf):
        row = np.zeros(size)
        for index, coefficient in coefficients.items():
            row[index] += coefficient
        rows.append(row)
        lows.append(low)
        highs.append(high)

    inner_low = battery.min_energy_kwh + config.soc_buffer_fraction * battery.capacity_kwh
    inner_high = battery.max_energy_kwh - config.soc_buffer_fraction * battery.capacity_kwh
    for t in range(h):
        charge, discharge, e, mode = (groups[k][t] for k in ('charge', 'discharge', 'energy', 'mode'))
        equation = {e: 1.0, charge: -battery.eta_charge * dt, discharge: dt / battery.eta_discharge}
        if t:
            equation[groups['energy'][t - 1]] = -1.0
            rhs = 0.0
        else:
            rhs = energy
        add(equation, rhs, rhs)
        add({charge: 1.0, mode: -battery.max_charge_kw}, high=0.0)
        add({discharge: 1.0, mode: battery.max_discharge_kw}, high=battery.max_discharge_kw)
        add({groups['low_margin'][t]: 1.0, e: 1.0}, low=inner_low)
        add({groups['high_margin'][t]: 1.0, e: -1.0}, low=-inner_high)
        net = {discharge: 1.0, charge: -1.0}
        add(net, -np.inf if config.grid_min_kw is None else config.grid_min_kw - lower[t],
            np.inf if config.grid_max_kw is None else config.grid_max_kw - upper[t])
        delta = dict(net)
        if t:
            delta[groups['discharge'][t - 1]] = -1.0
            delta[groups['charge'][t - 1]] = 1.0
            nominal_constant = point[t] - point[t - 1]
            up_constant = upper[t] - lower[t - 1]
            down_constant = upper[t - 1] - lower[t]
        else:
            nominal_constant = point[t] - previous_grid
            up_constant = upper[t] - previous_grid
            down_constant = previous_grid - lower[t]
        for variable, positive, negative in ((groups['nominal_excess'][t], nominal_constant, -nominal_constant),
                                              (groups['worst_excess'][t], up_constant, down_constant)):
            row = {index: -value for index, value in delta.items()}
            row[variable] = 1.0
            add(row, low=positive - config.ramp_limit_kw)
            row = dict(delta)
            row[variable] = 1.0
            add(row, low=negative - config.ramp_limit_kw)
    target = config.terminal_soc * battery.capacity_kwh
    add({terminal: 1.0, groups['energy'][-1]: -1.0}, low=-target)
    add({terminal: 1.0, groups['energy'][-1]: 1.0}, low=target)
    return c, integrality, Bounds(lb, ub), LinearConstraint(np.asarray(rows), lows, highs), groups


def _validate_solver_certificate(solution, objective, integrality, bounds, constraints, config):
    """Check the raw MILP incumbent and its reported optimality certificate.

    These are numerical acceptance checks, not an independent proof that HiGHS
    solved the MILP. A status flag alone does not establish a valid incumbent.
    Infinite formulation bounds are permitted; returned values must be finite.
    """
    primal_tolerance = 1e-5
    integer_tolerance = 1e-6
    gap_tolerance = 1e-9
    objective_relative_tolerance = 1e-5
    objective_absolute_tolerance = 1e-5
    if isinstance(solution.status, bool) or not isinstance(solution.status, (int, np.integer)) or solution.status != 0 or solution.success is not True:
        raise PhysicalError('Solver optimal termination metadata is invalid')
    x = np.asarray(solution.x, dtype=float)
    if x.shape != objective.shape or not np.isfinite(x).all():
        raise PhysicalError('Solver incumbent is not a complete finite vector')
    bound_violation = float(max(np.max(np.maximum(bounds.lb - x, 0.0)),
                                np.max(np.maximum(x - bounds.ub, 0.0))))
    activity = np.asarray(constraints.A @ x, dtype=float)
    if not np.isfinite(activity).all():
        raise PhysicalError('Solver constraint activity is nonfinite')
    constraint_violation = float(max(np.max(np.maximum(constraints.lb - activity, 0.0)),
                                     np.max(np.maximum(activity - constraints.ub, 0.0))))
    integer_values = x[np.asarray(integrality) != 0]
    integer_violation = float(np.max(np.abs(integer_values - np.round(integer_values)))) if integer_values.size else 0.0
    if bound_violation > primal_tolerance:
        raise PhysicalError('Solver incumbent violates original variable bounds')
    if constraint_violation > primal_tolerance:
        raise PhysicalError('Solver incumbent violates original linear constraints')
    if integer_violation > integer_tolerance:
        raise PhysicalError('Solver incumbent violates original integrality constraints')
    reported_objective = _number(solution.fun, 'solver objective')
    linear_objective = float(objective @ x)
    if not math.isfinite(linear_objective) or not math.isclose(linear_objective, reported_objective,
            rel_tol=objective_relative_tolerance, abs_tol=objective_absolute_tolerance):
        raise PhysicalError('Raw MILP objective does not agree with solver objective')
    gap = _number(solution.mip_gap, 'solver MIP relative gap')
    if gap < 0 or gap > config.solver_mip_rel_gap + gap_tolerance:
        raise PhysicalError('Solver MIP gap exceeds the requested optimality tolerance')
    dual = _number(solution.mip_dual_bound, 'solver MIP dual bound')
    absolute_tolerance = max(objective_absolute_tolerance,
                             objective_relative_tolerance * abs(reported_objective))
    if dual > reported_objective + absolute_tolerance:
        raise PhysicalError('Solver dual bound exceeds the minimization incumbent')
    # HiGHS reports (incumbent - lower bound) / abs(incumbent). Compare
    # absolute gaps to remain well-defined for a zero/near-zero objective.
    absolute_gap = max(0.0, reported_objective - dual)
    reported_absolute_gap = gap * abs(reported_objective)
    if abs(absolute_gap - reported_absolute_gap) > absolute_tolerance:
        raise PhysicalError('Solver relative gap and dual bound are inconsistent')
    nodes = solution.mip_node_count
    if isinstance(nodes, bool) or not isinstance(nodes, (int, np.integer)) or nodes < 0:
        raise PhysicalError('Solver node count must be a nonnegative integer')
    return {
        'solver_linear_objective': linear_objective,
        'solver_maximum_bound_violation': bound_violation,
        'solver_maximum_constraint_violation': constraint_violation,
        'solver_maximum_integrality_violation': integer_violation,
        'solver_mip_gap': gap, 'solver_mip_dual_bound': dual,
        'solver_mip_node_count': int(nodes),
        'solver_certificate_tolerances': {
            'primal_absolute': primal_tolerance, 'integrality_absolute': integer_tolerance,
            'relative_gap_roundoff': gap_tolerance,
            'objective_relative': objective_relative_tolerance,
            'objective_absolute': objective_absolute_tolerance,
        },
    }


def _clean_power(value: float, maximum: float) -> float:
    # Numerical-only cleanup, never projection of a materially invalid solution.
    if abs(value) <= NUMERICAL_TOLERANCE:
        return 0.0
    if maximum < value <= maximum + NUMERICAL_TOLERANCE:
        return float(maximum)
    return float(value)


def _plan(solution, point, lower, upper, initial_energy, previous_grid, battery, config, groups):
    x = np.asarray(solution.x, dtype=float)
    if x.shape != (8 * config.horizon_steps + 1,) or not np.isfinite(x).all():
        raise PhysicalError('Solver did not return a complete finite six-step plan')
    mode = x[groups['mode']]
    if np.any(np.abs(mode - np.round(mode)) > 1e-6) or np.any(mode < -1e-6) or np.any(mode > 1.0 + 1e-6):
        raise PhysicalError('Solver mode variables are not binary')
    charges = [_clean_power(v, battery.max_charge_kw) for v in x[groups['charge']]]
    discharges = [_clean_power(v, battery.max_discharge_kw) for v in x[groups['discharge']]]
    for t, (charge, discharge) in enumerate(zip(charges, discharges)):
        if charge > battery.max_charge_kw * round(float(mode[t])) + 1e-5 or discharge > battery.max_discharge_kw * (1 - round(float(mode[t]))) + 1e-5:
            raise PhysicalError('Solver power commands violate their binary mode links')
    energies = [float(initial_energy)]
    for charge, discharge in zip(charges, discharges):
        energies.append(transition(battery, energies[-1], charge, discharge))
    if not np.allclose(energies[1:], x[groups['energy']], atol=1e-5, rtol=0.0):
        raise PhysicalError('Solver states do not match the complete physical energy trajectory')
    net = np.asarray(discharges) - np.asarray(charges)
    grid = point + net
    grid_low, grid_high = lower + net, upper + net
    if config.grid_min_kw is not None and np.any(grid_low < config.grid_min_kw - 1e-5):
        raise PhysicalError('A predicted lower grid boundary is violated')
    if config.grid_max_kw is not None and np.any(grid_high > config.grid_max_kw + 1e-5):
        raise PhysicalError('A predicted upper grid boundary is violated')
    nominal_excess = np.maximum(0.0, np.abs(np.diff(np.r_[previous_grid, grid])) - config.ramp_limit_kw)
    prev_low = np.r_[previous_grid, grid_low[:-1]]
    prev_high = np.r_[previous_grid, grid_high[:-1]]
    worst_excess = np.maximum.reduce((np.zeros(config.horizon_steps),
        grid_high - prev_low - config.ramp_limit_kw, prev_high - grid_low - config.ramp_limit_kw))
    inner_low = battery.min_energy_kwh + config.soc_buffer_fraction * battery.capacity_kwh
    inner_high = battery.max_energy_kwh - config.soc_buffer_fraction * battery.capacity_kwh
    margin = sum(max(0.0, inner_low - e) + max(0.0, e - inner_high) for e in energies[1:])
    h, usable = config.horizon_steps, battery.usable_energy_kwh
    components = {
        'nominal_ramp_exceedance': float(np.sum(nominal_excess)) / (h * config.ramp_limit_kw),
        'battery_throughput': sum(c + d for c, d in zip(charges, discharges)) * battery.delta_t_hours / usable,
        'soc_margin_shortfall': margin / (h * usable),
        'uncertainty_exposure': float(np.sum(worst_excess)) / (h * config.ramp_limit_kw),
        'terminal_deviation': abs(energies[-1] - config.terminal_soc * battery.capacity_kwh) / usable,
    }
    weights = dict(zip(components, (config.ramp_weight, config.throughput_weight, config.soc_margin_weight,
                                    config.uncertainty_weight, config.terminal_weight)))
    weighted = {key: value * weights[key] for key, value in components.items()}
    objective = sum(weighted.values())
    solver_objective = _number(solution.fun, 'solver objective')
    if not math.isclose(objective, solver_objective, rel_tol=1e-5, abs_tol=1e-5):
        raise PhysicalError('Physical objective does not agree with solver objective')
    return {
        'horizon_steps': h, 'charge_kw': charges, 'discharge_kw': discharges,
        'energy_kwh': energies, 'soc': [e / battery.capacity_kwh for e in energies],
        'point_wind_kw': point.tolist(), 'lower_wind_kw': lower.tolist(), 'upper_wind_kw': upper.tolist(),
        'nominal_grid_kw': grid.tolist(), 'lower_grid_kw': grid_low.tolist(), 'upper_grid_kw': grid_high.tolist(),
        'nominal_ramp_exceedance_kw': nominal_excess.tolist(),
        'worst_box_ramp_exceedance_kw': worst_excess.tolist(),
        'objective_components': components, 'objective_weights': weights, 'weighted_objective_components': weighted,
        'objective': objective, 'solver_objective': solver_objective,
        'solver_mip_gap': None if getattr(solution, 'mip_gap', None) is None else float(solution.mip_gap),
        'solver_mip_node_count': None if getattr(solution, 'mip_node_count', None) is None else int(solution.mip_node_count),
        'numerical_cleanup_tolerance_kw': NUMERICAL_TOLERANCE,
        'risk_interpretation': 'sum of per-step Cartesian-box ramp envelopes; no joint coverage or closed-loop robustness guarantee',
    }


def _heuristic(forecast, energy, previous_grid, battery, config, start):
    point = float(forecast.point_kw[0])
    charge_cap = min(battery.max_charge_kw, max(0.0, (battery.max_energy_kwh - energy) / (battery.eta_charge * battery.delta_t_hours)))
    discharge_cap = min(battery.max_discharge_kw, max(0.0, (energy - battery.min_energy_kwh) * battery.eta_discharge / battery.delta_t_hours))
    lo, hi = -charge_cap, discharge_cap
    if config.grid_min_kw is not None:
        lo = max(lo, config.grid_min_kw - point)
    if config.grid_max_kw is not None:
        hi = min(hi, config.grid_max_kw - point)
    if lo > hi + NUMERICAL_TOLERANCE:
        return _fallback('heuristic', start, 'heuristic_grid_constraints_infeasible', optimization_failed=False)
    target = min(max(point, previous_grid - config.ramp_limit_kw), previous_grid + config.ramp_limit_kw)
    net = min(max(target - point, lo), hi)
    charge, discharge = max(0.0, -net), max(0.0, net)
    next_energy = transition(battery, energy, charge, discharge)
    return Decision(charge, discharge, 'heuristic', 'heuristic', None, 'First-point ramp-following rule; no solver',
        perf_counter() - start, False, False, None,
        {'horizon_steps': 1, 'charge_kw': [charge], 'discharge_kw': [discharge],
         'energy_kwh': [energy, next_energy], 'nominal_grid_kw': [point + net]})


def decide(controller: str, forecast: ForecastBundle | None, decision_time: datetime,
           energy_kwh: float, previous_grid_kw: float, battery: BatteryConfig | None = None,
           config: MPCConfig | None = None) -> Decision:
    """Plan from available forecasts, apply ONLY the first command, then replan.

    No realized future wind is accepted by this interface. Missing/invalid forecast
    and failed solves produce zero-dispatch battery safety fallbacks. Grid limits
    cannot be guaranteed by fallback when uncontrollable wind makes them impossible.
    """
    start = perf_counter()
    battery = BatteryConfig() if battery is None else battery
    config = MPCConfig() if config is None else config
    if not isinstance(battery, BatteryConfig) or not isinstance(config, MPCConfig):
        raise ValueError('Expected BatteryConfig and MPCConfig instances')
    if controller not in CONTROLLERS:
        raise ValueError('Unknown controller')
    _context(battery, config, energy_kwh, previous_grid_kw, decision_time)
    if controller == 'uncontrolled':
        return Decision(0.0, 0.0, controller, 'baseline', None, 'No battery dispatch',
                        perf_counter() - start, False, False, None, None)
    if forecast is None:
        return _fallback(controller, start, 'missing_forecast', optimization_failed=False)
    try:
        if not isinstance(forecast, ForecastBundle):
            raise ValueError('Expected a validated ForecastBundle')
        forecast.validate(decision_time, step_minutes=battery.step_minutes, horizon=config.horizon_steps)
    except (TypeError, ValueError, AttributeError) as error:
        return _fallback(controller, start, 'invalid_forecast: ' + str(error), optimization_failed=False)
    if controller == 'heuristic':
        return _heuristic(forecast, energy_kwh, previous_grid_kw, battery, config, start)
    point, lower, upper = _forecast_arrays(controller, forecast, config)
    try:
        objective, integers, bounds, constraints, groups = _formulate(point, lower, upper, energy_kwh, previous_grid_kw, battery, config)
        solution = milp(objective, integrality=integers, bounds=bounds, constraints=constraints,
                        options={'disp': False, 'presolve': True, 'time_limit': config.solver_time_limit_s,
                                 'mip_rel_gap': config.solver_mip_rel_gap})
    except Exception as error:
        return _fallback(controller, start, 'solver_exception: ' + type(error).__name__ + ': ' + str(error),
                         optimization_failed=True)
    status = getattr(solution, 'status', None)
    message = str(getattr(solution, 'message', ''))
    if status != 0 or not getattr(solution, 'success', False):
        return _fallback(controller, start, 'solver_status_' + str(status), optimization_failed=True,
                         solver_status=status, message=message)
    try:
        certificate = _validate_solver_certificate(solution, objective, integers, bounds, constraints, config)
        plan = _plan(solution, point, lower, upper, energy_kwh, previous_grid_kw, battery, config, groups)
        plan.update(certificate)
    except (ValueError, TypeError, AttributeError, OverflowError) as error:
        return _fallback(controller, start, 'invalid_solver_plan: ' + str(error), optimization_failed=True,
                         solver_status=status, message=message)
    return Decision(plan['charge_kw'][0], plan['discharge_kw'][0], controller, 'optimal', status, message,
                    perf_counter() - start, False, False, None, plan)
