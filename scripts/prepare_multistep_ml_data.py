
from pathlib import Path

import pandas as pd

DATA_PATH = "data/processed/wind_features_10min.csv"

df = pd.read_csv(
    DATA_PATH,
    parse_dates=["timestamp", "target_timestamp"],
)

df = df.sort_values("timestamp").reset_index(drop=True)

# A timestamp-indexed lookup of measured power.
power_lookup = df.set_index("timestamp")["power_kw"]

# Create six future power targets.
for h in range(1, 7):
    future_timestamps = (
        df["timestamp"]
        + pd.Timedelta(minutes=10 * h)
    )

    df[f"target_h{h}_kw"] = (
        future_timestamps.map(power_lookup)
    )

target_columns = [
    f"target_h{h}_kw"
    for h in range(1, 7)
]

# Retain only complete 60-minute forecast horizons.
complete = df.dropna(
    subset=target_columns
).copy()

validation_start = pd.Timestamp("2018-09-09 02:50:00")
test_start = pd.Timestamp("2018-11-05 15:10:00")

# Ensure training and validation targets
# do not cross their chronological boundaries.
last_target_time = (
    complete["timestamp"]
    + pd.Timedelta(minutes=60)
)

train = complete[
    last_target_time < validation_start
].copy()

validation = complete[
    (complete["timestamp"] >= validation_start)
    & (last_target_time < test_start)
].copy()

test = complete[
    complete["timestamp"] >= test_start
].copy()

Path("data/processed").mkdir(
    parents=True, exist_ok=True
)

output_path = (
    "data/processed/wind_multistep_features.csv"
)

complete.to_csv(output_path, index=False)

print("=" * 60)
print("MULTI-STEP MACHINE LEARNING DATASET")
print("=" * 60)

print("Original observations:", len(df))
print("Complete six-step windows:", len(complete))
print("Training observations:", len(train))
print("Validation observations:", len(validation))
print("Test observations:", len(test))

print("\nTarget columns:")
print(target_columns)

checks = {
    "Six targets available": (
        complete[target_columns].notna().all().all()
    ),
    "Train targets before validation": (
        (
            train["timestamp"]
            + pd.Timedelta(minutes=60)
        ).max() < validation_start
    ),
    "Validation targets before test": (
        (
            validation["timestamp"]
            + pd.Timedelta(minutes=60)
        ).max() < test_start
    ),
    "Test starts at correct boundary": (
        test["timestamp"].min() >= test_start
    ),
}

print("\nValidation checks:")

for name, passed in checks.items():
    print(
        f"{name}: "
        f"{'PASS' if passed else 'FAIL'}"
    )

print(
    "\nOverall validation:",
    "PASS" if all(checks.values()) else "FAIL"
)

print("\nSaved:", output_path)
print("Step 51 completed.")
