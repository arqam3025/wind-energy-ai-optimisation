
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
)
from xgboost import XGBRegressor

DATA_PATH = "data/processed/wind_features_10min.csv"

df = pd.read_csv(
    DATA_PATH,
    parse_dates=["timestamp", "target_timestamp"],
)

df = df.sort_values("timestamp").reset_index(drop=True)

validation_start = pd.Timestamp("2018-09-09 02:50:00")
test_start = pd.Timestamp("2018-11-05 15:10:00")

train = df[
    (df["timestamp"] < validation_start)
    & (df["target_timestamp"] < validation_start)
].copy()

validation = df[
    (df["timestamp"] >= validation_start)
    & (df["target_timestamp"] < test_start)
].copy()

test = df[
    df["timestamp"] >= test_start
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

print("=" * 60)
print("XGBOOST WIND FORECASTING")
print("=" * 60)

print("Training observations:", len(train))
print("Validation observations:", len(validation))
print("Test observations:", len(test))

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
    train["target_power_kw"],
)

Path("models").mkdir(exist_ok=True)
Path("results").mkdir(exist_ok=True)

model.save_model("models/wind_xgboost_10min.json")

print("\nModel saved: models/wind_xgboost_10min.json")

def evaluate(name, actual, predicted):
    mae = mean_absolute_error(actual, predicted)
    rmse = np.sqrt(mean_squared_error(actual, predicted))
    print(f"{name}: MAE={mae:.3f} kW, RMSE={rmse:.3f} kW")

print("\nValidation performance:")

evaluate(
    "Persistence",
    validation["target_power_kw"],
    validation["power_kw"],
)

evaluate(
    "XGBoost",
    validation["target_power_kw"],
    model.predict(validation[features]),
)

print("\nHeld-out test performance:")

test_predictions = model.predict(test[features])
persistence_predictions = test["power_kw"].to_numpy()

evaluate(
    "Persistence",
    test["target_power_kw"],
    persistence_predictions,
)

evaluate(
    "XGBoost",
    test["target_power_kw"],
    test_predictions,
)

results = pd.DataFrame({
    "timestamp": test["timestamp"].to_numpy(),
    "target_timestamp": test["target_timestamp"].to_numpy(),
    "actual_power_kw": test["target_power_kw"].to_numpy(),
    "persistence_prediction_kw": persistence_predictions,
    "xgboost_prediction_kw": test_predictions,
})

results.to_csv(
    "results/wind_xgboost_test_predictions.csv",
    index=False,
)

print(
    "\nSaved predictions: "
    "results/wind_xgboost_test_predictions.csv"
)

print("\nStep 48 completed.")
