"""Stage 3.3 scenario-based stochastic MPC (synthetic research controller).

Minimises a sample-average approximation of EXPECTED ramp-threshold exceedance
over K forecast scenarios built from each horizon's conformal interval, plus
battery throughput and an SOC operating-band penalty. A do-no-harm gate applies
zero dispatch unless the optimised plan beats the zero-dispatch plan's expected
cost by a prespecified margin. Stage 3.1 controllers are unchanged; this module
reuses their Decision type, plant model and solver-certificate checks.

Modelling assumptions (all explicit, all ablatable):
* Scenario shape: Gaussian quantile nodes scaled so the conformal (1-alpha)
  interval edge maps to the normal (1-alpha/2) quantile; the lower and upper
  half-widths are scaled separately. This is an ASSUMED shape, not a property
  conformal prediction provides.
* Cross-horizon dependence: comonotone (one common standardised shock per
  scenario across all six horizons). Not a joint-coverage guarantee.
* Open-loop plan within the horizon; only the first move is applied.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import math
from statistics import NormalDist
from time import perf_counter

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from publication_v2.stage31.battery import BatteryConfig, PhysicalError, transition
from publication_v2.stage31.controllers import (Decision, NUMERICAL_TOLERANCE, _clean_power,
                                                _validate_solver_certificate)
from publication_v2.stage31.forecast import ForecastBundle

SCENARIO_SETS = {
    'point': ((0.,), (1.,)),
    'gaussian3': ((-1.2815515655446004, 0., 1.2815515655446004), (.25, .5, .25)),
    'gaussian5': ((-1.2815515655446004, -.5244005127080407, 0., .5244005127080407, 1.2815515655446004),
                  (.2, .2, .2, .2, .2)),
}


@dataclass(frozen=True)
class StochasticMPCConfig:
    horizon_steps: int = 6
    ramp_limit_kw: float = 200.
    ramp_weight: float = 1.
    throughput_weight: float = .05
    scenarios: str = 'gaussian5'
    soc_mode: str = 'band'            # 'band' (operating band) or 'terminal' (Stage 3.1-style target)
    band_low_soc: float = .5
    band_high_soc: float = .8
    band_weight: float = .05
    terminal_soc: float = .65
    terminal_weight: float = .1
    gate_kw: float = 10.              # minimum expected ramp-exceedance-equivalent benefit; 0 disables
    dependence: str = 'comonotone'    # or 'independent_increments' (see ramp_scenarios)
    skill_gate: float | None = None   # dispatch only if released skill score vs persistence > this
    solver_time_limit_s: float = 5.
    solver_mip_rel_gap: float = 1e-8

    def __post_init__(self):
        if type(self.horizon_steps) is not int or self.horizon_steps != 6:
            raise ValueError('Six horizon steps required (Stage 2 compatibility)')
        if self.skill_gate is not None and (isinstance(self.skill_gate, bool) or not isinstance(self.skill_gate, (int, float))
                                            or not math.isfinite(self.skill_gate) or not -1 <= self.skill_gate < 1):
            raise ValueError('skill_gate must be None or a finite skill score in [-1, 1)')
        if self.scenarios not in SCENARIO_SETS:
            raise ValueError('Unknown scenario set')
        if self.dependence not in ('comonotone', 'independent_increments'):
            raise ValueError('Unknown cross-horizon dependence model')
        if self.soc_mode not in ('band', 'terminal'):
            raise ValueError('soc_mode must be band or terminal')
        for name in ('ramp_limit_kw', 'ramp_weight', 'solver_time_limit_s'):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be finite and positive')
        for name in ('throughput_weight', 'band_weight', 'terminal_weight', 'gate_kw', 'solver_mip_rel_gap'):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f'{name} must be finite and nonnegative')
        if not 0 <= self.band_low_soc < self.band_high_soc <= 1 or not 0 <= self.terminal_soc <= 1:
            raise ValueError('Invalid SOC band or terminal target')


def scenario_wind(forecast: ForecastBundle, config: StochasticMPCConfig):
    """Return (K x H wind scenarios in kW, probabilities)."""
    nodes, probabilities = SCENARIO_SETS[config.scenarios]
    point = np.asarray(forecast.point_kw, dtype=float)
    lower = np.asarray(forecast.lower_kw, dtype=float)
    upper = np.asarray(forecast.upper_kw, dtype=float)
    edge = NormalDist().inv_cdf(1 - forecast.alpha / 2)
    rows = []
    for z in nodes:
        half = (upper - point) if z > 0 else (point - lower)
        rows.append(np.maximum(0., point + z / edge * half))
    return np.asarray(rows), np.asarray(probabilities, dtype=float)


def ramp_scenarios(forecast: ForecastBundle, previous_grid: float, config: StochasticMPCConfig):
    """Uncontrolled ramp scenarios R (K x H, kW) and probabilities.

    Realised grid ramp at step t = R[k, t] + (net_t - net_{t-1}), net_{-1} = 0,
    because the previous grid export already contains the previous battery net.
    Expected total exceedance is a sum of per-step expectations, so only each
    step's MARGINAL ramp distribution matters (no joint scenario tree needed).

    * comonotone: one common standardised shock across horizons; the ramp
      spread is z * (sigma_t - sigma_{t-1}), i.e. later-step ramps look nearly
      certain whenever interval widths grow slowly.
    * independent_increments: forecast errors accumulate as independent steps
      (random-walk error); ramp spread s_0 = sigma_0, s_t = sqrt(sigma_t^2 -
      sigma_{t-1}^2) (floored at 0). Assumed, not provided by conformal theory.
    """
    nodes, probabilities = SCENARIO_SETS[config.scenarios]
    probabilities = np.asarray(probabilities, dtype=float)
    if config.dependence == 'comonotone':
        wind, _ = scenario_wind(forecast, config)
        anchor = np.c_[np.full(len(nodes), float(previous_grid)), wind[:, :-1]]
        return wind - anchor, probabilities
    point = np.asarray(forecast.point_kw, dtype=float)
    edge = NormalDist().inv_cdf(1 - forecast.alpha / 2)
    sigma_up = (np.asarray(forecast.upper_kw, dtype=float) - point) / edge
    sigma_down = (point - np.asarray(forecast.lower_kw, dtype=float)) / edge
    centre = np.diff(np.r_[float(previous_grid), point])
    rows = []
    for z in nodes:
        sigma = sigma_up if z > 0 else sigma_down
        spread = np.sqrt(np.maximum(np.diff(np.r_[0., sigma ** 2]), 0.))
        rows.append(centre + z * spread)
    return np.asarray(rows), probabilities


def _layout(h, k):
    names = ('charge', 'discharge', 'energy', 'mode', 'low', 'high')
    groups = {name: np.arange(i * h, (i + 1) * h) for i, name in enumerate(names)}
    groups['excess'] = np.arange(6 * h, 6 * h + k * h).reshape(k, h)
    return groups, 6 * h + k * h + 1  # final variable: terminal deviation


def _formulate(ramps, probabilities, energy, battery, config):
    k, h = ramps.shape
    groups, size = _layout(h, k)
    terminal = size - 1
    c, lb, ub = np.zeros(size), np.zeros(size), np.full(size, np.inf)
    integrality = np.zeros(size, dtype=int)
    ub[groups['charge']], ub[groups['discharge']] = battery.max_charge_kw, battery.max_discharge_kw
    lb[groups['energy']], ub[groups['energy']] = battery.min_energy_kwh, battery.max_energy_kwh
    ub[groups['mode']] = 1.
    integrality[groups['mode']] = 1
    usable, dt, limit = battery.usable_energy_kwh, battery.delta_t_hours, config.ramp_limit_kw
    c[groups['charge']] = c[groups['discharge']] = config.throughput_weight * dt / usable
    for s in range(k):
        c[groups['excess'][s]] = config.ramp_weight * probabilities[s] / (h * limit)
    if config.soc_mode == 'band':
        c[groups['low']] = c[groups['high']] = config.band_weight / (h * usable)
    else:
        ub[groups['low']] = ub[groups['high']] = 0.
        c[terminal] = config.terminal_weight / usable
    if config.soc_mode == 'band':
        ub[terminal] = 0.
    rows, lows, highs = [], [], []

    def add(coefficients, low=-np.inf, high=np.inf):
        row = np.zeros(size)
        for index, value in coefficients.items():
            row[index] += value
        rows.append(row); lows.append(low); highs.append(high)

    band_low = config.band_low_soc * battery.capacity_kwh
    band_high = config.band_high_soc * battery.capacity_kwh
    for t in range(h):
        ch, dis, e, mode = (groups[n][t] for n in ('charge', 'discharge', 'energy', 'mode'))
        equation = {e: 1., ch: -battery.eta_charge * dt, dis: dt / battery.eta_discharge}
        if t:
            equation[groups['energy'][t - 1]] = -1.
            add(equation, 0., 0.)
        else:
            add(equation, energy, energy)
        add({ch: 1., mode: -battery.max_charge_kw}, high=0.)
        add({dis: 1., mode: battery.max_discharge_kw}, high=battery.max_discharge_kw)
        if config.soc_mode == 'band':  # unused soft variables stay fixed at 0 with no constraint
            add({groups['low'][t]: 1., e: 1.}, low=band_low)
            add({groups['high'][t]: 1., e: -1.}, low=-band_high)
        delta = {dis: 1., ch: -1.}
        if t:
            delta[groups['discharge'][t - 1]] = -1.
            delta[groups['charge'][t - 1]] = 1.
        for s in range(k):
            constant = ramps[s, t]
            variable = groups['excess'][s, t]
            row = {i: -v for i, v in delta.items()}; row[variable] = 1.
            add(row, low=constant - limit)            # s >= +ramp - L
            row = dict(delta); row[variable] = 1.
            add(row, low=-constant - limit)           # s >= -ramp - L
    if config.soc_mode == 'terminal':
        target = config.terminal_soc * battery.capacity_kwh
        add({terminal: 1., groups['energy'][-1]: -1.}, low=-target)
        add({terminal: 1., groups['energy'][-1]: 1.}, low=target)
    return c, integrality, Bounds(lb, ub), LinearConstraint(np.asarray(rows), lows, highs), groups


def plan_cost(charges, discharges, energies, ramps, probabilities, battery, config):
    """Independent recomputation of the expected-cost objective from physical quantities."""
    k, h = ramps.shape
    net = np.asarray(discharges, dtype=float) - np.asarray(charges, dtype=float)
    realised = ramps + np.diff(np.r_[0., net])            # K x H scenario grid ramps
    excess = np.maximum(0., np.abs(realised) - config.ramp_limit_kw)
    usable = battery.usable_energy_kwh
    components = {
        'expected_ramp_exceedance': float(probabilities @ excess.sum(axis=1)) / (h * config.ramp_limit_kw),
        'battery_throughput': float(np.sum(charges) + np.sum(discharges)) * battery.delta_t_hours / usable,
    }
    if config.soc_mode == 'band':
        lo, hi = config.band_low_soc * battery.capacity_kwh, config.band_high_soc * battery.capacity_kwh
        components['soc_band_shortfall'] = sum(max(0., lo - e) + max(0., e - hi) for e in energies[1:]) / (h * usable)
        weights = {'expected_ramp_exceedance': config.ramp_weight, 'battery_throughput': config.throughput_weight,
                   'soc_band_shortfall': config.band_weight}
    else:
        components['terminal_deviation'] = abs(energies[-1] - config.terminal_soc * battery.capacity_kwh) / usable
        weights = {'expected_ramp_exceedance': config.ramp_weight, 'battery_throughput': config.throughput_weight,
                   'terminal_deviation': config.terminal_weight}
    weighted = {name: components[name] * weights[name] for name in components}
    return sum(weighted.values()), components, weighted, (probabilities @ excess).tolist()


def released_skill_score(forecast: ForecastBundle):
    """Pooled skill score the adapter derived from verified released residuals, or None."""
    try:
        score = json.loads(forecast.provenance)['released_skill']['pooled_skill_score']
    except (ValueError, KeyError, TypeError):
        return None
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
        return None
    return float(score)


def _zero_plan(energy, h):
    return [0.] * h, [0.] * h, [float(energy)] * (h + 1)


def decide_stochastic(controller: str, forecast: ForecastBundle | None, decision_time: datetime,
                      energy_kwh: float, previous_grid_kw: float, battery: BatteryConfig | None = None,
                      config: StochasticMPCConfig | None = None) -> Decision:
    """Plan, certify, gate, and return only the first move (receding horizon)."""
    start = perf_counter()
    battery = BatteryConfig() if battery is None else battery
    config = StochasticMPCConfig() if config is None else config
    if not isinstance(battery, BatteryConfig) or not isinstance(config, StochasticMPCConfig):
        raise ValueError('Expected BatteryConfig and StochasticMPCConfig')
    transition(battery, energy_kwh, 0., 0.)
    if not isinstance(decision_time, datetime) or decision_time.tzinfo is None:
        raise ValueError('decision_time must be timezone aware')

    def fallback(reason, failed, status=None, message=''):
        return Decision(0., 0., controller, 'fallback', status, message, perf_counter() - start,
                        failed, True, reason, None)

    if forecast is None:
        return fallback('missing_forecast', False)
    try:
        if not isinstance(forecast, ForecastBundle):
            raise ValueError('Expected a validated ForecastBundle')
        forecast.validate(decision_time, step_minutes=battery.step_minutes, horizon=config.horizon_steps)
    except (TypeError, ValueError, AttributeError) as error:
        return fallback('invalid_forecast: ' + str(error), False)
    if config.skill_gate is not None:
        score = released_skill_score(forecast)
        if score is None or score <= config.skill_gate:
            zero = _zero_plan(energy_kwh, config.horizon_steps)
            return Decision(0., 0., controller, 'skill_gated', None,
                            'Released forecast skill does not exceed the prespecified threshold',
                            perf_counter() - start, False, False, None,
                            {'horizon_steps': config.horizon_steps, 'charge_kw': zero[0], 'discharge_kw': zero[1],
                             'energy_kwh': zero[2], 'skill_gated': True, 'released_skill_score': score,
                             'skill_gate': config.skill_gate, 'config': asdict(config)})
    ramps, probabilities = ramp_scenarios(forecast, previous_grid_kw, config)
    try:
        objective, integers, bounds, constraints, groups = _formulate(
            ramps, probabilities, energy_kwh, battery, config)
        solution = milp(objective, integrality=integers, bounds=bounds, constraints=constraints,
                        options={'disp': False, 'presolve': True, 'time_limit': config.solver_time_limit_s,
                                 'mip_rel_gap': config.solver_mip_rel_gap})
    except Exception as error:  # solver/library failure -> safe zero dispatch
        return fallback('solver_exception: ' + type(error).__name__, True)
    status, message = getattr(solution, 'status', None), str(getattr(solution, 'message', ''))
    if status != 0 or not getattr(solution, 'success', False):
        return fallback('solver_status_' + str(status), True, status, message)
    try:
        certificate = _validate_solver_certificate(solution, objective, integers, bounds, constraints, config)
        x = np.asarray(solution.x, dtype=float)
        mode = x[groups['mode']]
        if np.any(np.abs(mode - np.round(mode)) > 1e-6):
            raise PhysicalError('Solver mode variables are not binary')
        charges = [_clean_power(v, battery.max_charge_kw) for v in x[groups['charge']]]
        discharges = [_clean_power(v, battery.max_discharge_kw) for v in x[groups['discharge']]]
        energies = [float(energy_kwh)]
        for ch, dis in zip(charges, discharges):
            energies.append(transition(battery, energies[-1], ch, dis))
        if not np.allclose(energies[1:], x[groups['energy']], atol=1e-5, rtol=0.):
            raise PhysicalError('Solver states do not match the physical energy trajectory')
        cost, components, weighted, expected_excess = plan_cost(
            charges, discharges, energies, ramps, probabilities, battery, config)
        if not math.isclose(cost, float(solution.fun), rel_tol=1e-5, abs_tol=1e-5):
            raise PhysicalError('Physical objective does not agree with solver objective')
    except (ValueError, TypeError, AttributeError, OverflowError) as error:
        return fallback('invalid_solver_plan: ' + str(error), True, status, message)
    zero = _zero_plan(energy_kwh, config.horizon_steps)
    zero_cost, zero_components, _, zero_excess = plan_cost(
        *zero, ramps, probabilities, battery, config)
    threshold = config.ramp_weight * config.gate_kw / (config.horizon_steps * config.ramp_limit_kw)
    benefit = zero_cost - cost
    gated = config.gate_kw > 0 and benefit < threshold
    applied = zero if gated else (charges, discharges, energies)
    plan = {'horizon_steps': config.horizon_steps, 'charge_kw': applied[0], 'discharge_kw': applied[1],
            'energy_kwh': applied[2], 'soc': [e / battery.capacity_kwh for e in applied[2]],
            'gated': gated, 'gate_threshold_objective': threshold, 'expected_benefit_objective': benefit,
            'optimised': {'charge_kw': charges, 'discharge_kw': discharges, 'energy_kwh': energies,
                          'objective': cost, 'objective_components': components,
                          'weighted_objective_components': weighted,
                          'expected_ramp_exceedance_kw': expected_excess},
            'zero_dispatch': {'objective': zero_cost, 'objective_components': zero_components,
                              'expected_ramp_exceedance_kw': zero_excess},
            'scenario_ramp_kw': ramps.tolist(), 'scenario_probabilities': probabilities.tolist(),
            'config': asdict(config), **certificate,
            'risk_interpretation': 'SAA of expected ramp exceedance under assumed Gaussian-shaped, '
                                   'comonotone scenarios scaled from marginal conformal intervals'}
    return Decision(applied[0][0], applied[1][0], controller, 'gated' if gated else 'optimal', status, message,
                    perf_counter() - start, False, False, None, plan)
