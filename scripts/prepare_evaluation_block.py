
from pathlib import Path
import numpy as np
import pandas as pd

schedule = pd.read_csv(
    "results/evaluation_schedule.csv",
    parse_dates=["start_timestamp", "end_timestamp"]
)

forecasts = pd.read_csv(
    "results/multistep_mpc_test_forecasts.csv",
    parse_dates=["timestamp"]
)

block_id = 1

selected = schedule.loc[
    schedule["block_id"] == block_id
]

if len(selected) != 1:
    raise ValueError("Block ID not found or duplicated.")

block_info = selected.iloc[0]

if block_info["evaluation_role"] != "evaluation":
    raise ValueError("Cannot evaluate a development block.")

start = block_info["start_timestamp"]
end = block_info["end_timestamp"]

block = forecasts.loc[
    forecasts["timestamp"].between(start, end)
].copy()

block = block.sort_values("timestamp").reset_index(drop=True)

required_columns = [
    "timestamp",
    "current_power_kw",
]

for h in range(1, 7):
    required_columns.extend([
        f"persistence_h{h}_kw",
        f"xgboost_h{h}_kw",
        f"actual_h{h}_kw",
    ])

missing = [
    column for column in required_columns
    if column not in block.columns
]

if missing:
    raise ValueError(f"Missing columns: {missing}")

checks = {
    "144 forecast origins": len(block) == 144,
    "No missing values": not block[required_columns].isna().any().any(),
    "Continuous timestamps": (
        block["timestamp"].diff().iloc[1:]
        == pd.Timedelta(minutes=10)
    ).all(),
    "Correct start": (
        len(block) > 0 and block["timestamp"].iloc[0] == start
    ),
    "Correct end": (
        len(block) > 0 and block["timestamp"].iloc[-1] == end
    ),
    "Persistence equals current power": np.allclose(
        block["persistence_h1_kw"],
        block["current_power_kw"],
        atol=0.001
    ),
    "Next actual matches next current": np.allclose(
        block["actual_h1_kw"].iloc[:-1],
        block["current_power_kw"].iloc[1:],
        atol=0.001
    ),
}

print("=" * 65)
print("EVALUATION BLOCK PREPARATION")
print("=" * 65)

print("Block ID:", block_id)
print("Start:", start)
print("End:", end)
print("Rows:", len(block))

print("\nData checks:")
for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

if not all(checks.values()):
    raise RuntimeError("Evaluation block validation failed.")

output = "data/processed/evaluation_block_1.csv"
Path("data/processed").mkdir(parents=True, exist_ok=True)

block.to_csv(output, index=False)

print("\nSaved:", output)
print("Evaluation block ready.")
