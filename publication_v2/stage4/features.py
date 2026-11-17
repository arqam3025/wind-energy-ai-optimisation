"""Causal features and six-horizon labels on the interval-END index (Stage 4, real data).

The feature set is the Stage 2 contract (``publication_v2.protocol.FEATURE_SUPPORT``), fixed before
any Kelmarsh data was opened: 14 features, in that order. For a decision at time d (an interval
end), each feature uses only values whose interval ends at or before d, at exactly the support
offsets declared in the contract. The labels are the realised interval means ending at
d + 10, ..., d + 60 min. Column 0 (``power_kw`` = y(d)) is the persistence anchor.

Rows with any missing feature or label are dropped. Nothing is imputed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from publication_v2.protocol import FEATURE_SUPPORT, HORIZONS

FEATURES = list(FEATURE_SUPPORT)
LABELS = [f'y_t+{h}' for h in HORIZONS]


def build(frame: pd.DataFrame) -> pd.DataFrame:
    """Features and labels for every decision time in ``frame`` (one continuous 10-minute grid)."""
    steps = frame.index.to_series().diff().dropna()
    if not frame.index.is_monotonic_increasing or (steps != pd.Timedelta(minutes=10)).any():
        raise ValueError('frame must be one continuous 10-minute grid')
    y, ws, wd = frame['realised_kw'], frame['wind_ms'], frame['wind_dir_deg']
    out = pd.DataFrame(index=frame.index)
    out['power_kw'], out['wind_speed'], out['wind_direction'] = y, ws, wd
    for kind, series in (('power', y), ('wind', ws)):
        for lag in (10, 20, 30, 60):
            out[f'{kind}_lag_{lag}min'] = series.shift(lag // 10)
    out['power_change_10min'] = y - y.shift(1)
    out['wind_change_10min'] = ws - ws.shift(1)
    out['power_mean_40min'] = y.rolling(4, min_periods=4).mean()
    if list(out.columns) != FEATURES:
        raise AssertionError('feature order differs from the Stage 2 contract')
    for i, label in enumerate(LABELS):
        out[label] = y.shift(-(i + 1))
    return out


def complete(table: pd.DataFrame) -> pd.DataFrame:
    return table.dropna(subset=FEATURES + LABELS)


NEIGHBOURS = (2, 3, 4, 5, 6)
SPATIAL = [f't{t}_{k}' for t in NEIGHBOURS for k in ('p', 'dp', 'dp3', 'w', 'dw')] + [
    'farm_dp', 'farm_dp3', 'dir_sin', 'dir_cos', 'p_std_60']
SPATIAL_FEATURES = FEATURES + SPATIAL


def build_spatial(frames: dict[int, pd.DataFrame]) -> pd.DataFrame:
    """Stage 2 features of turbine 1 plus causal neighbour-turbine features (selected in round 2).

    Every added feature uses values whose interval ends at or before the decision time:
    neighbour power, wind and their 10/30-minute changes, farm-total power changes, the wind
    direction of turbine 1 (sin/cos) and the 60-minute standard deviation of turbine 1 power.
    A missing value in any turbine makes the row incomplete; nothing is imputed.
    """
    target = frames[1]
    out = build(target)
    labels = out[LABELS]
    out = out.drop(columns=LABELS)
    for t in NEIGHBOURS:
        f = frames[t]
        if not f.index.equals(target.index):
            raise ValueError('turbine frames must share one grid')
        p, w = f['realised_kw'], f['wind_ms']
        out[f't{t}_p'], out[f't{t}_dp'], out[f't{t}_dp3'] = p, p - p.shift(1), p - p.shift(3)
        out[f't{t}_w'], out[f't{t}_dw'] = w, w - w.shift(1)
    farm = sum(frames[t]['realised_kw'] for t in (1, *NEIGHBOURS))
    out['farm_dp'], out['farm_dp3'] = farm - farm.shift(1), farm - farm.shift(3)
    direction = np.deg2rad(target['wind_dir_deg'])
    out['dir_sin'], out['dir_cos'] = np.sin(direction), np.cos(direction)
    out['p_std_60'] = target['realised_kw'].rolling(6, min_periods=6).std()
    if list(out.columns) != SPATIAL_FEATURES:
        raise AssertionError('spatial feature order changed')
    return pd.concat([out, labels], axis=1)
