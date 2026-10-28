
import numpy as np
import pandas as pd

df = pd.read_csv(
    "results/persistence_driven_mpc_24h.csv",
    parse_dates=["timestamp", "forecast_origin"],
)

df["wind_ramp_kw"] = (
    df["wind_generation_kw"].diff().abs()
)

df["grid_ramp_kw"] = (
    df["grid_export_kw"].diff().abs()
)

df["forecast_error_kw"] = (
    df["forecast_generation_kw"]
    - df["wind_generation_kw"]
)

print("=" * 65)
print("PERSISTENCE MPC DIAGNOSTIC")
print("=" * 65)

print("Controlled intervals:", len(df))

print("\nBattery operation:")
print(
    "Maximum charging power:",
    f"{df['charge_kw'].max():.6f} kW"
)
print(
    "Maximum discharging power:",
    f"{df['discharge_kw'].max():.6f} kW"
)
print(
    "Total charging energy:",
    f"{df['charge_kw'].sum() / 6:.3f} kWh"
)
print(
    "Total discharging energy:",
    f"{df['discharge_kw'].sum() / 6:.3f} kWh"
)

active = (
    (df["charge_kw"] > 0.01)
    | (df["discharge_kw"] > 0.01)
)

print("Active battery intervals:", int(active.sum()))

print("\nForecast accuracy:")
print(
    "MAE:",
    f"{df['forecast_error_kw'].abs().mean():.3f} kW"
)

print("\nLargest grid-export ramps:")

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

largest = df.nlargest(6, "grid_ramp_kw")

print(
    largest[columns].to_string(
        index=False,
        float_format=lambda x: f"{x:.3f}"
    )
)

print("\nDiagnostic completed.")
