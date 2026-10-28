
import pandas as pd

df = pd.read_csv(
    "data/processed/evaluation_block_34.csv"
)

print("=" * 75)
print("BLOCK 34 — FORECASTS BEFORE SOC EXHAUSTION")
print("=" * 75)

print("\nAvailable columns:")
print(df.columns.tolist())

print("\nForecast origins around the event:")
selected = df[
    df["timestamp"].between(
        "2018-12-13 17:00:00",
        "2018-12-13 18:40:00"
    )
]

print(selected.to_string(index=False))

print("\nInvestigation completed.")
