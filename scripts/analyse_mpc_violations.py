
import numpy as np
import pandas as pd

df = pd.read_csv(
    "results/real_wind_mpc_milp_24h.csv"
)

df["timestamp"] = pd.to_datetime(df["timestamp"])

df["grid_ramp_kw"] = (
    df["grid_export_kw"].diff().abs()
)

df["wind_ramp_kw"] = (
    df["wind_generation_kw"].diff().abs()
)

ramp_limit = 200.0

violations = df[
    df["grid_ramp_kw"] > ramp_limit + 0.001
].copy()

print("=" * 65)
print("MPC RAMP VIOLATION ANALYSIS")
print("=" * 65)

print("Total valid ramp intervals:", len(df) - 1)
print("Ramp violations:", len(violations))

print("\nViolation details:")

columns = [
    "timestamp",
    "wind_generation_kw",
    "wind_ramp_kw",
    "grid_export_kw",
    "grid_ramp_kw",
    "charge_kw",
    "discharge_kw",
    "soc_percent",
]

if violations.empty:
    print("No violations detected.")
else:
    print(
        violations[columns].to_string(
            index=False,
            float_format=lambda x: f"{x:.3f}"
        )
    )

print("\nBattery SOC at violations:")

if not violations.empty:
    print(
        f"Minimum: "
        f"{violations['soc_percent'].min():.2f}%"
    )
    print(
        f"Maximum: "
        f"{violations['soc_percent'].max():.2f}%"
    )

print("\nAnalysis completed.")
