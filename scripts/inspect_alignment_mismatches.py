
import numpy as np
import pandas as pd

df = pd.read_csv(
    "results/multistep_mpc_test_forecasts.csv",
    parse_dates=["timestamp"]
)

df = df.sort_values("timestamp").reset_index(drop=True)

# Compare persistence forecasts with current power.
df["persistence_error_kw"] = (
    df["persistence_h1_kw"] - df["current_power_kw"]
)

# Compare actual h1 with next current-power observation.
df["next_timestamp"] = df["timestamp"].shift(-1)
df["next_current_power_kw"] = df["current_power_kw"].shift(-1)

continuous = (
    df["next_timestamp"] - df["timestamp"]
    == pd.Timedelta(minutes=10)
)

df["actual_alignment_error_kw"] = (
    df["actual_h1_kw"] - df["next_current_power_kw"]
)

persistence_bad = df[
    df["persistence_error_kw"].abs() > 0.001
]

actual_bad = df[
    continuous
    & (df["actual_alignment_error_kw"].abs() > 0.001)
]

print("=" * 70)
print("FORECAST AND ACTUAL ALIGNMENT INVESTIGATION")
print("=" * 70)

print("Total forecast origins:", len(df))

print("\nPersistence mismatches:", len(persistence_bad))
print("Maximum persistence error:",
      f"{df['persistence_error_kw'].abs().max():.6f} kW")

print("\nFirst 10 persistence mismatches:")
print(
    persistence_bad[
        ["timestamp", "current_power_kw",
         "persistence_h1_kw", "persistence_error_kw"]
    ].head(10).to_string(index=False)
)

print("\nActual alignment mismatches:", len(actual_bad))
print("Maximum actual alignment error:",
      f"{df.loc[continuous, 'actual_alignment_error_kw'].abs().max():.6f} kW")

print("\nFirst 10 actual alignment mismatches:")
print(
    actual_bad[
        ["timestamp", "actual_h1_kw",
         "next_current_power_kw",
         "actual_alignment_error_kw"]
    ].head(10).to_string(index=False)
)

print("\nMismatch values near zero:")
print(
    "Persistence:",
    int((persistence_bad["current_power_kw"].abs() < 2).sum())
)

print(
    "Actual:",
    int((actual_bad["next_current_power_kw"].abs() < 2).sum())
)

print("\nInvestigation completed.")
