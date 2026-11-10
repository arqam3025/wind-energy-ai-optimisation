"""Horizon-specific causal absolute-residual calibration.

Static/rolling finite-sample ranks are split-conformal constructions only under
the usual appropriate exchangeability assumptions. Those assumptions are not
asserted for this dependent wind series. The recency-weighted alternative is a
declared time-decay heuristic, not a new coverage theorem. Its test-point mass
at infinity follows the weighted-quantile construction; arbitrary temporal
weights do not establish the covariate-shift or exchangeability assumptions.

Primary background: https://arxiv.org/abs/2202.13415 and
https://doi.org/10.1214/23-AOS2276 . No uncertainty method may read an unavailable
observation merely because its value is present in an offline table.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import math
from collections.abc import Sequence

from publication_v2.protocol import (ChronologyError, Residual, finite, horizon,
                                     model_identity, timestamp, validate_grid, validate_residual)

METHODS = ("static", "rolling", "weighted")


class CalibrationError(ValueError):
    """Calibration is malformed, unavailable, or cannot yield a finite interval."""


class InsufficientCalibration(CalibrationError):
    """The declared finite interval is unsupported by available residuals."""


@dataclass(frozen=True)
class CalibrationConfig:
    alpha: float = 0.10
    window: int = 144
    half_life_minutes: float = 1440.0
    floor_kw: float = 0.0
    min_samples: int = 9

    def __post_init__(self) -> None:
        finite(self.alpha, self.half_life_minutes, self.floor_kw)
        if not 0 < self.alpha < 1:
            raise CalibrationError("alpha must lie strictly between zero and one")
        if type(self.window) is not int or type(self.min_samples) is not int or not 1 <= self.min_samples <= self.window:
            raise CalibrationError("window and min_samples must be positive integers with window >= min_samples")
        if self.half_life_minutes <= 0 or self.floor_kw < 0:
            raise CalibrationError("half-life must be positive and floor nonnegative")


@dataclass(frozen=True)
class CalibrationResult:
    method: str
    horizon_minutes: int
    model_sha256: str
    decision_time: datetime
    alpha: float
    quantile_kw: float
    margin_kw: float
    floor_kw: float
    floor_binding: bool
    selected_count: int
    eligible_count_before_window: int
    effective_n: float
    total_calibration_weight: float
    rank: int | None
    selected_origin_times: tuple[datetime, ...]
    selected_target_times: tuple[datetime, ...]
    exclusions: tuple[dict, ...]
    other_horizon_records: int
    other_model_records: int

    @property
    def newest_target_time(self) -> datetime:
        return max(self.selected_target_times)

    def interval(self, prediction_kw: float) -> tuple[float, float]:
        finite(prediction_kw)
        if prediction_kw < 0:
            raise CalibrationError("Nonnegative-power prediction required for the declared clipped interval")
        return max(0.0, float(prediction_kw) - self.margin_kw), float(prediction_kw) + self.margin_kw

    def as_dict(self) -> dict:
        result = asdict(self)
        result["decision_time"] = self.decision_time.isoformat()
        result["selected_origin_times"] = [t.isoformat() for t in self.selected_origin_times]
        result["selected_target_times"] = [t.isoformat() for t in self.selected_target_times]
        result["newest_target_time"] = self.newest_target_time.isoformat()
        result["coverage_claim"] = "descriptive under temporal dependence; no guaranteed coverage asserted"
        result["interval_type"] = "two_sided_absolute_residual_nonnegative_support"
        return result


def finite_sample_quantile(scores: Sequence[float], alpha: float) -> tuple[float, int]:
    """Exact order statistic; never interpolate or cap an infinite rank."""
    finite(alpha)
    if not 0 < alpha < 1 or len(scores) == 0:
        raise InsufficientCalibration("Nonempty scores and alpha in (0,1) are required")
    for score in scores:
        finite(score)
        if score < 0:
            raise CalibrationError("Absolute-residual scores cannot be negative")
    rank = math.ceil((len(scores) + 1) * (1 - alpha))
    if rank > len(scores):
        raise InsufficientCalibration("Finite-sample rank reaches the test point at infinity")
    return float(sorted(scores)[rank - 1]), rank


def _weighted_quantile(scores: Sequence[float], weights: Sequence[float], alpha: float) -> tuple[float, float, float]:
    # The new/test observation has weight one and score +infinity.
    total = math.fsum(weights)
    square_sum = math.fsum(w*w for w in weights)
    if total <= 0 or square_sum <= 0:
        raise InsufficientCalibration("Temporal weights underflow; no positive calibration mass")
    threshold = (1 - alpha) * (total + 1.0)
    if threshold > total:
        raise InsufficientCalibration("Weighted test-point mass implies an infinite quantile")
    cumulative = 0.0
    for score, weight in sorted(zip(scores, weights)):
        cumulative += weight
        if cumulative >= threshold:
            return float(score), total*total/square_sum, total
    # No finite upper endpoint is fabricated if floating arithmetic cannot hit it.
    raise InsufficientCalibration("Finite weighted quantile could not be established")


def _residual_metadata(record: Residual) -> tuple[datetime, datetime, datetime, datetime, datetime]:
    """Validate structural evidence without reading either numerical outcome.

    A candidate can be well formed but unavailable at a particular decision.
    Such candidates must still have valid issuance, receipt and model clocks,
    even when their model/horizon will not be used by this calibration call.
    The decision-dependent eligibility boundary is deliberately applied later.
    """
    if not isinstance(record, Residual):
        raise CalibrationError("Every candidate requires a complete Stage 1 Residual ledger")
    try:
        origin, issued, target, observed_at, residual_at, trained_through, model_at, anchor = map(
            timestamp, (record.origin_time, record.issued_at, record.target_time,
                        record.observation_available_at, record.residual_available_at,
                        record.model_latest_training_target, record.model_available_at,
                        record.grid_anchor))
        step = horizon(record.horizon_minutes)
        model_identity(record.model_sha256)
        validate_grid((origin, target), allow_gaps=True, anchor=anchor)
        if target != origin + timedelta(minutes=step) or not origin <= issued < target:
            raise ChronologyError("Residual forecast/target alignment violated")
        if not target <= observed_at <= residual_at or residual_at < issued:
            raise ChronologyError("Residual observation/computation clocks precede their inputs")
        if not trained_through < origin or not trained_through <= model_at <= issued:
            raise ChronologyError("Calibration forecast model is not historically eligible")
    except ChronologyError as error:
        raise CalibrationError(f"Invalid calibration metadata: {error}") from error
    return origin, target, observed_at, residual_at, anchor


def calibrate(records: Sequence[Residual], decision_time: datetime, horizon_minutes: int,
              method: str, model_sha256: str,
              config: CalibrationConfig = CalibrationConfig()) -> CalibrationResult:
    """Admit only available residuals from one horizon and one model identity.

    Static calibration rejects any ineligible member of its declared fixed set.
    All candidates undergo metadata validation before eligibility filtering.
    Rolling/weighted modes explicitly exclude unavailable candidates before
    reading observed or prediction values. Unknown/malformed evidence fails
    closed, including records belonging to a different model or horizon.
    Caller supplies only the predeclared static set for ``static`` and the
    predeclared update-history ledger for adaptive modes; no set is selected by
    coverage or forecasting performance.
    """
    decision = timestamp(decision_time)
    horizon(horizon_minutes)
    model_identity(model_sha256)
    if method not in METHODS:
        raise CalibrationError(f"Unknown calibration method: {method}")
    if not isinstance(config, CalibrationConfig):
        raise CalibrationError("CalibrationConfig required")
    if not records:
        raise InsufficientCalibration("Calibration history is empty")
    # Complete the metadata-only pass before inspecting any candidate's values.
    metadata = [_residual_metadata(record) for record in records]
    eligible, exclusions, seen, anchors = [], [], set(), set()
    other_horizon, other_model = 0, 0
    for record, (origin, target, observation_available, residual_available, anchor) in zip(records, metadata):
        key = (record.model_sha256, origin, record.horizon_minutes)
        if key in seen:
            raise CalibrationError("Duplicate calibration model/origin/horizon identity")
        seen.add(key)
        if record.model_sha256 != model_sha256:
            other_model += 1
            continue
        if record.horizon_minutes != horizon_minutes:
            other_horizon += 1
            continue
        anchors.add(anchor)
        reasons = []
        if target >= decision:
            reasons.append("target_not_strictly_before_decision")
        if observation_available > decision:
            reasons.append("observation_not_available")
        if residual_available > decision:
            reasons.append("residual_not_available")
        if reasons:
            rejection = {"origin_time": origin.isoformat(), "target_time": target.isoformat(),
                         "reasons": reasons}
            if method == "static":
                raise CalibrationError(f"Fixed calibration contains an ineligible residual: {rejection}")
            exclusions.append(rejection)
            continue  # Never inspect an unavailable observed value or score.
        try:
            validate_residual(record, decision)
        except ChronologyError as error:
            raise CalibrationError(f"Invalid calibration chronology: {error}") from error
        if record.prediction_kw < 0 or record.observed_kw < 0:
            raise CalibrationError("Declared nonnegative physical-power support violated")
        eligible.append(record)
    if len(anchors) > 1:
        raise CalibrationError("One shared calibration grid anchor is required")
    eligible.sort(key=lambda r: (timestamp(r.target_time), timestamp(r.origin_time)))
    count = len(eligible)
    selected = eligible if method == "static" else eligible[-config.window:]
    if len(selected) < config.min_samples:
        raise InsufficientCalibration(f"Only {len(selected)} eligible horizon-specific residuals; need {config.min_samples}")
    scores = [abs(float(r.prediction_kw) - float(r.observed_kw)) for r in selected]
    if method == "weighted":
        ages_minutes = [(decision-timestamp(r.target_time)).total_seconds()/60 for r in selected]
        weights = [math.exp2(-age/config.half_life_minutes) for age in ages_minutes]
        quantile, effective_n, total_weight = _weighted_quantile(scores, weights, config.alpha)
        rank = None
    else:
        quantile, rank = finite_sample_quantile(scores, config.alpha)
        effective_n = total_weight = float(len(selected))
    margin = max(config.floor_kw, quantile)
    return CalibrationResult(method, horizon_minutes, model_sha256, decision, config.alpha,
        quantile, margin, config.floor_kw, bool(config.floor_kw > 0 and config.floor_kw >= quantile),
        len(selected), count, effective_n, total_weight, rank,
        tuple(timestamp(r.origin_time) for r in selected), tuple(timestamp(r.target_time) for r in selected),
        tuple(exclusions), other_horizon, other_model)
