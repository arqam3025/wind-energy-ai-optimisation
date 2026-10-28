
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error

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

validation["prediction"] = (
    validation["power_kw"]
    + model.predict(validation[features])
)

validation["persistence_error"] = (
    validation["target_power_kw"]
    - validation["power_kw"]
).abs()

validation["xgboost_error"] = (
    validation["target_power_kw"]
    - validation["prediction"]
).abs()

# Wind-speed groups in metres per second.
bins = [0, 4, 8, 12, 16, np.inf]
labels = ["0-4", "4-8", "8-12", "12-16", "16+"]

validation["wind_group"] = pd.cut(
    validation["wind_speed"],
    bins=bins,
    labels=labels,
    include_lowest=True,
)

results = validation.groupby(
    "wind_group",
    observed=True,
).agg(
    observations=("target_power_kw", "size"),
    persistence_mae=("persistence_error", "mean"),
    xgboost_mae=("xgboost_error", "mean"),
)

results["improvement_pct"] = (
    (results["persistence_mae"] - results["xgboost_mae"])
    / results["persistence_mae"]
    * 100
)

print("=" * 60)
print("FORECAST ERRORS BY WIND SPEED")
print("=" * 60)

print(results.round(3).to_string())

print("\nPositive improvement means XGBoost is better.")
print("Negative improvement means persistence is better.")
print("\nFinal test period remains untouched.")
