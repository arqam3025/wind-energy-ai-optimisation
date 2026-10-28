
from pathlib import Path

import numpy as np
import pandas as pd

input_path = Path(
    "results/multistep_controller_development_split.csv"
)

output_dir = Path(
    "data/processed/controller_development_blocks"
)

if output_dir.exists():
    raise FileExistsError(
        f"Output directory already exists: {output_dir}"
    )

df = pd.read_csv(
    input_path,
    parse_dates=["timestamp"]
)

df = df.sort_values("timestamp").reset_index(drop=True)

if df.empty:
    raise ValueError("Development dataset is empty")

if df["timestamp"].duplicated().any():
    raise ValueError("Duplicate timestamps detected")

required = (
    ["timestamp", "current_power_kw"]
    + [
        f"{kind}_h{h}_kw"
        for kind in ["xgboost", "persistence", "actual"]
        for h in range(1, 7)
    ]
)

if df[required].isna().any().any():
    raise ValueError("Missing required values")

# Separate genuinely continuous segments.
segment_id = (
    df["timestamp"]
    .diff()
    .ne(pd.Timedelta(minutes=10))
    .cumsum()
)

blocks = []
block_id = 0
block_size = 144

for _, segment in df.groupby(segment_id):
    segment = segment.reset_index(drop=True)

    # Leave six rows of look-ahead buffer inside
    # each segment for the 60-minute horizon.
    usable_rows = max(0, len(segment) - 6)

    n_blocks = usable_rows // block_size

    for i in range(n_blocks):
        start = i * block_size
        block = segment.iloc[
            start:start + block_size
        ].copy()

        if len(block) != block_size:
            raise ValueError("Unexpected block size")

        expected_timestamps = pd.date_range(
            start=block["timestamp"].iloc[0],
            periods=block_size,
            freq="10min",
        )

        if not np.array_equal(
            block["timestamp"].to_numpy(),
            expected_timestamps.to_numpy(),
        ):
            raise ValueError("Block is not continuous")

        # All six future values must match subsequent
        # current-power observations when available.
        for h in range(1, 7):
            count = block_size - h

            actual = block[
                f"actual_h{h}_kw"
            ].to_numpy()[:count]

            # Apply the same non-negative generation convention
            # used when producing the forecast targets.
            future_power = np.maximum(
                block["current_power_kw"].to_numpy()[h:],
                0.0
            )

            if not np.allclose(
                actual, future_power,
                atol=1e-5,
                rtol=1e-7,
            ):
                raise ValueError(
                    f"Future target mismatch at horizon {h}"
                )

        block_id += 1

        blocks.append((
            block_id,
            block,
        ))

if not blocks:
    raise ValueError("No valid 24-hour blocks found")

output_dir.mkdir(parents=True, exist_ok=False)

print("=" * 65)
print("STEP 60: CONTROLLER DEVELOPMENT BLOCKS")
print("=" * 65)

for block_id, block in blocks:
    output_path = (
        output_dir /
        f"development_block_{block_id}.csv"
    )

    with output_path.open(
        "x", newline="", encoding="utf-8"
    ) as file:
        block.to_csv(file, index=False)

    print(
        f"Block {block_id:02d} | "
        f"{block['timestamp'].iloc[0]} to "
        f"{block['timestamp'].iloc[-1]}"
    )

print("\nTotal blocks:", len(blocks))
print("Total observations:", len(blocks) * block_size)
print("Saved directory:", output_dir)
print("Step 60 completed.")
