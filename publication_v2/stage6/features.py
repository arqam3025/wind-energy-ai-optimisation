"""Stage 6 forecast features: upstream sensing across the whole farm, and ramp-targeted labels.

All features at decision time t use only intervals ending at or before t (causal). They extend the
Stage 2 feature contract (``stage4.features.build``) for one target unit:

Upstream sensing (direction-aware)
    The farm wind direction theta(t) (circular mean of nacelle positions) gives each turbine j an
    upwind weight u_j = max(0, cos(bearing_j - theta))**4, where bearing_j is the bearing from the
    target to turbine j; turbines behind or beside the target get weight 0. The weighted averages
    of power, power change and wind speed of the upwind turbines describe what is about to reach
    the target. ``up_gap`` = upwind power - target power is the "incoming wave". ``up_lead_s`` is the
    weighted along-wind distance divided by the wind speed (seconds of warning).

Farm-wide state
    Total power change (10 and 30 min), the spread of power across turbines, and the fraction of
    turbines whose power changed by more than ``RAMP_KW`` in the last interval.

Ramp-targeted labels
    ``d_t+h`` = y(t+h) - y(t): the model predicts the change, and the forecast is y(t) + change.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from publication_v2.stage4.features import FEATURES, LABELS, build

from . import hill_of_towie as h

RAMP_KW = 200.0
SHARPNESS = 4
UPSTREAM = ['up_p', 'up_dp', 'up_dp3', 'up_w', 'up_dw', 'up_gap', 'up_weight', 'up_lead_s']
FARM = ['farm_dp', 'farm_dp3', 'farm_spread', 'farm_ramp_frac', 'dir_sin', 'dir_cos', 'p_std_60']
STAGE6_FEATURES = FEATURES + UPSTREAM + FARM
DELTA_LABELS = [f'd_{label[2:]}' for label in LABELS]  # 'd_t+10' ...


def upstream_weights(direction: pd.Series, target: str = h.TARGET) -> pd.DataFrame:
    """Upwind weight of every other turbine at each time (rows) from the farm direction (degrees)."""
    geo = h.geometry().drop(index=target)
    delta = np.deg2rad(geo['bearing_deg'].to_numpy()[None, :] - direction.to_numpy()[:, None])
    weights = np.clip(np.cos(delta), 0.0, None) ** SHARPNESS
    return pd.DataFrame(weights, index=direction.index, columns=geo.index)


def _weighted(values: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    v = values[weights.columns]
    w = weights.where(v.notna(), 0.0)
    total = w.sum(axis=1)
    return (v.fillna(0.0) * w).sum(axis=1) / total.where(total > 0)


def build_stage6(signals: dict, target: str = h.TARGET) -> pd.DataFrame:
    """Features (Stage 2 contract + upstream + farm) and level and delta labels for the target turbine."""
    frame = h.turbine_frame(signals, target)
    out = build(frame)
    labels = out[LABELS]
    out = out.drop(columns=LABELS)
    power = signals['power_kw'].clip(lower=0.0)
    wind = signals['wind_ms']
    direction = frame['wind_dir_deg']
    weights = upstream_weights(direction.fillna(0.0), target).where(direction.notna(), np.nan)
    geo = h.geometry().drop(index=target)
    out['up_p'] = _weighted(power, weights)
    out['up_dp'] = _weighted(power - power.shift(1), weights)
    out['up_dp3'] = _weighted(power - power.shift(3), weights)
    out['up_w'] = _weighted(wind, weights)
    out['up_dw'] = _weighted(wind - wind.shift(1), weights)
    out['up_gap'] = out['up_p'] - frame['realised_kw']
    out['up_weight'] = weights.sum(axis=1)
    along = (weights * geo['distance_m'].to_numpy()[None, :]).sum(axis=1) / weights.sum(axis=1).where(lambda s: s > 0)
    out['up_lead_s'] = along / out['up_w'].where(out['up_w'] > 0.5)
    farm = power.sum(axis=1, min_count=len(h.TURBINES))
    out['farm_dp'], out['farm_dp3'] = farm - farm.shift(1), farm - farm.shift(3)
    out['farm_spread'] = power.std(axis=1)
    changes = (power - power.shift(1)).abs()
    out['farm_ramp_frac'] = (changes > RAMP_KW).sum(axis=1) / changes.notna().sum(axis=1).where(lambda s: s > 0)
    radians = np.deg2rad(direction)
    out['dir_sin'], out['dir_cos'] = np.sin(radians), np.cos(radians)
    out['p_std_60'] = frame['realised_kw'].rolling(6, min_periods=6).std()
    if list(out.columns) != STAGE6_FEATURES:
        raise AssertionError('Stage 6 feature order changed')
    current = frame['realised_kw']
    deltas = pd.DataFrame({d: labels[label] - current for d, label in zip(DELTA_LABELS, LABELS, strict=True)})
    return pd.concat([out, labels, deltas], axis=1)
