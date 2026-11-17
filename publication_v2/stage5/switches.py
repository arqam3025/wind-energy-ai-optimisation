"""Graded forecast-skill switch (Stage 5, exploratory).

The Stage 3.3 switch is binary: the battery idles when the released skill score is at or below a
threshold. On real data the skill hovers near that threshold (about 0.13–0.15 vs 0.10), so the
switch idles about half of the decisions and loses benefit.

The graded switch scales the battery's planned flows by a weight w(skill):

    w = clip((skill - s0) / (s1 - s0), 0, 1)

- w = 0 means idle; w = 1 means the unswitched stochastic MPC plan.
- Scaling every planned flow by w moves the energy trajectory linearly towards its initial level
  (E_k -> E_0 + w (E_k - E_0)). Both end points are feasible, so the scaled plan is feasible.
- s0 and s1 are fixed a priori from the simulation scale: skill 0 means no better than
  persistence, and 0.30 means clearly skilful. They are not tuned on real outcomes.

The same scaling is offered for the low-pass filter baseline.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from publication_v2.stage31.battery import transition
from publication_v2.stage31.controllers import Decision
from publication_v2.stage33.controller import StochasticMPCConfig, decide_stochastic, released_skill_score

from .filters import FilterConfig, decide_filter


@dataclass(frozen=True)
class GradedConfig:
    base: object                 # StochasticMPCConfig or FilterConfig
    skill_zero: float = 0.0      # weight 0 at or below this skill
    skill_full: float = 0.30     # weight 1 at or above this skill


def weight(skill, config: GradedConfig) -> float:
    if skill is None:
        return 0.
    return min(1., max(0., (skill - config.skill_zero) / (config.skill_full - config.skill_zero)))


def _scale(decision: Decision, w: float, energy: float, battery) -> Decision:
    if decision.plan is None or w >= 1.:
        return decision
    if w <= 0.:
        return Decision(0., 0., decision.controller, 'skill_scaled_idle', decision.solver_status,
                        'graded switch weight 0', decision.computation_time_s, decision.optimization_failed,
                        False, None, {**decision.plan, 'charge_kw': [0.] * len(decision.plan['charge_kw']),
                                      'discharge_kw': [0.] * len(decision.plan['discharge_kw']),
                                      'energy_kwh': [energy] * len(decision.plan['energy_kwh'])})
    charges = [w * c for c in decision.plan['charge_kw']]
    discharges = [w * d for d in decision.plan['discharge_kw']]
    energies = [energy]
    for c, d in zip(charges, discharges):
        energies.append(transition(battery, energies[-1], c, d))
    plan = {**decision.plan, 'charge_kw': charges, 'discharge_kw': discharges, 'energy_kwh': energies}
    plan.pop('nominal_grid_kw', None)
    return Decision(charges[0], discharges[0], decision.controller, 'skill_scaled', decision.solver_status,
                    f'graded switch weight {w:.3f}', decision.computation_time_s, decision.optimization_failed,
                    decision.fallback, decision.fallback_reason, plan)


def _graded(decide, base, controller, forecast, decision_time, energy_kwh, previous_grid_kw, battery, config):
    from publication_v2.stage31.battery import BatteryConfig
    battery = BatteryConfig() if battery is None else battery
    decision = decide(controller, forecast, decision_time, energy_kwh, previous_grid_kw, battery, base)
    w = 0. if forecast is None else weight(released_skill_score(forecast), config)
    return _scale(decision, w, energy_kwh, battery)


def decide_graded_mpc(controller, forecast, decision_time, energy_kwh, previous_grid_kw, battery=None,
                      config: GradedConfig | None = None):
    """Unswitched stochastic MPC plan scaled by the graded skill weight."""
    return _graded(decide_stochastic, replace(config.base, skill_gate=None), controller, forecast, decision_time,
                   energy_kwh, previous_grid_kw, battery, config)


def decide_graded_filter(controller, forecast, decision_time, energy_kwh, previous_grid_kw, battery=None,
                         config: GradedConfig | None = None):
    """Low-pass filter action scaled by the graded skill weight."""
    return _graded(decide_filter, config.base, controller, forecast, decision_time, energy_kwh, previous_grid_kw,
                   battery, config)


decide_graded_filter.one_step = True


def decide_filter_gated(controller, forecast, decision_time, energy_kwh, previous_grid_kw, battery=None,
                        config: FilterConfig | None = None, gate: float = .10):
    """Low-pass filter behind the binary skill switch (same 0.10 threshold as Stage 3.3)."""
    skill = None if forecast is None else released_skill_score(forecast)
    if skill is None or skill <= gate:
        return decide_filter(controller, None, decision_time, energy_kwh, previous_grid_kw, battery, config)
    return decide_filter(controller, forecast, decision_time, energy_kwh, previous_grid_kw, battery, config)


decide_filter_gated.one_step = True
