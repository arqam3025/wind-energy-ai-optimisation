
from pathlib import Path

import numpy as np
import pandas as pd

df = pd.read_csv(
    "data/processed/forecast_mpc_24h.csv",
    parse_dates=["timestamp"]
)

capacity = 2000.0
max_power = 1000.0
min_energy = 0.10 * capacity
max_energy = 0.90 * capacity

eta_charge = 0.95
eta_discharge = 0.95
dt = 10 / 60
ramp_limit = 200.0

energy_now = 0.50 * capacity

initial_export = max(
    0.0, float(df.iloc[0]["current_power_kw"])
)
previous_export = initial_export

records = []

for _, row in df.iterrows():

    actual_generation = max(
        0.0, float(row["actual_h1_kw"])
    )

    # Physical limits at the current SOC.
    max_charge = max(
        0.0,
        min(
            max_power,
            actual_generation,
            (max_energy - energy_now) / (eta_charge * dt)
        )
    )

    max_discharge = max(
        0.0,
        min(
            max_power,
            (energy_now - min_energy) * eta_discharge / dt
        )
    )

    # Feasible export range.
    min_export = actual_generation - max_charge
    max_export = actual_generation + max_discharge

    # Reactive-only target:
    # maintain the previous export if feasible.
    # No forecast or MPC optimisation is used.
    actual_export = float(np.clip(
        previous_export,
        min_export,
        max_export
    ))

    if actual_export < actual_generation:
        charge = actual_generation - actual_export
        discharge = 0.0
    else:
        charge = 0.0
        discharge = actual_export - actual_generation

    energy_now += (
        eta_charge * charge * dt
        - discharge * dt / eta_discharge
    )

    records.append({
        "timestamp": (
            row["timestamp"]
            + pd.Timedelta(minutes=10)
        ),
        "wind_generation_kw": actual_generation,
        "charge_kw": charge,
        "discharge_kw": discharge,
        "grid_export_kw": actual_export,
        "soc_percent": 100 * energy_now / capacity,
    })

    previous_export = actual_export

results = pd.DataFrame(records)

wind = results["wind_generation_kw"].to_numpy()
grid = results["grid_export_kw"].to_numpy()

wind_ramps = np.abs(np.diff(
    np.concatenate([[initial_export], wind])
))

grid_ramps = np.abs(np.diff(
    np.concatenate([[initial_export], grid])
))

overlap = np.minimum(
    results["charge_kw"].to_numpy(),
    results["discharge_kw"].to_numpy()
)

checks = {
    "SOC limits": results["soc_percent"].between(
        9.99, 90.01
    ).all(),
    "Battery power limit": (
        results["charge_kw"]
        + results["discharge_kw"]
        <= max_power + 0.01
    ).all(),
    "Nonnegative export": (
        results["grid_export_kw"] >= -0.01
    ).all(),
    "No simultaneous operation": (
        overlap <= 0.01
    ).all(),
    "Power balance": np.allclose(
        results["wind_generation_kw"]
        - results["charge_kw"]
        + results["discharge_kw"],
        results["grid_export_kw"],
        atol=0.01
    ),
}

print("=" * 65)
print("REACTIVE-ONLY BATTERY CONTROL BASELINE")
print("=" * 65)

print("Controlled intervals:", len(results))

print("\nMean absolute ramp:")
print(f"No battery: {wind_ramps.mean():.3f} kW")
print(f"Reactive only: {grid_ramps.mean():.3f} kW")

print("\nMaximum absolute ramp:")
print(f"No battery: {wind_ramps.max():.3f} kW")
print(f"Reactive only: {grid_ramps.max():.3f} kW")

print("\nViolations above 200 kW:")
print("No battery:", int((wind_ramps > 200.001).sum()))
print("Reactive only:", int((grid_ramps > 200.001).sum()))

print("\nBattery SOC:")
print(f"Minimum: {results['soc_percent'].min():.2f}%")
print(f"Maximum: {results['soc_percent'].max():.2f}%")
print(f"Final: {results['soc_percent'].iloc[-1]:.2f}%")

print("\nPhysical checks:")
for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

print(
    "\nOverall validation:",
    "PASS" if all(checks.values()) else "FAIL"
)

Path("results").mkdir(exist_ok=True)

output_path = "results/reactive_only_baseline_24h.csv"
results.to_csv(output_path, index=False)

print("\nSaved:", output_path)
