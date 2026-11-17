"""Industry-style smoothing baselines for the 10-minute dispatch layer (Stage 5, exploratory).

Low-pass filter smoothing is the common forecast-free battery smoothing scheme: the grid follows
a first-order low-pass filtered version of the wind power, and the battery supplies the
difference. A state-of-charge (SOC) feedback term steers the battery back towards a reference
SOC so that it does not saturate [CITE: battery smoothing with low-pass filter and SOC feedback].

In discrete time, with the next-interval estimate ``p`` (the first forecast point; with
persistence this is the last measured value):

    target = g_prev + alpha * (p - g_prev) + k_soc * (E - E_ref) / dt
    battery net discharge = clip(target - p, power and energy limits)

- ``alpha = 1`` disables smoothing; smaller ``alpha`` smooths more.
- ``k_soc`` > 0 discharges when the battery is above its reference and charges when below.

The same interface as ``stage31.controllers.decide`` is used, so the closed-loop runner, battery
model and scoring are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from publication_v2.stage31.battery import BatteryConfig, transition
from publication_v2.stage31.controllers import Decision
from publication_v2.stage31.forecast import ForecastBundle


@dataclass(frozen=True)
class FilterConfig:
    alpha: float = .5          # low-pass gain per 10-minute step
    soc_gain: float = 1 / 6    # fraction of the SOC error corrected per step (about one hour)
    soc_reference: float = .65

    def __post_init__(self):
        if not 0 < self.alpha <= 1 or not 0 <= self.soc_gain <= 1 or not 0 < self.soc_reference < 1:
            raise ValueError('invalid filter configuration')


FILTER_VARIANTS = {
    'lowpass_fast': FilterConfig(alpha=.5),
    'lowpass_slow': FilterConfig(alpha=.25),
}


def _idle(controller, start, reason):
    return Decision(0., 0., controller, 'fallback', None, reason, perf_counter() - start, False, True, reason, None)


def decide_filter(controller: str, forecast: ForecastBundle | None, decision_time: datetime, energy_kwh: float,
                  previous_grid_kw: float, battery: BatteryConfig | None = None,
                  config: FilterConfig | None = None) -> Decision:
    start = perf_counter()
    battery = BatteryConfig() if battery is None else battery
    config = FilterConfig() if config is None else config
    if forecast is None:
        return _idle(controller, start, 'missing_forecast')
    forecast.validate(decision_time)
    point = float(forecast.point_kw[0])
    dt = battery.delta_t_hours
    reference = battery.capacity_kwh * config.soc_reference
    target = previous_grid_kw + config.alpha * (point - previous_grid_kw) + config.soc_gain * (energy_kwh - reference) / dt
    charge_cap = min(battery.max_charge_kw, max(0., (battery.max_energy_kwh - energy_kwh) / (battery.eta_charge * dt)))
    discharge_cap = min(battery.max_discharge_kw, max(0., (energy_kwh - battery.min_energy_kwh) * battery.eta_discharge / dt))
    net = min(max(target - point, -charge_cap), discharge_cap)
    charge, discharge = max(0., -net), max(0., net)
    next_energy = transition(battery, energy_kwh, charge, discharge)
    return Decision(charge, discharge, controller, 'filter', None, 'low-pass smoothing with SOC feedback; no solver',
                    perf_counter() - start, False, False, None,
                    {'horizon_steps': 1, 'charge_kw': [charge], 'discharge_kw': [discharge],
                     'energy_kwh': [energy_kwh, next_energy], 'nominal_grid_kw': [point + net]})


decide_filter.one_step = True  # plans one interval ahead (validated as a one-step plan)
