
import pandas as pd

df = pd.read_csv(
    "data/processed/wind_features_10min.csv",
    parse_dates=["timestamp", "target_timestamp"],
)

df = df.sort_values("timestamp").reset_index(drop=True)

n = len(df)

train_end = int(n * 0.70)
val_end = int(n * 0.85)

# Establish chronological timestamp boundaries.
train_boundary = df.iloc[train_end]["timestamp"]
val_boundary = df.iloc[val_end]["timestamp"]

# Keep both feature and target timestamps
# inside their respective time partitions.
train = df[
    df["target_timestamp"] < train_boundary
].copy()

validation = df[
    (df["timestamp"] >= train_boundary)
    & (df["target_timestamp"] < val_boundary)
].copy()

test = df[
    df["timestamp"] >= val_boundary
].copy()

print("=" * 60)
print("FORECASTING DATA SPLIT VERIFICATION")
print("=" * 60)

for name, part in [
    ("TRAIN", train),
    ("VALIDATION", validation),
    ("TEST", test),
]:
    print(f"\n{name}")
    print("Observations:", len(part))
    print("Feature start:", part["timestamp"].min())
    print("Feature end:", part["timestamp"].max())
    print("Target end:", part["target_timestamp"].max())

print("\nLeakage checks:")

train_val_separate = (
    train["target_timestamp"].max()
    < validation["timestamp"].min()
)

val_test_separate = (
    validation["target_timestamp"].max()
    < test["timestamp"].min()
)

all_targets_future = (
    df["target_timestamp"] > df["timestamp"]
).all()

all_targets_10min = (
    (
        df["target_timestamp"] - df["timestamp"]
    ) == pd.Timedelta(minutes=10)
).all()

print(
    "Train/validation separation:",
    "PASS" if train_val_separate else "FAIL"
)

print(
    "Validation/test separation:",
    "PASS" if val_test_separate else "FAIL"
)

print(
    "Targets occur after features:",
    "PASS" if all_targets_future else "FAIL"
)

print(
    "All forecast horizons exactly 10 minutes:",
    "PASS" if all_targets_10min else "FAIL"
)

print(
    "\nOverall verification:",
    "PASS" if all([
        train_val_separate,
        val_test_separate,
        all_targets_future,
        all_targets_10min,
    ]) else "FAIL"
)
