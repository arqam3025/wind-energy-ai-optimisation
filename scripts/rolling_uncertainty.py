
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


def predict(data):
    return (
        data["power_kw"].to_numpy()
        + model.predict(data[features])
    )


cal_pred = predict(calibration)
eval_pred = predict(evaluation)

cal_errors = np.abs(
    calibration["target_power_kw"].to_numpy() - cal_pred
)

eval_actual = evaluation["target_power_kw"].to_numpy()
eval_errors = np.abs(eval_actual - eval_pred)

# Rolling calibration based on recent observed errors.
window = 1000
alpha = 0.10

error_history = list(cal_errors)

covered = []
widths = []

for error in eval_errors:

    recent = np.array(error_history[-window:])

    n = len(recent)
    level = min(
        1.0,
        np.ceil((n + 1) * (1 - alpha)) / n,
    )

    q = np.quantile(
        recent,
        level,
        method="higher",
    )

    covered.append(error <= q)
    widths.append(2 * q)

    # Update after the actual observation becomes available.
    error_history.append(error)


print("=" * 60)
print("ROLLING UNCERTAINTY CALIBRATION")
print("=" * 60)

print("Calibration observations:", len(calibration))
print("Evaluation observations:", len(evaluation))
print("Rolling error window:", window)

print("\nTarget coverage: 90%")
print(f"Observed coverage: {np.mean(covered) * 100:.2f}%")
print(f"Average interval width: {np.mean(widths):.3f} kW")

print("\nPrevious fixed-interval results:")
print("Coverage: 85.07%")
print("Average width: 689.640 kW")

print("\nFinal test period remains untouched.")
