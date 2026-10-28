
from pathlib import Path
import numpy as np
import pandas as pd

BLOCK_ID = 6

schedule = pd.read_csv(
    "results/evaluation_schedule.csv",
    parse_dates=["start_timestamp", "end_timestamp"]
)

forecasts = pd.read_csv(
    "results/multistep_mpc_test_forecasts.csv",
    parse_dates=["timestamp"]
)

matches = schedule[schedule["block_id"] == BLOCK_ID]

if len(matches) != 1:
    raise ValueError("Expected exactly one schedule entry for block 6.")

info = matches.iloc[0]

if info["evaluation_role"] != "development":
    raise ValueError("Block 6 is not marked as development.")

start = info["start_timestamp"]
end = info["end_timestamp"]

block = forecasts[
    forecasts["timestamp"].between(start, end)
].copy()

block = block.sort_values(
    "timestamp"
).reset_index(drop=True)

required = ["timestamp", "current_power_kw"]

for h in range(1, 7):
    required.extend([
        f"persistence_h{h}_kw",
        f"xgboost_h{h}_kw",
        f"actual_h{h}_kw",
    ])

missing = [col for col in required if col not in block.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

block["current_power_kw"] = (
    block["current_power_kw"].clip(lower=0)
)

valid = (
    len(block) == 144
    and not block[required].isna().any().any()
    and block["timestamp"].iloc[0] == start
    and block["timestamp"].iloc[-1] == end
    and (
        block["timestamp"].diff().iloc[1:]
        == pd.Timedelta(minutes=10)
    ).all()
    and np.allclose(
        block["persistence_h1_kw"],
        block["current_power_kw"],
        atol=0.001
    )
    and np.allclose(
        block["actual_h1_kw"].iloc[:-1],
        block["current_power_kw"].iloc[1:],
        atol=0.001
    )
)

if not valid:
    raise RuntimeError("Development block 6 failed validation.")

output = Path("data/processed/evaluation_block_6.csv")

if output.exists():
    raise FileExistsError(
        f"Refusing to overwrite existing file: {output}"
    )

block.to_csv(output, index=False)

print("=" * 60)
print("DEVELOPMENT BLOCK 6")
print("=" * 60)
print("Validation: PASS")
print("Rows:", len(block))
print("Start:", start)
print("End:", end)
print("Saved:", output)
