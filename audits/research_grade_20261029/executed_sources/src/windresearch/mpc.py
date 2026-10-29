"""Versioned exploratory MPC, preserving the frozen controller's algebra.

The frozen scripts remain the authority for the original experiment.  This
parameterized implementation has a separately declared deterministic solver
profile; alternative MILP optima can therefore produce different trajectories.
No actual future wind is accepted by :meth:`TwoStageMPC.decide`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any

import cvxpy as cp
import numpy as np


class SolverFailure(RuntimeError):
    """A non-optimal solve is an experiment failure, never a zero-cost result."""


@dataclass(frozen=True)
class MPCConfig:
    capacity_kwh: float = 2000.0
    max_power_kw: float = 1000.0
    min_soc_percent: float = 40.0
    max_soc_percent: float = 90.0
    initial_soc_percent: float = 50.0
    reserve_soc_percent: float = 50.0
    terminal_soc_percent: float = 50.0
    eta_charge: float = 0.95
    eta_discharge: float = 0.95
    dt_hours: float = 1 / 6
    horizon: int = 6
    ramp_limit_kw: float = 200.0
    risk_weight: float = 0.5
    battery_ramp_weight: float = 0.1
    absolute_ramp_weight: float = 1.0
    secondary_exceedance_weight: float = 20.0
    throughput_weight: float = 0.1
    terminal_weight: float = 2.0
    curtailment_weight: float = 50.0
    reserve_penalty: float = 100.0
    primary_tolerance: float = 100.0
    primary_enabled: bool = True
    solver: str = "HIGHS"
    threads: int = 1
    random_seed: int = 20261029
    time_limit_seconds: float = 30.0
    mip_relative_gap: float = 0.0

    def __post_init__(self) -> None:
        if not all(np.isfinite(v) for v in asdict(self).values() if isinstance(v, (int, float))):
            raise ValueError("Configuration contains non-finite values")
        if not 1 <= self.horizon <= 6 or not isinstance(self.horizon, int):
            raise ValueError("Horizon must be an integer from one to six")
        if self.capacity_kwh <= 0 or self.max_power_kw <= 0 or self.dt_hours <= 0:
            raise ValueError("Capacity, power and interval must be positive")
        if not 0 <= self.min_soc_percent < self.max_soc_percent <= 100:
            raise ValueError("Invalid SOC limits")
        for value in (self.initial_soc_percent, self.reserve_soc_percent, self.terminal_soc_percent):
            if not self.min_soc_percent <= value <= self.max_soc_percent:
                raise ValueError("Initial, reserve and terminal references must lie inside SOC bounds")
        if not 0 < self.eta_charge <= 1 or not 0 < self.eta_discharge <= 1:
            raise ValueError("Efficiencies must lie in (0, 1]")
        if not 0 <= self.risk_weight <= 1:
            raise ValueError("Risk weight must lie in [0, 1]")
        for name in ("ramp_limit_kw", "battery_ramp_weight", "absolute_ramp_weight", "secondary_exceedance_weight",
                     "throughput_weight", "terminal_weight", "curtailment_weight", "reserve_penalty",
                     "primary_tolerance", "mip_relative_gap"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be nonnegative")
        if self.time_limit_seconds <= 0 or self.threads < 1:
            raise ValueError("Invalid solver resources")

    @property
    def min_energy(self) -> float:
        return self.capacity_kwh * self.min_soc_percent / 100

    @property
    def max_energy(self) -> float:
        return self.capacity_kwh * self.max_soc_percent / 100

    @property
    def initial_energy(self) -> float:
        return self.capacity_kwh * self.initial_soc_percent / 100


def _differences(values: cp.Expression, previous: cp.Parameter, horizon: int) -> cp.Expression:
    first = cp.reshape(values[0] - previous, (1,), order="C")
    return first if horizon == 1 else cp.hstack([first, values[1:] - values[:-1]])


class TwoStageMPC:
    """Compile once per configuration, then update only observed state/forecasts."""

    def __init__(self, config: MPCConfig = MPCConfig()) -> None:
        self.config = c = config
        h = c.horizon
        self.energy_now = cp.Parameter(name="observed_energy")
        self.previous_export = cp.Parameter(name="previous_actual_export")
        self.previous_battery = cp.Parameter(name="previous_actual_battery_power")
        self.primary_bound = cp.Parameter(name="primary_stage_bound")
        self.charge_first = cp.Variable(nonneg=True)
        self.discharge_first = cp.Variable(nonneg=True)
        self.curtail_first = cp.Variable(nonneg=True)
        mode_first = cp.Variable(boolean=True)
        constraints = [
            self.charge_first <= c.max_power_kw * mode_first,
            self.discharge_first <= c.max_power_kw * (1 - mode_first),
            self.charge_first <= (c.max_energy - self.energy_now) / (c.eta_charge * c.dt_hours),
            self.discharge_first <= (self.energy_now - c.min_energy) * c.eta_discharge / c.dt_hours,
        ]
        self.weights = [1.0] if c.risk_weight == 0 else [1 - c.risk_weight, c.risk_weight]
        self.scenarios: list[dict[str, Any]] = []
        costs, exceeds = [], []
        for index in range(len(self.weights)):
            forecast = cp.Parameter(h, nonneg=True, name=f"forecast_{index}")
            big_m = cp.Parameter(nonneg=True, name=f"first_min_big_m_{index}")
            charge = cp.Variable(h, nonneg=True)
            discharge = cp.Variable(h, nonneg=True)
            curtailment = cp.Variable(h, nonneg=True)
            energy = cp.Variable(h + 1)
            mode = cp.Variable(h, boolean=True)
            export = forecast - curtailment - charge + discharge
            constraints += [energy[0] == self.energy_now, energy >= c.min_energy, energy <= c.max_energy,
                charge <= c.max_power_kw * mode, discharge <= c.max_power_kw * (1 - mode),
                curtailment <= forecast, charge <= forecast - curtailment, export >= 0,
                discharge[0] == self.discharge_first, mode[0] == mode_first]
            charge_selector, curtail_selector = cp.Variable(boolean=True), cp.Variable(boolean=True)
            remaining = forecast[0] - charge[0]
            constraints += [charge[0] <= self.charge_first, charge[0] <= forecast[0],
                charge[0] >= self.charge_first - big_m * charge_selector,
                charge[0] >= forecast[0] - big_m * (1 - charge_selector),
                curtailment[0] <= self.curtail_first, curtailment[0] <= remaining,
                curtailment[0] >= self.curtail_first - big_m * curtail_selector,
                curtailment[0] >= remaining - big_m * (1 - curtail_selector)]
            for t in range(h):
                constraints += [energy[t + 1] == energy[t] + c.eta_charge * charge[t] * c.dt_hours
                                - discharge[t] * c.dt_hours / c.eta_discharge]
            ramp = _differences(export, self.previous_export, h)
            battery_ramp = _differences(discharge - charge, self.previous_battery, h)
            abs_ramp, abs_battery = cp.Variable(h, nonneg=True), cp.Variable(h, nonneg=True)
            exceedance, reserve_shortfall = cp.Variable(h, nonneg=True), cp.Variable(h, nonneg=True)
            constraints += [abs_battery >= battery_ramp, abs_battery >= -battery_ramp,
                abs_ramp >= ramp, abs_ramp >= -ramp, exceedance >= abs_ramp - c.ramp_limit_kw,
                energy[1:] + reserve_shortfall >= c.capacity_kwh * c.reserve_soc_percent / 100]
            cost = (c.absolute_ramp_weight * cp.sum(abs_ramp) + c.battery_ramp_weight * cp.sum(abs_battery)
                + c.secondary_exceedance_weight * cp.sum(exceedance)
                + c.throughput_weight * c.dt_hours * cp.sum(charge + discharge)
                + c.terminal_weight * cp.abs(energy[h] - c.capacity_kwh * c.terminal_soc_percent / 100)
                + c.curtailment_weight * cp.sum(curtailment) + c.reserve_penalty * cp.sum(reserve_shortfall))
            costs.append(cost)
            exceeds.append(cp.sum(exceedance))
            self.scenarios.append(dict(forecast=forecast, big_m=big_m, charge=charge,
                discharge=discharge, curtailment=curtailment, energy=energy, export=export,
                ramp=ramp, exceedance=exceedance, reserve_shortfall=reserve_shortfall))
        self.primary_expression = sum(w * e for w, e in zip(self.weights, exceeds))
        self.secondary_expression = sum(w * cost for w, cost in zip(self.weights, costs))
        self.primary_problem = cp.Problem(cp.Minimize(self.primary_expression), constraints)
        secondary_constraints = constraints + ([self.primary_expression <= self.primary_bound] if c.primary_enabled else [])
        self.secondary_problem = cp.Problem(cp.Minimize(self.secondary_expression), secondary_constraints)
        self.constraints = constraints
        if not self.primary_problem.is_dpp() or not self.secondary_problem.is_dpp():
            raise ValueError("Parameterized controller must satisfy DPP caching rules")

    def _solve(self, problem: cp.Problem, stage: str) -> dict[str, Any]:
        start = perf_counter()
        c = self.config
        try:
            problem.solve(solver=c.solver, warm_start=False, threads=c.threads, random_seed=c.random_seed,
                          time_limit=c.time_limit_seconds, mip_rel_gap=c.mip_relative_gap)
        except Exception as error:
            raise SolverFailure(f"{stage}: {type(error).__name__}: {error}") from error
        if problem.status != cp.OPTIMAL or problem.value is None or not np.isfinite(problem.value):
            raise SolverFailure(f"{stage}: status={problem.status}, objective={problem.value}")
        info = problem.solver_stats.extra_stats
        def number(name: str) -> float | None:
            value = getattr(info, name, None)
            return float(value) if value is not None and np.isfinite(value) else None
        return {"status": problem.status, "objective": float(problem.value),
                "wall_seconds": perf_counter() - start, "solver_seconds": problem.solver_stats.solve_time,
                "mip_gap": number("mip_gap"), "mip_nodes": number("mip_node_count"),
                "mip_dual_bound": number("mip_dual_bound")}

    def decide(self, nominal: np.ndarray, margins: np.ndarray, energy_now: float,
               previous_export: float, previous_battery: float = 0.0) -> dict[str, Any]:
        c = self.config
        nominal, margins = np.asarray(nominal, float), np.asarray(margins, float)
        if nominal.shape != (c.horizon,) or margins.shape != nominal.shape:
            raise ValueError("Forecast/margin arrays must match configured horizon")
        if not np.isfinite(np.r_[nominal, margins, energy_now, previous_export, previous_battery]).all():
            raise ValueError("Non-finite forecast or state")
        if (margins < 0).any() or not c.min_energy - 1e-5 <= energy_now <= c.max_energy + 1e-5:
            raise ValueError("Negative margin or state outside hard SOC limits")
        self.energy_now.value = float(np.clip(energy_now, c.min_energy, c.max_energy))
        self.previous_export.value, self.previous_battery.value = previous_export, previous_battery
        forecasts = [np.maximum(0, nominal)]
        if len(self.scenarios) == 2:
            forecasts.append(np.maximum(0, nominal - margins))
        for scenario, forecast in zip(self.scenarios, forecasts):
            scenario["forecast"].value = forecast
            scenario["big_m"].value = c.max_power_kw + max(float(forecast[0]), c.max_power_kw)
        stage1 = self._solve(self.primary_problem, "primary") if c.primary_enabled else {
            "status": "disabled_by_declared_ablation", "objective": None, "wall_seconds": 0.0,
            "solver_seconds": 0.0, "mip_gap": None, "mip_nodes": None, "mip_dual_bound": None}
        if c.primary_enabled:
            self.primary_bound.value = stage1["objective"] + c.primary_tolerance
        stage2 = self._solve(self.secondary_problem, "secondary")
        achieved = float(self.primary_expression.value)
        if c.primary_enabled and achieved > stage1["objective"] + c.primary_tolerance + 1e-3:
            raise SolverFailure("Secondary solution violates lexicographic tolerance")
        max_violation = max(float(np.max(np.abs(constraint.violation()))) for constraint in self.secondary_problem.constraints)
        if max_violation > 1e-3:
            raise SolverFailure(f"Constraint residual {max_violation:.6g} exceeds 1e-3")
        plans = []
        for index, scenario in enumerate(self.scenarios):
            for t in range(c.horizon):
                plans.append({"scenario": "nominal" if index == 0 else "downside", "scenario_weight": self.weights[index],
                    "physical_ramp_exceedance_kw": max(0., abs(float(scenario["ramp"].value[t])) - c.ramp_limit_kw),
                    "physical_reserve_shortfall_kwh": max(0., c.capacity_kwh * c.reserve_soc_percent / 100 - float(scenario["energy"].value[t + 1])),
                    "horizon_minutes": (t + 1) * 10, **{name + ("_kwh" if name in ("energy", "reserve_shortfall") else "_kw"):
                    float(scenario[name].value[t + 1 if name == "energy" else t])
                    for name in ("forecast", "charge", "discharge", "curtailment", "energy", "export", "ramp", "exceedance", "reserve_shortfall")}})
        return {"committed_charge_kw": max(0., float(self.charge_first.value)),
                "committed_discharge_kw": max(0., float(self.discharge_first.value)),
                "committed_curtailment_kw": max(0., float(self.curtail_first.value)),
                "stage1": stage1, "stage2": stage2, "achieved_primary": achieved,
                "max_constraint_residual": max_violation, "plans": plans}


def realise(decision: dict[str, Any], actual_wind_kw: float, energy_kwh: float,
            config: MPCConfig = MPCConfig()) -> dict[str, float]:
    """Reveal wind only after commitment, then apply the frozen physical fallback."""
    c = config
    if not np.isfinite([actual_wind_kw, energy_kwh]).all():
        raise ValueError("Non-finite physical input")
    wind = max(0., actual_wind_kw)
    charge = min(decision["committed_charge_kw"], wind, c.max_power_kw,
                 max(0., c.max_energy - energy_kwh) / (c.eta_charge * c.dt_hours))
    discharge = min(decision["committed_discharge_kw"], c.max_power_kw,
                    max(0., energy_kwh + c.eta_charge * charge * c.dt_hours - c.min_energy)
                    * c.eta_discharge / c.dt_hours)
    curtailment = min(decision["committed_curtailment_kw"], max(0., wind - charge))
    next_energy = energy_kwh + c.eta_charge * charge * c.dt_hours - discharge * c.dt_hours / c.eta_discharge
    if min(charge, discharge, curtailment) < -1e-6 or charge * discharge > 1e-3:
        raise ValueError("Invalid committed command or simultaneous charging/discharging")
    if not c.min_energy - 1e-5 <= next_energy <= c.max_energy + 1e-5:
        raise ValueError("Physical fallback violated SOC bounds")
    return {"wind_generation_kw": wind, "charge_kw": charge, "discharge_kw": discharge,
            "curtailment_kw": curtailment, "grid_export_kw": wind - charge - curtailment + discharge,
            "energy_kwh": next_energy, "soc_percent": 100 * next_energy / c.capacity_kwh}
