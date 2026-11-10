"""Normative information-time contracts; naive historical clocks cannot pass."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import re
from collections.abc import Mapping, Sequence

HORIZONS = (10, 20, 30, 40, 50, 60)
FEATURE_SUPPORT = {
    'power_kw': (0,), 'wind_speed': (0,), 'wind_direction': (0,),
    **{f'{kind}_lag_{lag}min': (lag,) for kind in ('power', 'wind') for lag in (10, 20, 30, 60)},
    'power_change_10min': (0, 10), 'wind_change_10min': (0, 10), 'power_mean_40min': (0, 10, 20, 30),
}


class ChronologyError(ValueError):
    """Missing or inconsistent chronology/availability evidence."""


def timestamp(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ChronologyError('Offset-aware datetime required; unknown timezone cannot be guessed')
    return value.astimezone(timezone.utc)


def horizon(value: int) -> int:
    if type(value) is not int or value not in HORIZONS:
        raise ChronologyError('Horizon must be one of 10,20,30,40,50,60 minutes')
    return value


def finite(*values: float) -> None:
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in values):
        raise ChronologyError('Required numeric value is missing or non-finite')


def model_identity(value: str) -> None:
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ChronologyError('Authenticated SHA256 model identity required')


@dataclass(frozen=True)
class Feature:
    name: str
    value: float
    source_times: tuple[datetime, ...]
    available_at: datetime
    source_available_ats: tuple[datetime, ...]


@dataclass(frozen=True)
class Forecast:
    origin_time: datetime
    issued_at: datetime
    decision_time: datetime
    target_time: datetime
    horizon_minutes: int
    prediction_kw: float
    features: tuple[Feature, ...]
    model_sha256: str
    model_latest_training_target: datetime
    model_available_at: datetime
    grid_anchor: datetime


@dataclass(frozen=True)
class Residual:
    origin_time: datetime
    issued_at: datetime
    target_time: datetime
    horizon_minutes: int
    prediction_kw: float
    observed_kw: float
    observation_available_at: datetime
    residual_available_at: datetime
    model_sha256: str
    model_latest_training_target: datetime
    model_available_at: datetime
    grid_anchor: datetime


def validate_features(features: Sequence[Feature], origin: datetime, issued: datetime) -> None:
    origin, issued = timestamp(origin), timestamp(issued)
    if len(features) != len(FEATURE_SUPPORT) or {f.name for f in features} != set(FEATURE_SUPPORT):
        raise ChronologyError('All fourteen features are required exactly once')
    for feature in features:
        finite(feature.value)
        available = timestamp(feature.available_at)
        sources = tuple(timestamp(t) for t in feature.source_times)
        expected = tuple(origin - timedelta(minutes=m) for m in FEATURE_SUPPORT[feature.name])
        if len(set(sources)) != len(sources) or set(sources) != set(expected):
            raise ChronologyError(f'Missing, future or incorrectly aligned feature support: {feature.name}')
        receipts = tuple(timestamp(t) for t in feature.source_available_ats)
        if len(receipts) != len(sources) or any(not event <= receipt <= available for event, receipt in zip(sources, receipts)):
            raise ChronologyError(f'Missing or inconsistent source availability: {feature.name}')
        if not max(sources) <= available <= origin <= issued:
            raise ChronologyError(f'Feature availability invalid: {feature.name}')


def validate_forecast(record: Forecast) -> None:
    origin, issued, decision, target = map(timestamp, (record.origin_time, record.issued_at,
                                                     record.decision_time, record.target_time))
    step = horizon(record.horizon_minutes)
    validate_grid((origin, target), allow_gaps=True, anchor=record.grid_anchor)
    finite(record.prediction_kw)
    model_identity(record.model_sha256)
    if target != origin + timedelta(minutes=step) or not origin <= issued <= decision < target:
        raise ChronologyError('Forecast origin/issue/decision/target alignment violated')
    if not timestamp(record.model_latest_training_target) < origin:
        raise ChronologyError('Model training target reaches forecast origin')
    if not timestamp(record.model_latest_training_target) <= timestamp(record.model_available_at) <= issued:
        raise ChronologyError('Model availability precedes its labels or follows issuance')
    validate_features(record.features, origin, issued)


def validate_residual(record: Residual, decision_time: datetime) -> None:
    origin, issued, target, available, residual_available, decision = map(timestamp, (record.origin_time,
        record.issued_at, record.target_time, record.observation_available_at, record.residual_available_at,
        decision_time))
    finite(record.prediction_kw, record.observed_kw)
    step = horizon(record.horizon_minutes)
    validate_grid((origin, target), allow_gaps=True, anchor=record.grid_anchor)
    model_identity(record.model_sha256)
    if target != origin + timedelta(minutes=step) or not origin <= issued < target:
        raise ChronologyError('Residual forecast/target alignment violated')
    if not target < decision:
        raise ChronologyError('Calibration target must be strictly before decision; equality/future rejected')
    if not target <= available <= decision:
        raise ChronologyError('Calibration observation was not available by decision')
    if not max(issued, available) <= residual_available <= decision:
        raise ChronologyError('Residual was computed before its inputs or after decision')
    training, model_available = map(timestamp, (record.model_latest_training_target, record.model_available_at))
    if not training < origin or not training <= model_available <= issued:
        raise ChronologyError('Calibration forecast model is not historically eligible')


def validate_calibration(records: Sequence[Residual], decision_time: datetime) -> None:
    if not records:
        raise ChronologyError('Calibration history is empty')
    keys = set()
    anchors = {timestamp(record.grid_anchor) for record in records}
    if len(anchors) != 1:
        raise ChronologyError('Calibration records must share one declared cohort grid anchor')
    for record in records:
        key = (timestamp(record.origin_time), horizon(record.horizon_minutes))
        if key in keys:
            raise ChronologyError('Duplicated calibration origin/horizon')
        keys.add(key)
        validate_residual(record, decision_time)


def validate_grid(times: Sequence[datetime], *, allow_gaps: bool = False,
                  anchor: datetime | None = None) -> None:
    values = [timestamp(t) for t in times]
    if not values or len(values) != len(set(values)) or values != sorted(values):
        raise ChronologyError('Times must be nonempty, unique and sorted; no silent repair')
    reference = timestamp(anchor) if anchor is not None else datetime(1970, 1, 1, tzinfo=timezone.utc)
    for value in values:
        if (value-reference).total_seconds() % 600:
            raise ChronologyError('Timestamp is not on the declared ten-minute grid')
    differences = [b-a for a,b in zip(values, values[1:])]
    if not allow_gaps and any(delta != timedelta(minutes=10) for delta in differences):
        raise ChronologyError('Missing ten-minute observation; gaps must be declared explicitly')


def embargo_projection(origins: Sequence[datetime], boundary: datetime,
                       horizons_minutes: Sequence[int] = HORIZONS, *,
                       grid_anchor: datetime | None = None) -> dict[int, dict]:
    """Describe retained/rejected origins per horizon without altering any data."""
    validate_grid(origins, allow_gaps=True, anchor=grid_anchor)
    first_decision = timestamp(boundary)
    if not horizons_minutes or len(set(horizons_minutes)) != len(horizons_minutes):
        raise ChronologyError('Nonempty distinct horizons required')
    result = {}
    for h in horizons_minutes:
        horizon(h)
        keep = [t for t in origins if timestamp(t) + timedelta(minutes=h) < first_decision]
        reject = [t for t in origins if timestamp(t) + timedelta(minutes=h) >= first_decision]
        result[h] = {'retained_origins': keep, 'embargoed_origins': reject}
    return result


def validate_splits(splits: Mapping[str, Sequence[datetime]],
                    order: Sequence[str] = ('train', 'calibration', 'development', 'test'),
                    horizons_by_role: Mapping[str, Sequence[int]] | None = None, *,
                    grid_anchor: datetime | None = None) -> None:
    """Reject cross-role target intersections and horizon-specific boundary leaks."""
    if set(splits) != set(order) or len(order) != len(set(order)):
        raise ChronologyError('Every declared chronological role is required exactly once')
    previous_targets, previous_origins = set(), set()
    previous_latest_target = None
    for role in order:
        values = [timestamp(t) for t in splits[role]]
        validate_grid(values, allow_gaps=True, anchor=grid_anchor)
        hs = HORIZONS if horizons_by_role is None else horizons_by_role.get(role, ())
        if not hs or len(set(hs)) != len(hs):
            raise ChronologyError(f'Missing or duplicate horizons: {role}')
        for h in hs:
            horizon(h)
        targets = {t+timedelta(minutes=h) for t in values for h in hs}
        if previous_origins.intersection(values) or previous_targets.intersection(targets):
            raise ChronologyError(f'Cross-split origin/target overlap: {role}')
        if previous_latest_target is not None and not previous_latest_target < min(values):
            raise ChronologyError(f'Horizon-specific embargo violated before {role}')
        previous_targets.update(targets)
        previous_origins.update(values)
        previous_latest_target = max(targets)
