
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

DATA_PATH = "data/processed/wind_features_10min.csv"

df = pd.read_csv(
    DATA_PATH,
    parse_dates=["timestamp", "target_timestamp"],
)

df = df.sort_values("timestamp").reset_index(drop=True)

# Use the original chronological experiment boundaries.
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

X_train = train[features]
y_train = train["target_power_kw"]

X_val = validation[features]
y_val = validation["target_power_kw"]


def evaluate(name, predictions):
    mae = mean_absolute_error(y_val, predictions)
    rmse = np.sqrt(mean_squared_error(y_val, predictions))

    print(f"\n{name}")
    print(f"MAE:  {mae:.3f} kW")
    print(f"RMSE: {rmse:.3f} kW")


print("=" * 60)
print("HISTORICAL WIND FORECASTING COMPARISON")
print("=" * 60)

print("Training observations:", len(train))
print("Validation observations:", len(validation))
print("Historical features:", len(features))

evaluate(
    "Persistence baseline",
    validation["power_kw"],
)

rf = RandomForestRegressor(
    n_estimators=200,
    min_samples_leaf=3,
    random_state=42,
    n_jobs=-1,
)

rf.fit(X_train, y_train)

evaluate(
    "Random Forest with historical features",
    rf.predict(X_val),
)

xgb = XGBRegressor(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.9,
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1,
)

xgb.fit(X_train, y_train)

evaluate(
    "XGBoost with historical features",
    xgb.predict(X_val),
)

print("\nTest period remains untouched.")
