"""Battery energy and signed grid-exchange equations in kW/kWh.

Charge/discharge powers are nonnegative AC-side terminal powers. Positive signed
battery power is discharge. Positive grid exchange is export; negative is import.
All defaults are synthetic research assumptions, not installation specifications.
"""
from dataclasses import dataclass
import math


class PhysicalError(ValueError):
    """Nonphysical or unsupported simulation input."""


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PhysicalError(f"{name} must be a finite non-boolean number")
    try:
        result = float(value)
    except (OverflowError, ValueError, TypeError) as error:
        raise PhysicalError(f"{name} cannot be represented as a finite number") from error
    if not math.isfinite(result):
        raise PhysicalError(f"{name} must be a finite non-boolean number")
    return result


@dataclass(frozen=True)
class BatteryConfig:
    capacity_kwh: float = 2000.0
    max_charge_kw: float = 1000.0
    max_discharge_kw: float = 1000.0
    min_soc: float = 0.40
    max_soc: float = 0.90
    initial_soc: float = 0.65
    eta_charge: float = 0.95
    eta_discharge: float = 0.95
    step_minutes: int = 10

    def __post_init__(self):
        names = ('capacity_kwh', 'max_charge_kw', 'max_discharge_kw', 'min_soc',
                 'max_soc', 'initial_soc', 'eta_charge', 'eta_discharge')
        for name in names:
            _number(getattr(self, name), name)
        if self.capacity_kwh <= 0:
            raise PhysicalError('capacity_kwh must be positive')
        if self.max_charge_kw < 0 or self.max_discharge_kw < 0:
            raise PhysicalError('Terminal power limits must be nonnegative')
        if not 0 <= self.min_soc < self.max_soc <= 1:
            raise PhysicalError('SOC bounds must satisfy 0 <= min_soc < max_soc <= 1')
        if not self.min_soc <= self.initial_soc <= self.max_soc:
            raise PhysicalError('Initial SOC lies outside its declared bounds')
        if not 0 < self.eta_charge <= 1 or not 0 < self.eta_discharge <= 1:
            raise PhysicalError('Conversion efficiencies must lie in (0, 1]')
        if type(self.step_minutes) is not int or self.step_minutes <= 0:
            raise PhysicalError('step_minutes must be a positive integer')
        _number(self.step_minutes, 'step_minutes')

    @property
    def delta_t_hours(self):
        return self.step_minutes / 60.0

    @property
    def min_energy_kwh(self):
        return self.capacity_kwh * self.min_soc

    @property
    def max_energy_kwh(self):
        return self.capacity_kwh * self.max_soc

    @property
    def initial_energy_kwh(self):
        return self.capacity_kwh * self.initial_soc

    @property
    def usable_energy_kwh(self):
        return self.max_energy_kwh - self.min_energy_kwh


def transition(config, energy_kwh, charge_kw, discharge_kw, tolerance=1e-6):
    """Return raw next energy; never clip a command or SOC to make it feasible.

    E_next = E + eta_charge * P_charge * dt - P_discharge * dt / eta_discharge.
    The declared absolute tolerance accepts only numerical boundary residuals;
    it does not change returned energy. Negative power commands remain invalid.
    Both terminal powers exceeding tolerance constitute simultaneous operation.
    """
    if not isinstance(config, BatteryConfig):
        raise PhysicalError('BatteryConfig is required')
    energy = _number(energy_kwh, 'energy_kwh')
    charge = _number(charge_kw, 'charge_kw')
    discharge = _number(discharge_kw, 'discharge_kw')
    tol = _number(tolerance, 'tolerance')
    if tol < 0:
        raise PhysicalError('tolerance must be nonnegative')
    if charge < 0 or discharge < 0:
        raise PhysicalError('Charge and discharge commands must be nonnegative')
    if charge > config.max_charge_kw + tol or discharge > config.max_discharge_kw + tol:
        raise PhysicalError('Terminal battery power limit exceeded')
    if charge > tol and discharge > tol:
        raise PhysicalError('Simultaneous charging and discharging is prohibited')
    if not config.min_energy_kwh - tol <= energy <= config.max_energy_kwh + tol:
        raise PhysicalError('Initial battery energy violates SOC constraints')
    result = energy + config.eta_charge * charge * config.delta_t_hours - discharge * config.delta_t_hours / config.eta_discharge
    if not math.isfinite(result):
        raise PhysicalError('Battery energy update is nonfinite')
    if not config.min_energy_kwh - tol <= result <= config.max_energy_kwh + tol:
        raise PhysicalError('Next battery energy violates SOC constraints')
    return result


def grid_export(wind_kw, charge_kw, discharge_kw):
    """Signed grid exchange: wind - charge + discharge (kW).

    Positive means export and negative means import. Grid limits, battery limits
    and SOC constraints belong to the controller/plant, not this balance identity.
    """
    wind = _number(wind_kw, 'wind_kw')
    charge = _number(charge_kw, 'charge_kw')
    discharge = _number(discharge_kw, 'discharge_kw')
    if wind < 0 or charge < 0 or discharge < 0:
        raise PhysicalError('Wind and terminal battery powers must be nonnegative')
    result = wind - charge + discharge
    if not math.isfinite(result):
        raise PhysicalError('Grid exchange is nonfinite')
    return result


def ramp_metrics(grid_kw, previous_grid_kw, limit_kw=200.0):
    """Return (absolute ramp, positive threshold exceedance), both in kW.

    The reference is a ramp per control interval, not kW/minute. Signed import
    and export are permitted; threshold equality has zero exceedance.
    """
    grid = _number(grid_kw, 'grid_kw')
    previous = _number(previous_grid_kw, 'previous_grid_kw')
    limit = _number(limit_kw, 'limit_kw')
    if limit < 0:
        raise PhysicalError('Ramp reference must be nonnegative')
    magnitude = abs(grid - previous)
    if not math.isfinite(magnitude):
        raise PhysicalError('Grid ramp is nonfinite')
    return magnitude, max(0.0, magnitude - limit)
