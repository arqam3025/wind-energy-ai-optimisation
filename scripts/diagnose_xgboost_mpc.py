
import pandas as pd

df = pd.read_csv(
    "results/xgboost_driven_mpc_24h.csv",
    parse_dates=["timestamp"]
)

tolerance = 0.01

invalid = df[
    df["grid_export_kw"] < -tolerance
].copy()

print("=" * 65)
print("XGBOOST MPC PHYSICAL FEASIBILITY DIAGNOSTIC")
print("=" * 65)

print("Total controlled intervals:", len(df))
print("Negative export intervals:", len(invalid))

print(
    "Minimum grid export:",
    f"{df['grid_export_kw'].min():.3f} kW"
)

print(
    "Total implied grid import:",
    f"{(-df['grid_export_kw'].clip(upper=0)).sum() / 6:.3f} kWh"
)

if not invalid.empty:
    invalid["forecast_error_kw"] = (
        invalid["forecast_generation_kw"]
        - invalid["wind_generation_kw"]
    )

    print("\nIntervals with infeasible export:")

    columns = [
        "timestamp",
        "forecast_generation_kw",
        "wind_generation_kw",
        "forecast_error_kw",
        "charge_kw",
        "discharge_kw",
        "grid_export_kw",
        "soc_percent",
    ]

    print(
        invalid[columns].to_string(
            index=False,
            float_format=lambda x: f"{x:.3f}"
        )
    )

print("\nBattery activity:")

active = (
    (df["charge_kw"] > tolerance)
    | (df["discharge_kw"] > tolerance)
)

print("Active intervals:", int(active.sum()))

print(
    "Charging energy:",
    f"{df['charge_kw'].sum() / 6:.3f} kWh"
)

print(
    "Discharging energy:",
    f"{df['discharge_kw'].sum() / 6:.3f} kWh"
)

print("\nDiagnostic completed.")
