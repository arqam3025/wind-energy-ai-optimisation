
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

df = pd.read_csv(
    "data/processed/wind_multistep_features.csv",
    parse_dates=["timestamp"],
)

test_start = pd.Timestamp("2018-11-05 15:10:00")

test = df[
    df["timestamp"] >= test_start
].copy()

test = test.sort_values("timestamp").reset_index(drop=True)

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

results = pd.DataFrame({
    "timestamp": test["timestamp"],
    "current_power_kw": test["power_kw"],
})

print("=" * 60)
print("GENERATING SIX-STEP TEST FORECASTS")
print("=" * 60)

print("Test observations:", len(test))

for h in range(1, 7):
    model = XGBRegressor()
    model.load_model(
        f"models/wind_xgboost_h{h}.json"
    )

    predictions = model.predict(test[features])

    # Wind generation cannot be negative.
    predictions = np.maximum(predictions, 0.0)

    results[f"xgboost_h{h}_kw"] = predictions
    results[f"persistence_h{h}_kw"] = np.maximum(
        test["power_kw"].to_numpy(), 0.0
    )
    results[f"actual_h{h}_kw"] = np.maximum(
        test[f"target_h{h}_kw"].to_numpy(), 0.0
    )

    print(f"Horizon {h * 10} minutes: generated")

Path("results").mkdir(exist_ok=True)

output_path = "results/multistep_mpc_test_forecasts.csv"

results.to_csv(output_path, index=False)

print("\nChecks:")

forecast_columns = [
    f"{model}_h{h}_kw"
    for model in ["xgboost", "persistence"]
    for h in range(1, 7)
]

checks = {
    "No missing forecasts": (
        results[forecast_columns].notna().all().all()
    ),
    "No negative forecasts": (
        results[forecast_columns] >= 0
    ).all().all(),
    "Correct test period": (
        results["timestamp"].min() >= test_start
    ),
    "Correct forecast count": (
        len(results) == len(test)
    ),
}

for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

print(
    "\nOverall validation:",
    "PASS" if all(checks.values()) else "FAIL"
)

print("\nSaved:", output_path)
print("Step 53 completed.")
