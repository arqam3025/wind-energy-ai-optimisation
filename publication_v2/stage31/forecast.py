"""Explicit interval-mean forecast packet for synthetic MPC integration.

Target i is the END of the mean-power interval
[decision + i*step, decision + (i+1)*step). All power values are kW.
An uncertainty label is a contract, not proof of calibration or data admission.
No forecast model, dataset or private historical artifact is loaded here.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math


class ForecastError(ValueError):
    """Missing, unsupported or noncausal MPC forecast metadata."""


def _utc(value, name):
    if not isinstance(value, datetime):
        raise ForecastError(f'{name} requires an offset-aware datetime')
    try:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ForecastError(f'{name} requires an offset-aware datetime')
        return value.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError) as error:
        raise ForecastError(f'Invalid {name} timestamp') from error


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ForecastError(f'{name} must be a finite non-boolean number')
    try:
        valid = math.isfinite(float(value))
    except (OverflowError, TypeError, ValueError) as error:
        raise ForecastError(f'{name} cannot be represented as a finite number') from error
    if not valid:
        raise ForecastError(f'{name} must be a finite non-boolean number')


@dataclass(frozen=True)
class ForecastBundle:
    issue_time: datetime
    point_kw: tuple[float, ...]
    lower_kw: tuple[float, ...]
    upper_kw: tuple[float, ...]
    alpha: float
    provenance: str
    available_at: datetime
    target_times: tuple[datetime, ...]
    model_available_at: datetime
    calibration_newest_target_times: tuple[datetime | None, ...] = (None,) * 6
    calibration_available_ats: tuple[datetime | None, ...] = (None,) * 6
    uncertainty_kind: str = 'SYNTHETIC_INTERVALS'

    def validate(self, decision_time, step_minutes=10, horizon=6):
        """Validate the entire issued packet before any controller consumes it.

        Supplied calibration metadata is checked even for synthetic/point-only
        packets. A whole packet cannot be issued before any of its inputs exist.
        Different explicit timezone offsets are compared as UTC instants; naive
        or guessed clocks are never repaired. Frozen tuple fields prevent later
        mutation of validated numerical sequences.
        """
        if type(step_minutes) is not int or step_minutes <= 0:
            raise ForecastError('step_minutes must be a positive integer')
        if type(horizon) is not int or horizon <= 0:
            raise ForecastError('horizon must be a positive integer')
        decision = _utc(decision_time, 'decision_time')
        issue = _utc(self.issue_time, 'issue_time')
        available = _utc(self.available_at, 'available_at')
        model = _utc(self.model_available_at, 'model_available_at')
        if not model <= issue <= available <= decision:
            raise ForecastError('Model/issue/availability/decision chronology is invalid')
        if not isinstance(self.provenance, str) or not self.provenance or self.provenance.strip() != self.provenance:
            raise ForecastError('A nonempty explicit provenance string is required')
        if self.uncertainty_kind not in ('SYNTHETIC_INTERVALS', 'POINT_ONLY', 'CONFORMAL_MARGINAL'):
            raise ForecastError('Unsupported uncertainty kind')
        _finite(self.alpha, 'alpha')
        if not 0 < self.alpha < 1:
            raise ForecastError('alpha must lie strictly between zero and one')
        names = ('point_kw', 'lower_kw', 'upper_kw', 'target_times',
                 'calibration_newest_target_times', 'calibration_available_ats')
        for name in names:
            values = getattr(self, name)
            if not isinstance(values, tuple) or len(values) != horizon:
                raise ForecastError(f'{name} requires an immutable tuple of exactly {horizon} entries')
        for index in range(horizon):
            point, lower, upper = self.point_kw[index], self.lower_kw[index], self.upper_kw[index]
            for name, value in (('point_kw', point), ('lower_kw', lower), ('upper_kw', upper)):
                _finite(value, name)
            if not 0 <= lower <= point <= upper:
                raise ForecastError('Forecast bounds must satisfy 0 <= lower <= point <= upper')
            if self.uncertainty_kind == 'POINT_ONLY' and (lower != point or upper != point):
                raise ForecastError('POINT_ONLY requires identical point/lower/upper values')
            target = _utc(self.target_times[index], 'target_times')
            try:
                expected = decision + timedelta(minutes=(index + 1) * step_minutes)
            except (OverflowError, ValueError) as error:
                raise ForecastError('Forecast horizon exceeds representable time bounds') from error
            if target != expected or not issue <= decision < target:
                raise ForecastError('Forecast target is missing or misaligned with its interval end')
            newest = self.calibration_newest_target_times[index]
            ready = self.calibration_available_ats[index]
            if newest is None and ready is None:
                if self.uncertainty_kind == 'CONFORMAL_MARGINAL':
                    raise ForecastError('Conformal marginal bounds require complete calibration metadata')
                continue
            if newest is None or ready is None:
                raise ForecastError('Calibration target and availability metadata must be supplied together')
            newest = _utc(newest, 'calibration_newest_target_times')
            ready = _utc(ready, 'calibration_available_ats')
            if not newest < issue or not newest < decision:
                raise ForecastError('Calibration target must strictly precede packet issue and decision')
            if not newest <= ready <= issue or ready > available or ready > decision:
                raise ForecastError('Calibration residual was unavailable when the packet was issued')
