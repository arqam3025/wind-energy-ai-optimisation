
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

# Chronologically divide validation into calibration
# and evaluation periods.
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


def predict_power(data):
    return (
        data["power_kw"].to_numpy()
        + model.predict(data[features])
    )


calibration_predictions = predict_power(calibration)

calibration_errors = np.abs(
    calibration["target_power_kw"].to_numpy()
    - calibration_predictions
)

# Finite-sample split-conformal quantile.
alpha = 0.10
n = len(calibration_errors)

quantile_level = min(
    1.0,
    np.ceil((n + 1) * (1 - alpha)) / n,
)

q = np.quantile(
    calibration_errors,
    quantile_level,
    method="higher",
)

evaluation_predictions = predict_power(evaluation)

lower = evaluation_predictions - q
upper = evaluation_predictions + q

actual = evaluation["target_power_kw"].to_numpy()

coverage = np.mean(
    (actual >= lower) & (actual <= upper)
)

average_width = np.mean(upper - lower)

print("=" * 60)
print("UNCERTAINTY-AWARE WIND POWER FORECASTING")
print("=" * 60)

print("Training observations:", len(train))
print("Calibration observations:", len(calibration))
print("Evaluation observations:", len(evaluation))

print("\nNominal interval coverage: 90%")
print(f"Calibration error quantile: {q:.3f} kW")
print(f"Observed interval coverage: {coverage * 100:.2f}%")
print(f"Average interval width: {average_width:.3f} kW")

print("\nFinal test period remains untouched.")
