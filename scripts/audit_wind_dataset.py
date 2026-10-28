
from pathlib import Path
import pandas as pd

DATA_PATH = Path("data/raw/T1.csv")

df = pd.read_csv(DATA_PATH)

# Parse the dataset's day-month-year timestamps.
df["Date/Time"] = pd.to_datetime(
    df["Date/Time"],
    format="%d %m %Y %H:%M",
    errors="raise",
)

df = df.sort_values("Date/Time").reset_index(drop=True)

print("=" * 60)
print("WIND TURBINE DATA QUALITY AUDIT")
print("=" * 60)

print("\nTotal observations:", len(df))
print("Start date:", df["Date/Time"].min())
print("End date:", df["Date/Time"].max())

print("\nDuplicate timestamps:")
print(df["Date/Time"].duplicated().sum())

print("\nSampling intervals:")
intervals = df["Date/Time"].diff().dropna()
print(intervals.value_counts().head(10))

print("\nNegative power observations:")
print((df["LV ActivePower (kW)"] < 0).sum())

print("\nZero power observations:")
print((df["LV ActivePower (kW)"] == 0).sum())

print("\nNegative wind speed observations:")
print((df["Wind Speed (m/s)"] < 0).sum())

print("\nWind direction outside 0-360 degrees:")
direction = df["Wind Direction (°)"]
print(((direction < 0) | (direction > 360)).sum())

print("\nNumerical summary:")
print(df.describe().to_string())
