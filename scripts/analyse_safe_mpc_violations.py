
import pandas as pd
import numpy as np

source = pd.read_csv(
    "data/processed/forecast_mpc_24h.csv"
)

df = pd.read_csv(
    "results/xgboost_safe_mpc_24h.csv",
    parse_dates=["timestamp"]
)

initial_export = max(
    0.0, float(source["current_power_kw"].iloc[0])
)

initial_wind = initial_export

df["previous_export_kw"] = (
    df["grid_export_kw"].shift(1)
)

df.loc[0, "previous_export_kw"] = initial_export

df["previous_wind_kw"] = (
    df["wind_generation_kw"].shift(1)
)

df.loc[0, "previous_wind_kw"] = initial_wind

df["grid_ramp_kw"] = (
    df["grid_export_kw"]
    - df["previous_export_kw"]
)

df["wind_ramp_kw"] = (
    df["wind_generation_kw"]
    - df["previous_wind_kw"]
)

df["forecast_error_kw"] = (
    df["forecast_generation_kw"]
    - df["wind_generation_kw"]
)

violations = df[
    df["grid_ramp_kw"].abs() > 200.001
].copy()

print("=" * 75)
print("XGBOOST SAFE MPC: RAMP VIOLATION ANALYSIS")
print("=" * 75)

print("Controlled intervals:", len(df))
print("Ramp violations:", len(violations))

columns = [
    "timestamp",
    "wind_generation_kw",
    "forecast_generation_kw",
    "forecast_error_kw",
    "wind_ramp_kw",
    "grid_ramp_kw",
    "charge_kw",
    "discharge_kw",
    "soc_percent",
]

print("\nIntervals exceeding 200 kW:")
print(
    violations[columns].to_string(
        index=False,
        float_format=lambda x: f"{x:.3f}"
    )
)

print("\nSummary:")

print(
    "Mean absolute forecast error at violations:",
    f"{violations['forecast_error_kw'].abs().mean():.3f} kW"
)

print(
    "Maximum absolute grid ramp:",
    f"{df['grid_ramp_kw'].abs().max():.3f} kW"
)

print(
    "Violations with charging:",
    int((violations["charge_kw"] > 0.01).sum())
)

print(
    "Violations with discharging:",
    int((violations["discharge_kw"] > 0.01).sum())
)

print(
    "Violations near minimum SOC:",
    int((violations["soc_percent"] <= 10.1).sum())
)

print(
    "Violations near maximum SOC:",
    int((violations["soc_percent"] >= 89.9).sum())
)

print("\nAnalysis completed.")
