
from pathlib import Path

import numpy as np
import pandas as pd

CALIBRATION_PATH = Path(
    "results/multistep_uncertainty_calibration.csv"
)
FORECAST_PATH = Path(
    "results/multistep_mpc_test_forecasts.csv"
)
SUMMARY_PATH = Path(
    "results/multistep_uncertainty_test_evaluation.csv"
)
INTERVALS_PATH = Path(
    "results/multistep_uncertainty_test_intervals.csv"
)

calibration = pd.read_csv(CALIBRATION_PATH)
test = pd.read_csv(FORECAST_PATH, parse_dates=["timestamp"])

test = test.sort_values("timestamp").reset_index(drop=True)

if test.empty:
    raise ValueError("Test forecast file is empty.")

if test["timestamp"].duplicated().any():
    raise ValueError("Duplicate test timestamps detected.")

if test["timestamp"].min() < pd.Timestamp("2018-11-05 15:10:00"):
    raise ValueError("Unexpected observations before test period.")

summary_records = []
intervals = test[["timestamp"]].copy()

for h in range(1, 7):
    horizon = h * 10

    row = calibration.loc[
        calibration["horizon_minutes"] == horizon
    ]

    if len(row) != 1:
        raise ValueError(
            f"Expected one calibration row for {horizon} min."
        )

    q = float(row.iloc[0]["calibration_quantile_kw"])

    predicted = test[
        f"xgboost_h{h}_kw"
    ].to_numpy(dtype=float)

    actual = test[
        f"actual_h{h}_kw"
    ].to_numpy(dtype=float)

    if not (
        np.isfinite(predicted).all()
        and np.isfinite(actual).all()
        and np.isfinite(q)
    ):
        raise ValueError(
            f"Non-finite values detected at horizon {horizon}."
        )

    lower = np.maximum(predicted - q, 0.0)
    upper = predicted + q

    covered = (actual >= lower) & (actual <= upper)

    coverage = float(np.mean(covered))
    mean_width = float(np.mean(upper - lower))
    mae = float(np.mean(np.abs(actual - predicted)))

    below = float(np.mean(actual < lower))
    above = float(np.mean(actual > upper))

    intervals[f"predicted_h{h}_kw"] = predicted
    intervals[f"actual_h{h}_kw"] = actual
    intervals[f"lower_h{h}_kw"] = lower
    intervals[f"upper_h{h}_kw"] = upper
    intervals[f"covered_h{h}"] = covered

    summary_records.append({
        "horizon_minutes": horizon,
        "test_samples": len(test),
        "target_coverage": 0.90,
        "test_coverage": coverage,
        "mean_interval_width_kw": mean_width,
        "test_mae_kw": mae,
        "below_interval_fraction": below,
        "above_interval_fraction": above,
    })

summary = pd.DataFrame(summary_records)

SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

summary.to_csv(SUMMARY_PATH, index=False)
intervals.to_csv(INTERVALS_PATH, index=False)

print("=" * 70)
print("HELD-OUT TEST UNCERTAINTY EVALUATION")
print("=" * 70)

print("Test observations:", len(test))
print("Test start:", test["timestamp"].min())
print("Test end:", test["timestamp"].max())

print("\nResults:")
print(
    summary.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)

print("\nSaved:", SUMMARY_PATH)
print("Saved:", INTERVALS_PATH)
