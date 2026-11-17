"""Causal six-horizon adaptive wind forecast uncertainty.

Development-only experimental module.

Every residual must have target timestamp strictly earlier
than the MPC decision timestamp.
"""

import numpy as np
import pandas as pd


ALPHA = 0.10
WINDOW = 144
POST_GAP_MINIMUM = 72
GAP_START = pd.Timestamp("2018-10-31 16:50:00")

STATIC_FLOORS_KW = np.array([
    358.379810,
    504.728717,
    571.614234,
    630.176420,
    690.977755,
    731.661882,
], dtype=float)


def conformal_quantile(values, alpha=ALPHA):
    values = np.asarray(values, dtype=float)

    if values.ndim != 1 or len(values) == 0:
        raise ValueError("Expected nonempty 1D residual array")

    if not np.isfinite(values).all():
        raise ValueError("Non-finite residual")

    n = len(values)
    rank = int(np.ceil((n + 1) * (1 - alpha)))

    if rank > n:
        raise ValueError("Insufficient samples for quantile")

    return float(np.partition(values, rank - 1)[rank - 1])


class CausalAdaptiveUncertainty:
    def __init__(self, history):
        required = ["timestamp"]

        for h in range(1, 7):
            required += [
                f"xgboost_h{h}_kw",
                f"actual_h{h}_kw",
            ]

        missing = [
            column for column in required
            if column not in history.columns
        ]

        if missing:
            raise ValueError(f"Missing columns: {missing}")

        data = history[required].copy()
        data["timestamp"] = pd.to_datetime(
            data["timestamp"],
            errors="raise"
        )

        if data["timestamp"].isna().any():
            raise ValueError("Missing timestamps")

        data = data.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        if data["timestamp"].duplicated().any():
            raise ValueError("Duplicate forecast origins")

        self.origins = data["timestamp"].to_numpy(
            dtype="datetime64[ns]"
        )

        self.targets = []
        self.errors = []

        for h in range(1, 7):
            forecasts = data[
                f"xgboost_h{h}_kw"
            ].to_numpy(dtype=float)

            actuals = data[
                f"actual_h{h}_kw"
            ].to_numpy(dtype=float)

            if not np.isfinite(forecasts).all():
                raise ValueError("Invalid forecast data")

            if not np.isfinite(actuals).all():
                raise ValueError("Invalid actual data")

            targets = (
                data["timestamp"]
                + pd.Timedelta(minutes=10 * h)
            ).to_numpy(dtype="datetime64[ns]")

            self.targets.append(targets)
            self.errors.append(
                np.abs(forecasts - actuals)
            )

    def margins(self, decision_time):
        decision = np.datetime64(
            pd.Timestamp(decision_time),
            "ns"
        )

        margins = []
        diagnostics = []

        for h in range(6):
            eligible = np.flatnonzero(
                self.targets[h] < decision
            )

            selected = eligible[-WINDOW:]

            if len(selected) < WINDOW:
                raise ValueError(
                    f"Insufficient causal history at horizon {h+1}"
                )

            if np.any(self.targets[h][selected] >= decision):
                raise RuntimeError(
                    "Future-information leakage detected"
                )

            rolling = conformal_quantile(
                self.errors[h][selected]
            )

            post_gap_count = int(np.count_nonzero(
                self.origins[selected]
                >= np.datetime64(GAP_START, "ns")
            ))

            fallback = (
                decision >= np.datetime64(GAP_START, "ns")
                and post_gap_count < POST_GAP_MINIMUM
            )

            floor = STATIC_FLOORS_KW[h]

            margin = (
                floor if fallback
                else max(rolling, floor)
            )

            margins.append(margin)

            diagnostics.append({
                "horizon_minutes": 10 * (h + 1),
                "rolling_margin_kw": rolling,
                "static_floor_kw": float(floor),
                "adaptive_margin_kw": float(margin),
                "post_gap_count": post_gap_count,
                "fallback_active": bool(fallback),
                "newest_target": pd.Timestamp(
                    self.targets[h][selected[-1]]
                ),
            })

        return (
            np.asarray(margins, dtype=float),
            diagnostics
        )
