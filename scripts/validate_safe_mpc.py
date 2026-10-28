
import numpy as np
import pandas as pd

df = pd.read_csv(
    "results/xgboost_safe_mpc_24h.csv",
    parse_dates=["timestamp", "forecast_origin"]
)

dt = 10 / 60
capacity = 2000.0
eta_charge = 0.95
eta_discharge = 0.95

corrections = df["charge_correction_kw"]
active_corrections = corrections > 0.01

planned_charge = df["planned_charge_kw"]
actual_charge = df["charge_kw"]
discharge = df["discharge_kw"]
generation = df["wind_generation_kw"]
export = df["grid_export_kw"]

# Reconstruct battery SOC from executed actions.
energy = 0.50 * capacity
reconstructed_soc = []

for charge_kw, discharge_kw in zip(
    actual_charge, discharge
):
    energy += (
        eta_charge * charge_kw * dt
        - discharge_kw * dt / eta_discharge
    )
    reconstructed_soc.append(100 * energy / capacity)

soc_error = np.abs(
    np.array(reconstructed_soc)
    - df["soc_percent"].to_numpy()
)

balance_error = np.abs(
    generation - actual_charge + discharge - export
)

print("=" * 65)
print("SAFE XGBOOST MPC VALIDATION")
print("=" * 65)

print("\nReal-time charging corrections:")
print("Corrected intervals:", int(active_corrections.sum()))
print(
    "Maximum charging correction:",
    f"{corrections.max():.3f} kW"
)
print(
    "Total curtailed charging request:",
    f"{corrections.sum() * dt:.3f} kWh"
)

print("\nBattery operation:")
print(
    "Planned charging energy:",
    f"{planned_charge.sum() * dt:.3f} kWh"
)
print(
    "Executed charging energy:",
    f"{actual_charge.sum() * dt:.3f} kWh"
)
print(
    "Executed discharging energy:",
    f"{discharge.sum() * dt:.3f} kWh"
)
print(
    "Final SOC:",
    f"{df['soc_percent'].iloc[-1]:.3f}%"
)

print("\nConsistency checks:")
checks = {
    "Charging does not exceed wind": (
        actual_charge <= generation + 0.01
    ).all(),
    "Executed charging <= planned": (
        actual_charge <= planned_charge + 0.01
    ).all(),
    "SOC reconstruction": soc_error.max() < 0.01,
    "Power balance": balance_error.max() < 0.01,
    "No negative export": (export >= -0.01).all(),
}

for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

print(
    "\nOverall validation:",
    "PASS" if all(checks.values()) else "FAIL"
)
