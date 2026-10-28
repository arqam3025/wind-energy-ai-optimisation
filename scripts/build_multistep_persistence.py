
from pathlib import Path

import numpy as np
import pandas as pd

df = pd.read_csv(
    "data/processed/wind_features_10min.csv",
    parse_dates=["timestamp", "target_timestamp"],
)

df = df.sort_values("timestamp").reset_index(drop=True)

test_start = pd.Timestamp("2018-11-05 15:10:00")

# Use only the previously established held-out test period.
test = df[df["timestamp"] >= test_start].copy()

# Build a timestamp lookup for measured power.
power_lookup = df.set_index("timestamp")["power_kw"]

records = []

for _, row in test.iterrows():
    current_time = row["timestamp"]
    current_power = max(0.0, float(row["power_kw"]))

    future_times = [
        current_time + pd.Timedelta(minutes=10 * h)
        for h in range(1, 7)
    ]

    # Only evaluate complete, uninterrupted horizons.
    if not all(t in power_lookup.index for t in future_times):
        continue

    actual = np.array([
        max(0.0, float(power_lookup.loc[t]))
        for t in future_times
    ])

    predicted = np.full(6, current_power)

    record = {"timestamp": current_time}

    for h in range(6):
        record[f"actual_h{h+1}_kw"] = actual[h]
        record[f"predicted_h{h+1}_kw"] = predicted[h]

    records.append(record)

results = pd.DataFrame(records)

Path("results").mkdir(exist_ok=True)

output_path = "results/multistep_persistence_test.csv"
results.to_csv(output_path, index=False)

print("=" * 60)
print("MULTI-STEP PERSISTENCE FORECAST")
print("=" * 60)

print("Valid six-step forecast windows:", len(results))

if results.empty:
    raise RuntimeError("No complete forecast windows found.")

print("\nForecast accuracy by horizon:")

for h in range(1, 7):
    actual = results[f"actual_h{h}_kw"].to_numpy()
    predicted = results[f"predicted_h{h}_kw"].to_numpy()

    mae = np.mean(np.abs(actual - predicted))
    rmse = np.sqrt(np.mean((actual - predicted) ** 2))

    print(
        f"{h * 10:2d} minutes: "
        f"MAE={mae:.3f} kW, "
        f"RMSE={rmse:.3f} kW"
    )

print("\nSaved:", output_path)
print("Step 50 completed.")
