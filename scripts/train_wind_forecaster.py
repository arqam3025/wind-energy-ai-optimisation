
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

DATA_PATH = Path("data/processed/wind_forecasting_10min.csv")

df = pd.read_csv(
    DATA_PATH,
    parse_dates=["timestamp", "target_timestamp"],
)

df = df.sort_values("timestamp").reset_index(drop=True)

features = [
    "power_kw",
    "wind_speed",
    "wind_direction",
]

target = "target_power_kw"

# Chronological 70% / 15% / 15% split.
n = len(df)
train_end = int(n * 0.70)
validation_end = int(n * 0.85)

train = df.iloc[:train_end]
validation = df.iloc[train_end:validation_end]
test = df.iloc[validation_end:]

print("=" * 60)
print("WIND POWER FORECASTING — FIRST EXPERIMENT")
print("=" * 60)

print("Training observations:", len(train))
print("Validation observations:", len(validation))
print("Test observations:", len(test))

print("\nDate ranges:")
for name, subset in [
    ("Train", train),
    ("Validation", validation),
    ("Test", test),
]:
    print(
        name,
        subset["timestamp"].min(),
        "to",
        subset["timestamp"].max(),
    )


def evaluate(name, actual, predicted):
    mae = mean_absolute_error(actual, predicted)
    rmse = np.sqrt(mean_squared_error(actual, predicted))

    print(f"\n{name}")
    print(f"MAE:  {mae:.3f} kW")
    print(f"RMSE: {rmse:.3f} kW")


# Baseline: next power equals current power.
evaluate(
    "Validation — Persistence baseline",
    validation[target],
    validation["power_kw"],
)

model = RandomForestRegressor(
    n_estimators=200,
    min_samples_leaf=3,
    random_state=42,
    n_jobs=-1,
)

model.fit(train[features], train[target])

validation_predictions = model.predict(validation[features])

evaluate(
    "Validation — Random Forest",
    validation[target],
    validation_predictions,
)

print("\nTest set has been reserved for final evaluation.")
print("No test metrics calculated yet.")
