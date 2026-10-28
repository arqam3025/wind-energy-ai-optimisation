
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

df = pd.read_csv(
    "data/processed/wind_features_10min.csv",
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

# Predict change in power rather than absolute power.
train["power_delta"] = (
    train["target_power_kw"] - train["power_kw"]
)

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

model.fit(train[features], train["power_delta"])

predicted_delta = model.predict(validation[features])

# Convert predicted changes back to absolute power.
predicted_power = validation["power_kw"].to_numpy() + predicted_delta

actual = validation["target_power_kw"].to_numpy()
persistence = validation["power_kw"].to_numpy()


def evaluate(name, predictions):
    mae = mean_absolute_error(actual, predictions)
    rmse = np.sqrt(mean_squared_error(actual, predictions))

    print(f"\n{name}")
    print(f"MAE:  {mae:.3f} kW")
    print(f"RMSE: {rmse:.3f} kW")


print("=" * 60)
print("WIND POWER CHANGE FORECASTING")
print("=" * 60)

print("Training observations:", len(train))
print("Validation observations:", len(validation))

evaluate("Persistence baseline", persistence)
evaluate("XGBoost predicting power change", predicted_power)

print("\nTest period remains untouched.")
