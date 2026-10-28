
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

# Chronological boundaries
validation_start = pd.Timestamp("2018-09-09 02:50:00")
test_start = pd.Timestamp("2018-11-05 15:10:00")

input_path = Path("data/processed/wind_multistep_features.csv")
output_path = Path("results/multistep_mpc_validation_forecasts.csv")

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

print("=" * 60)
print("STEP 54: SIX-HORIZON VALIDATION FORECASTS")
print("=" * 60)

# Never overwrite previous results
if output_path.exists():
    raise FileExistsError(
        f"Output already exists: {output_path}"
    )

df = pd.read_csv(input_path, parse_dates=["timestamp"])

validation = df.loc[
    (df["timestamp"] >= validation_start)
    & (df["timestamp"] < test_start)
].copy()

validation = validation.sort_values(
    "timestamp"
).reset_index(drop=True)

required_columns = (
    ["timestamp", "power_kw"]
    + features
    + [f"target_h{h}_kw" for h in range(1, 7)]
)

missing = [
    column
    for column in required_columns
    if column not in validation.columns
]

if missing:
    raise ValueError(f"Missing columns: {missing}")

if validation.empty:
    raise ValueError("Validation period is empty.")

if validation[required_columns].isna().any().any():
    raise ValueError("Missing values in validation data.")

if validation["timestamp"].duplicated().any():
    raise ValueError("Duplicate validation timestamps.")

# Check timestamp spacing
# Detect and report gaps without treating them as continuous.
time_differences = validation["timestamp"].diff()

irregular_intervals = (
    time_differences.notna()
    & time_differences.ne(pd.Timedelta(minutes=10))
)

gap_count = int(irregular_intervals.sum())

print("Timestamp gaps detected:", gap_count)

if gap_count:
    print(
        "WARNING: Validation data contains timestamp gaps. "
        "MPC evaluation must use continuous blocks only."
    )

results = pd.DataFrame({
    "timestamp": validation["timestamp"],
    "current_power_kw": validation["power_kw"],
})

print("Validation observations:", len(validation))
print("First timestamp:", validation["timestamp"].min())
print("Last timestamp:", validation["timestamp"].max())

for h in range(1, 7):
    model_path = Path(f"models/wind_xgboost_h{h}.json")

    if not model_path.exists():
        raise FileNotFoundError(model_path)

    model = XGBRegressor()
    model.load_model(str(model_path))

    predictions = model.predict(validation[features])
    predictions = np.maximum(predictions, 0.0)

    results[f"xgboost_h{h}_kw"] = predictions

    results[f"persistence_h{h}_kw"] = np.maximum(
        validation["power_kw"].to_numpy(),
        0.0
    )

    results[f"actual_h{h}_kw"] = np.maximum(
        validation[f"target_h{h}_kw"].to_numpy(),
        0.0
    )

    print(f"Horizon {h * 10} minutes: generated")

forecast_columns = [
    f"{model}_h{h}_kw"
    for model in ["xgboost", "persistence"]
    for h in range(1, 7)
]

actual_columns = [
    f"actual_h{h}_kw" for h in range(1, 7)
]

checks = {
    "No missing values": results[
        forecast_columns + actual_columns
    ].notna().all().all(),

    "No negative forecasts": (
        results[forecast_columns] >= 0
    ).all().all(),

    "No negative actual values": (
        results[actual_columns] >= 0
    ).all().all(),

    "Correct validation period": (
        results["timestamp"].min() >= validation_start
        and results["timestamp"].max() < test_start
    ),

    "Correct row count": len(results) == len(validation),
}

print("\nValidation checks:")

for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

if not all(checks.values()):
    raise RuntimeError("Validation checks failed.")

output_path.parent.mkdir(parents=True, exist_ok=True)

# Exclusive creation prevents overwriting existing results
with output_path.open("x", encoding="utf-8", newline="") as file:
    results.to_csv(file, index=False)

print("\nOverall validation: PASS")
print("Saved:", output_path)
print("Step 54 completed.")
