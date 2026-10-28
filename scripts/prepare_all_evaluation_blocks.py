
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

forecasts = forecasts.sort_values("timestamp")

output_dir = Path("data/processed")
output_dir.mkdir(parents=True, exist_ok=True)

required = ["timestamp", "current_power_kw"]

for h in range(1, 7):
    required.extend([
        f"persistence_h{h}_kw",
        f"xgboost_h{h}_kw",
        f"actual_h{h}_kw",
    ])

missing = [c for c in required if c not in forecasts.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

evaluation = schedule[
    schedule["evaluation_role"] == "evaluation"
].copy()

passed = 0
failed = 0

print("=" * 65)
print("PREPARING ALL EVALUATION BLOCKS")
print("=" * 65)

for _, info in evaluation.iterrows():

    block_id = int(info["block_id"])
    start = info["start_timestamp"]
    end = info["end_timestamp"]

    block = forecasts[
        forecasts["timestamp"].between(start, end)
    ].copy()

    block = block.sort_values(
        "timestamp"
    ).reset_index(drop=True)
    # Physical modelling convention:
# Negative measured wind generation is treated as zero
# available wind power for battery dispatch.
# Preserve the original source dataset unchanged.
    block["current_power_kw"] = block["current_power_kw"].clip(lower=0)
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
        print(f"Block {block_id}: FAIL")
        failed += 1
        continue

    output = (
        output_dir /
        f"evaluation_block_{block_id}.csv"
    )

    block.to_csv(output, index=False)

    print(f"Block {block_id}: PASS")
    passed += 1

print("\n" + "=" * 65)
print("SUMMARY")
print("=" * 65)

print("Evaluation blocks:", len(evaluation))
print("Passed:", passed)
print("Failed:", failed)

if failed:
    raise RuntimeError(
        f"{failed} evaluation blocks failed validation."
    )

print("\nAll evaluation blocks prepared successfully.")
