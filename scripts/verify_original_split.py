
import pandas as pd

df = pd.read_csv(
    "data/processed/wind_features_10min.csv",
    parse_dates=["timestamp", "target_timestamp"],
)

df = df.sort_values("timestamp").reset_index(drop=True)

validation_start = pd.Timestamp("2018-09-09 02:50:00")
test_start = pd.Timestamp("2018-11-05 15:10:00")

train = df[
    (df["timestamp"] < validation_start)
    & (df["target_timestamp"] < validation_start)
].copy()

validation = df[
    (df["timestamp"] >= validation_start)
    & (df["target_timestamp"] < test_start)
].copy()

test = df[
    df["timestamp"] >= test_start
].copy()

print("=" * 60)
print("ORIGINAL FORECASTING SPLIT")
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

checks = {
    "Train/validation separation": (
        train["target_timestamp"].max()
        < validation["timestamp"].min()
    ),
    "Validation/test separation": (
        validation["target_timestamp"].max()
        < test["timestamp"].min()
    ),
    "Exact 10-minute prediction horizon": (
        (
            df["target_timestamp"] - df["timestamp"]
        ) == pd.Timedelta(minutes=10)
    ).all(),
    "No duplicate timestamps": (
        df["timestamp"].is_unique
    ),
}

print("\nChecks:")
for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

print(
    "\nOverall:",
    "PASS" if all(checks.values()) else "FAIL"
)
