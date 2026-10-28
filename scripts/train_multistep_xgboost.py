
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

DATA_PATH = "data/processed/wind_multistep_features.csv"

df = pd.read_csv(
    DATA_PATH,
    parse_dates=["timestamp", "target_timestamp"],
)

df = df.sort_values("timestamp").reset_index(drop=True)

validation_start = pd.Timestamp("2018-09-09 02:50:00")
test_start = pd.Timestamp("2018-11-05 15:10:00")

last_target = df["timestamp"] + pd.Timedelta(minutes=60)

train = df[last_target < validation_start].copy()

validation = df[
    (df["timestamp"] >= validation_start)
    & (last_target < test_start)
].copy()

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

Path("models").mkdir(exist_ok=True)
Path("results").mkdir(exist_ok=True)

print("=" * 65)
print("SIX-HORIZON XGBOOST FORECASTING")
print("=" * 65)

print("Training observations:", len(train))
print("Validation observations:", len(validation))
print("Features:", len(features))

results = []

for h in range(1, 7):
    target = f"target_h{h}_kw"

    model = XGBRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        train[features],
        train[target],
    )

    predictions = model.predict(validation[features])

    # Compare against multi-step persistence.
    persistence = validation["power_kw"].to_numpy()
    actual = validation[target].to_numpy()

    xgb_mae = np.mean(np.abs(predictions - actual))
    xgb_rmse = np.sqrt(np.mean((predictions - actual) ** 2))

    persistence_mae = np.mean(np.abs(persistence - actual))
    persistence_rmse = np.sqrt(
        np.mean((persistence - actual) ** 2)
    )

    model_path = f"models/wind_xgboost_h{h}.json"
    model.save_model(model_path)

    results.append({
        "horizon_minutes": h * 10,
        "persistence_mae_kw": persistence_mae,
        "xgboost_mae_kw": xgb_mae,
        "persistence_rmse_kw": persistence_rmse,
        "xgboost_rmse_kw": xgb_rmse,
    })

    print(f"\nForecast horizon: {h * 10} minutes")
    print(f"Persistence MAE:  {persistence_mae:.3f} kW")
    print(f"XGBoost MAE:      {xgb_mae:.3f} kW")
    print(f"Persistence RMSE: {persistence_rmse:.3f} kW")
    print(f"XGBoost RMSE:     {xgb_rmse:.3f} kW")
    print("Saved:", model_path)

summary = pd.DataFrame(results)

summary.to_csv(
    "results/multistep_xgboost_validation.csv",
    index=False,
)

print("\n" + "=" * 65)
print("VALIDATION SUMMARY")
print("=" * 65)

print(summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

print("\nHeld-out test period not evaluated.")
print("Step 52 completed.")
