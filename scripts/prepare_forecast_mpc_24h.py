
from pathlib import Path

import numpy as np
import pandas as pd

df = pd.read_csv(
    "results/multistep_mpc_test_forecasts.csv",
    parse_dates=["timestamp"],
)

df = df.sort_values("timestamp").reset_index(drop=True)

start = pd.Timestamp("2018-11-14 13:00:00")

end = start + pd.Timedelta(minutes=1430)

selected = df[
    (df["timestamp"] >= start)
    & (df["timestamp"] <= end)
].copy().reset_index(drop=True)

print("=" * 65)
print("FORECAST-DRIVEN MPC: 24-HOUR DATA PREPARATION")
print("=" * 65)

print("Observations:", len(selected))
print("Start:", selected["timestamp"].min())
print("End:", selected["timestamp"].max())

expected_times = pd.date_range(
    start=start,
    periods=144,
    freq="10min",
)

time_check = (
    len(selected) == 144
    and selected["timestamp"].reset_index(drop=True)
        .equals(pd.Series(expected_times, name="timestamp"))
)

forecast_columns = [
    f"{model}_h{h}_kw"
    for model in ["persistence", "xgboost"]
    for h in range(1, 7)
]

actual_columns = [
    f"actual_h{h}_kw"
    for h in range(1, 7)
]

missing_check = selected[
    forecast_columns + actual_columns
].notna().all().all()

nonnegative_check = (
    selected[forecast_columns + actual_columns] >= 0
).all().all()

# Every actual h1 value should match the next
# measured power, whenever the next row exists.
alignment_check = np.allclose(
    selected["actual_h1_kw"].iloc[:-1].to_numpy(),
    np.maximum(
        selected["current_power_kw"].iloc[1:].to_numpy(),
        0.0,
    ),
    atol=0.001,
)

# Persistence must use only the current power.
persistence_check = all(
    np.allclose(
        selected[f"persistence_h{h}_kw"],
        np.maximum(selected["current_power_kw"], 0.0),
        atol=0.001,
    )
    for h in range(1, 7)
)

checks = {
    "Exactly 144 continuous timestamps": time_check,
    "No missing forecast or actual values": missing_check,
    "Nonnegative forecasts and actuals": nonnegative_check,
    "Future actuals aligned with timestamps": alignment_check,
    "Persistence uses current power only": persistence_check,
}

print("\nValidation checks:")

for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

if not all(checks.values()):
    raise RuntimeError("MPC data validation failed.")

Path("data/processed").mkdir(
    parents=True, exist_ok=True
)

output_path = "data/processed/forecast_mpc_24h.csv"

selected.to_csv(output_path, index=False)

print("\nFirst forecast origin:", selected.iloc[0]["timestamp"])
print(
    "First realised future generation:",
    selected.iloc[0]["actual_h1_kw"],
    "kW",
)

print("\nSaved:", output_path)
print("Step 55 completed.")
