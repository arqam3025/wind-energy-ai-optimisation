
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

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

midpoint = len(validation) // 2

calibration = validation.iloc[:midpoint].copy()
evaluation = validation.iloc[midpoint:].copy()

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


def analyse_period(name, data):
    predictions = (
        data["power_kw"].to_numpy()
        + model.predict(data[features])
    )

    errors = np.abs(
        data["target_power_kw"].to_numpy()
        - predictions
    )

    print(f"\n{name}")
    print("Start:", data["timestamp"].min())
    print("End:", data["timestamp"].max())
    print("Observations:", len(data))
    print(f"Average wind speed: {data['wind_speed'].mean():.3f} m/s")
    print(f"Average power: {data['power_kw'].mean():.3f} kW")
    print(f"Mean absolute error: {errors.mean():.3f} kW")
    print(f"90th percentile error: {np.percentile(errors, 90):.3f} kW")
    print(f"95th percentile error: {np.percentile(errors, 95):.3f} kW")


print("=" * 60)
print("UNCERTAINTY DISTRIBUTION SHIFT ANALYSIS")
print("=" * 60)

analyse_period("Calibration period", calibration)
analyse_period("Evaluation period", evaluation)

print("\nFinal test period remains untouched.")
