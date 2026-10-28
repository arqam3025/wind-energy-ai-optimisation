
from pathlib import Path
import numpy as np
import pandas as pd

input_path = Path(
    "results/multistep_mpc_validation_audited.csv"
)

calibration_path = Path(
    "results/multistep_calibration_split.csv"
)

development_path = Path(
    "results/multistep_controller_development_split.csv"
)

# Refuse to overwrite existing results
for path in [calibration_path, development_path]:
    if path.exists():
        raise FileExistsError(
            f"Output already exists: {path}"
        )

df = pd.read_csv(
    input_path,
    parse_dates=["timestamp"]
)

df = df.sort_values("timestamp").reset_index(drop=True)

if df.empty:
    raise ValueError("Input dataset is empty")

if df["timestamp"].duplicated().any():
    raise ValueError("Duplicate timestamps detected")

required = [
    f"{kind}_h{h}_kw"
    for kind in ["xgboost", "persistence", "actual"]
    for h in range(1, 7)
]

if df[required].isna().any().any():
    raise ValueError("Missing forecast or actual values")

# 60% calibration, 40% controller development
split_index = int(len(df) * 0.60)

calibration = df.iloc[:split_index].copy()
development = df.iloc[split_index:].copy()

if calibration.empty or development.empty:
    raise ValueError("One split is empty")

if not (
    calibration["timestamp"].max()
    < development["timestamp"].min()
):
    raise ValueError("Chronological overlap detected")

print("=" * 65)
print("STEP 57: CHRONOLOGICAL VALIDATION SPLIT")
print("=" * 65)

for name, part in [
    ("Calibration", calibration),
    ("Controller development", development),
]:
    gaps = part["timestamp"].diff()
    irregular = (
        gaps.notna()
        & gaps.ne(pd.Timedelta(minutes=10))
    )

    print(f"\n{name}")
    print("Rows:", len(part))
    print("Start:", part["timestamp"].min())
    print("End:", part["timestamp"].max())
    print("Timestamp discontinuities:", int(irregular.sum()))

# Atomic-style exclusive file creation
with calibration_path.open("x", newline="", encoding="utf-8") as f:
    calibration.to_csv(f, index=False)

with development_path.open("x", newline="", encoding="utf-8") as f:
    development.to_csv(f, index=False)

print("\nSaved:", calibration_path)
print("Saved:", development_path)
print("Step 57 completed.")
