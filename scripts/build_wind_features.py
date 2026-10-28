
from pathlib import Path
import pandas as pd

SOURCE = Path("data/processed/wind_forecasting_10min.csv")
OUTPUT = Path("data/processed/wind_features_10min.csv")

df = pd.read_csv(
    SOURCE,
    parse_dates=["timestamp", "target_timestamp"],
)

df = df.sort_values("timestamp").reset_index(drop=True)

# Build historical features using timestamp-based joins.
# Missing time intervals remain missing rather than being
# mistaken for consecutive 10-minute observations.

history = df[
    ["timestamp", "power_kw", "wind_speed"]
].copy()

for minutes in [10, 20, 30, 60]:

    previous = history.copy()

    previous["timestamp"] = (
        previous["timestamp"]
        + pd.Timedelta(minutes=minutes)
    )

    previous = previous.rename(
        columns={
            "power_kw": f"power_lag_{minutes}min",
            "wind_speed": f"wind_lag_{minutes}min",
        }
    )

    df = df.merge(
        previous,
        on="timestamp",
        how="left",
        validate="one_to_one",
    )

# Changes observed up to the prediction time.
df["power_change_10min"] = (
    df["power_kw"] - df["power_lag_10min"]
)

df["wind_change_10min"] = (
    df["wind_speed"] - df["wind_lag_10min"]
)

# Recent power summary, using only known observations.
power_columns = [
    "power_kw",
    "power_lag_10min",
    "power_lag_20min",
    "power_lag_30min",
]

df["power_mean_40min"] = df[power_columns].mean(
    axis=1,
    skipna=False,
)

# Require a complete history for the first experiment.
feature_columns = [
    "power_lag_10min",
    "power_lag_20min",
    "power_lag_30min",
    "power_lag_60min",
    "wind_lag_10min",
    "wind_lag_20min",
    "wind_lag_30min",
    "wind_lag_60min",
    "power_change_10min",
    "wind_change_10min",
    "power_mean_40min",
]

clean = df.dropna(subset=feature_columns).copy()

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
clean.to_csv(OUTPUT, index=False)

print("=" * 60)
print("HISTORICAL WIND FEATURE ENGINEERING")
print("=" * 60)

print("Original forecasting pairs:", len(df))
print("Pairs with complete history:", len(clean))
print("Excluded due to missing history:", len(df) - len(clean))

print("\nNew features:")
for feature in feature_columns:
    print("-", feature)

print("\nFirst five rows:")
print(
    clean[
        ["timestamp", "power_kw",
         "power_lag_10min", "power_change_10min",
         "target_power_kw"]
    ].head().to_string(index=False)
)

print("\nSaved:", OUTPUT)
