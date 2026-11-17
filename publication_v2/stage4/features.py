"""Causal features and six-horizon labels on the interval-END index (Stage 4, real data).

The feature set is the Stage 2 contract (``publication_v2.protocol.FEATURE_SUPPORT``), fixed before
any Kelmarsh data was opened: 14 features, in that order. For a decision at time d (an interval
end), each feature uses only values whose interval ends at or before d, at exactly the support
offsets declared in the contract. The labels are the realised interval means ending at
d + 10, ..., d + 60 min. Column 0 (``power_kw`` = y(d)) is the persistence anchor.

Rows with any missing feature or label are dropped. Nothing is imputed.
"""
from __future__ import annotations

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
