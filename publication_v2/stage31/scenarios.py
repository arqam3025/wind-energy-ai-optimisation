"""Explicitly synthetic traces; forecasting receives past observations only."""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import math
import random
from .forecast import ForecastBundle

START = datetime(2031, 1, 1, tzinfo=timezone.utc)

@dataclass(frozen=True)
class SyntheticScenario:
    name: str
    wind_kw: tuple[float, ...]
    initial_history_kw: tuple[float, ...]
    seed: int
    initial_soc: float = .65
    forecast_bias_kw: float = 0.
    base_width_kw: float = 100.
    width_growth_kw: float = 20.
    faults: tuple[tuple[int, str], ...] = ()
    grid_min_kw: float | None = None
    grid_max_kw: float | None = None


def make_scenarios(seed: int = 20261110, steps: int = 24) -> tuple[SyntheticScenario, ...]:
    if isinstance(seed, bool) or not isinstance(seed, int) or isinstance(steps, bool) or not isinstance(steps, int) or steps < 8:
        raise ValueError('Integer seed and at least eight synthetic intervals required')
    scenarios = []
    names = ('stable', 'gradual_increase', 'gradual_decrease', 'sudden_ramps',
             'forecast_bias', 'high_uncertainty', 'low_initial_soc', 'high_initial_soc',
             'invalid_forecasts', 'conflicting_constraints')
    for number, name in enumerate(names):
        rng = random.Random(seed + 10007 * number)
        history = (1000.,) * 6
        actual = []
        for i in range(steps):
            if name == 'stable': value = 1000.
            elif name == 'gradual_increase': value = 500. + 35. * i + rng.uniform(-10, 10)
            elif name == 'gradual_decrease': value = max(150., 1800. - 35. * i) + rng.uniform(-10, 10)
            elif name in ('sudden_ramps', 'forecast_bias', 'high_uncertainty'):
                level = (600., 1750., 400., 1500.)[min(3, 4 * i // steps)]
                value = level + rng.uniform(-10, 10)
            elif name == 'conflicting_constraints': value = 1800.
            else: value = 1000. + 80. * math.sin(i / 3.) + rng.uniform(-10, 10)
            actual.append(max(0., value))
        if name == 'gradual_increase': history = tuple(500. - 35. * (5-i) for i in range(6))
        elif name == 'gradual_decrease': history = tuple(1800. + 35. * (5-i) for i in range(6))
        elif name in ('sudden_ramps', 'forecast_bias', 'high_uncertainty'): history = (600.,) * 6
        elif name == 'conflicting_constraints': history = (1800.,) * 6
        scenarios.append(SyntheticScenario(name, tuple(actual), history, seed + 10007 * number,
            initial_soc=.40 if name == 'low_initial_soc' else .90 if name == 'high_initial_soc' else .65,
            forecast_bias_kw=350. if name == 'forecast_bias' else 0.,
            base_width_kw=500. if name == 'high_uncertainty' else 100.,
            width_growth_kw=80. if name == 'high_uncertainty' else 20.,
            faults=((steps//4, 'missing'), (steps//2, 'future_availability'), (3*steps//4, 'invalid_interval')) if name == 'invalid_forecasts' else (),
            grid_min_kw=0. if name == 'conflicting_constraints' else None,
            grid_max_kw=400. if name == 'conflicting_constraints' else None))
    return tuple(scenarios)


def past_only_forecast(past_wind_kw: tuple[float, ...], decision_time: datetime, *,
                       seed: int, decision_index: int, bias_kw: float = 0.,
                       base_width_kw: float = 100., width_growth_kw: float = 20.,
                       step_minutes: float = 10.) -> ForecastBundle:
    """Predeclared analytic fixture, NOT XGBoost or conformal calibration.

    Each value forecasts interval-average generation for [d+i*dt,d+(i+1)*dt).
    The timestamp is that interval's endpoint. Past interval observations become
    available at their endpoints with explicitly assumed zero synthetic latency.
    No current/future realized wind argument is accepted.
    """
    if not past_wind_kw or any(not math.isfinite(x) or x < 0 for x in past_wind_kw):
        raise ValueError('Finite nonnegative released history required')
    if not math.isfinite(bias_kw) or not math.isfinite(base_width_kw) or base_width_kw < 0 or not math.isfinite(width_growth_kw) or width_growth_kw < 0:
        raise ValueError('Invalid synthetic forecast parameters')
    rng = random.Random(seed + 32452843 + 49999 * decision_index)
    last = past_wind_kw[-1]
    trend = max(-100., min(100., last - past_wind_kw[-2])) if len(past_wind_kw) > 1 else 0.
    recent = past_wind_kw[-6:]
    variation = sum(abs(b-a) for a,b in zip(recent, recent[1:])) / max(1, len(recent)-1)
    point = tuple(max(0., last + trend * min(h+1, 3) + bias_kw + rng.uniform(-8, 8)) for h in range(6))
    widths = tuple(base_width_kw + (h+1)*width_growth_kw + .15*variation for h in range(6))
    return ForecastBundle(issue_time=decision_time, available_at=decision_time,
        model_available_at=START-timedelta(days=1), point_kw=point,
        lower_kw=tuple(max(0., p-w) for p,w in zip(point,widths)),
        upper_kw=tuple(p+w for p,w in zip(point,widths)), alpha=.1,
        target_times=tuple(decision_time+timedelta(minutes=step_minutes*(h+1)) for h in range(6)),
        provenance='SYNTHETIC_PAST_ONLY_ANALYTIC_RULE_V1;seed='+str(seed),
        uncertainty_kind='SYNTHETIC_INTERVALS')


def forecast_for_step(scenario: SyntheticScenario, past_wind_kw: tuple[float, ...],
                      decision_time: datetime, index: int, *, step_minutes: float = 10.):
    # Access only prespecified scenario parameters, never scenario.wind_kw here.
    packet = past_only_forecast(past_wind_kw, decision_time, seed=scenario.seed,
        decision_index=index, bias_kw=scenario.forecast_bias_kw,
        base_width_kw=scenario.base_width_kw, width_growth_kw=scenario.width_growth_kw,
        step_minutes=step_minutes)
    fault = dict(scenario.faults).get(index)
    if fault == 'missing': return None, fault
    if fault == 'future_availability': packet = replace(packet, available_at=decision_time+timedelta(minutes=1))
    elif fault == 'invalid_interval': packet = replace(packet, lower_kw=(packet.upper_kw[0]+1.,)+packet.lower_kw[1:])
    return packet, fault
