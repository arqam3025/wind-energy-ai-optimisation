
from pathlib import Path
import pandas as pd

SOURCE = Path("data/raw/T1.csv")
OUTPUT = Path("data/processed/wind_forecasting_10min.csv")

df = pd.read_csv(SOURCE)

df["timestamp"] = pd.to_datetime(
    df["Date/Time"],
    format="%d %m %Y %H:%M",
)

df = df.sort_values("timestamp").reset_index(drop=True)

# Use only information available at prediction time.
df["power_kw"] = df["LV ActivePower (kW)"]
df["wind_speed"] = df["Wind Speed (m/s)"]
df["wind_direction"] = df["Wind Direction (°)"]

# The next observed measurement is our candidate target.
df["target_power_kw"] = df["power_kw"].shift(-1)
df["target_timestamp"] = df["timestamp"].shift(-1)

# Retain only pairs exactly 10 minutes apart.
valid_interval = (
    df["target_timestamp"] - df["timestamp"]
    == pd.Timedelta(minutes=10)
)

forecast_df = df.loc[
    valid_interval,
    [
        "timestamp",
        "power_kw",
        "wind_speed",
        "wind_direction",
        "target_timestamp",
        "target_power_kw",
    ],
].copy()

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
forecast_df.to_csv(OUTPUT, index=False)

print("=" * 60)
print("10-MINUTE WIND POWER FORECASTING DATASET")
print("=" * 60)

print("Original observations:", len(df))
print("Valid forecasting pairs:", len(forecast_df))
print("Excluded pairs:", len(df) - len(forecast_df))

print("\nFirst five forecasting records:")
print(forecast_df.head().to_string(index=False))

print("\nMissing values:")
print(forecast_df.isna().sum().to_string())

print("\nSaved to:", OUTPUT)
