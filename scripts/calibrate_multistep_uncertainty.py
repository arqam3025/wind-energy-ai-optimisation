
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

DATA_PATH = Path("data/processed/wind_multistep_features.csv")
OUTPUT_PATH = Path("results/multistep_uncertainty_calibration.csv")

VALIDATION_START = pd.Timestamp("2018-09-09 02:50:00")
TEST_START = pd.Timestamp("2018-11-05 15:10:00")

ALPHA = 0.10  # Target marginal coverage: 90%

features = [
    "power_kw",
    "wind_speed",
    "wind_direction",
    "power_lag_10min",
    "power_lag_20min",
    "power_lag_30min",
    "power_lag_60min",
    "wind_lag_10min",
    "wind_lag_20min",
    "wind_lag_30min",
    "wind_lag_60min",
    "power_change_10min",
    "wind_change_10min",
    "power_mean_40min",
]

df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)

last_target = df["timestamp"] + pd.Timedelta(minutes=60)

validation = df[
    (df["timestamp"] >= VALIDATION_START)
    & (last_target < TEST_START)
].copy()

if validation.empty:
    raise ValueError("No validation observations found.")

if validation[features].isna().any().any():
    raise ValueError("Missing validation features detected.")

print("=" * 65)
print("SIX-HORIZON XGBOOST UNCERTAINTY CALIBRATION")
print("=" * 65)
print("Validation observations:", len(validation))

records = []

for h in range(1, 7):
    target = f"target_h{h}_kw"

    if validation[target].isna().any():
        raise ValueError(f"Missing values in {target}")

    model = XGBRegressor()
    model.load_model(f"models/wind_xgboost_h{h}.json")

    predicted = np.maximum(
        model.predict(validation[features]), 0.0
    )

    actual = np.maximum(
        validation[target].to_numpy(dtype=float), 0.0
    )

    absolute_errors = np.abs(actual - predicted)
    n = len(absolute_errors)

    # Finite-sample split-conformal quantile.
    rank = int(np.ceil((n + 1) * (1 - ALPHA)))

    sorted_errors = np.sort(absolute_errors)

    q = (
        float(sorted_errors[rank - 1])
        if rank <= n
        else float("inf")
    )

    lower = np.maximum(predicted - q, 0.0)
    upper = predicted + q

    coverage = np.mean(
        (actual >= lower) & (actual <= upper)
    )

    records.append({
        "horizon_minutes": h * 10,
        "calibration_samples": n,
        "target_coverage": 1 - ALPHA,
        "calibration_quantile_kw": q,
        "calibration_coverage": coverage,
        "mean_interval_width_kw": np.mean(upper - lower),
        "validation_mae_kw": np.mean(absolute_errors),
    })

    print(
        f"Horizon {h * 10:2d} min | "
        f"Quantile: {q:9.3f} kW | "
        f"Coverage: {coverage * 100:6.2f}%"
    )

summary = pd.DataFrame(records)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
summary.to_csv(OUTPUT_PATH, index=False)

print("\nCalibration summary:")
print(summary.round(3).to_string(index=False))

print("\nSaved:", OUTPUT_PATH)
