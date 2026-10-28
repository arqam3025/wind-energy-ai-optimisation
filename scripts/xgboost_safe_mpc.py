
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd

df = pd.read_csv(
    "data/processed/forecast_mpc_24h.csv",
    parse_dates=["timestamp"],
)

capacity = 2000.0
max_power = 1000.0
min_energy = 0.10 * capacity
max_energy = 0.90 * capacity

eta_charge = 0.95
eta_discharge = 0.95
dt = 10 / 60

energy_now = 0.50 * capacity

# Initial grid export before the first controlled interval.
# Assume no battery action at the forecast origin.
previous_export = max(
    0.0, float(df.iloc[0]["current_power_kw"])
)

records = []

for step, row in df.iterrows():

    forecast = np.array([
        row[f"xgboost_h{h}_kw"]
        for h in range(1, 7)
    ], dtype=float)

    actual_generation = max(
        0.0, float(row["actual_h1_kw"])
    )

    n = len(forecast)

    charge = cp.Variable(n, nonneg=True)
    discharge = cp.Variable(n, nonneg=True)
    energy = cp.Variable(n + 1)
    mode = cp.Variable(n, boolean=True)

    planned_export = forecast - charge + discharge

    constraints = [
        energy[0] == energy_now,
        energy >= min_energy,
        energy <= max_energy,
        charge <= max_power * mode,
        discharge <= max_power * (1 - mode),
        planned_export >= 0,
    ]

    for t in range(n):
        constraints.append(
            energy[t + 1] ==
            energy[t]
            + eta_charge * charge[t] * dt
            - discharge[t] * dt / eta_discharge
        )

    ramps = cp.hstack([
        planned_export[0] - previous_export,
        planned_export[1:] - planned_export[:-1],
    ])

    absolute_ramps = cp.Variable(
        n, nonneg=True
    )

    exceedance = cp.Variable(
        n, nonneg=True
    )

    constraints += [
        absolute_ramps >= ramps,
        absolute_ramps >= -ramps,
        exceedance >= absolute_ramps - 200.0,
    ]

    objective = cp.Minimize(
        cp.sum(absolute_ramps)
        + 20.0 * cp.sum(exceedance)
        + 0.1 * dt * cp.sum(charge + discharge)
    )

    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.HIGHS)

    if problem.status != "optimal":
        raise RuntimeError(
            f"Optimisation failed at step {step}: "
            f"{problem.status}"
        )

    planned_charge = max(
        0.0, float(charge.value[0])
)

    planned_discharge = max(
        0.0, float(discharge.value[0])
)

# Real-time safety correction:
# charging cannot exceed measured wind generation.
    first_charge = min(
        planned_charge,
        actual_generation
)

    first_discharge = planned_discharge

    actual_export = (
        actual_generation
        - first_charge
        + first_discharge
)

    # Record how much planned charging was curtailed.
    charge_correction = (
        planned_charge - first_charge
)

    energy_now += (
        eta_charge * first_charge * dt
        - first_discharge * dt / eta_discharge
    )

    records.append({
        "timestamp": (
            row["timestamp"]
            + pd.Timedelta(minutes=10)
        ),
        "forecast_origin": row["timestamp"],
        "wind_generation_kw": actual_generation,
        "forecast_generation_kw": forecast[0],
        "planned_charge_kw": planned_charge,
        "charge_kw": first_charge,
        "charge_correction_kw": charge_correction,
        "discharge_kw": first_discharge,
        "grid_export_kw": actual_export,
        "soc_percent": 100 * energy_now / capacity,
    })

    previous_export = actual_export

results = pd.DataFrame(records)

wind_ramps = (
    results["wind_generation_kw"].diff().abs().dropna()
)

grid_ramps = (
    results["grid_export_kw"].diff().abs().dropna()
)

simultaneous = np.minimum(
    results["charge_kw"].to_numpy(),
    results["discharge_kw"].to_numpy(),
)

tol = 0.01

checks = {
    "SOC limits": results["soc_percent"].between(
        10 - tol, 90 + tol
    ).all(),
    "Battery power limit": (
        results["charge_kw"]
        + results["discharge_kw"]
        <= max_power + tol
    ).all(),
    "Nonnegative actual grid export": (
        results["grid_export_kw"] >= -tol
    ).all(),
    "No simultaneous operation": (
        simultaneous <= tol
    ).all(),
    "Correct forecast timing": (
        results["timestamp"]
        - results["forecast_origin"]
        == pd.Timedelta(minutes=10)
    ).all(),
}

print("=" * 60)
print("XGBOOST MPC WITH REAL-TIME CHARGING PROTECTION")
print("=" * 60)

print("Controlled intervals:", len(results))

print("\nMean absolute ramp:")
print(f"Without battery: {wind_ramps.mean():.3f} kW")
print(f"With MPC:        {grid_ramps.mean():.3f} kW")

print("\nMaximum absolute ramp:")
print(f"Without battery: {wind_ramps.max():.3f} kW")
print(f"With MPC:        {grid_ramps.max():.3f} kW")

print("\nGrid ramp violations above 200 kW:")
print(int((grid_ramps > 200.001).sum()))

print("\nBattery SOC:")
print(f"Minimum: {results['soc_percent'].min():.2f}%")
print(f"Maximum: {results['soc_percent'].max():.2f}%")
print(f"Final: {results['soc_percent'].iloc[-1]:.2f}%")

print("\nPhysical and timing checks:")

for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

print(
    "\nOverall validation:",
    "PASS" if all(checks.values()) else "FAIL"
)

Path("results").mkdir(exist_ok=True)

output_path = "results/xgboost_safe_mpc_24h.csv"
results.to_csv(output_path, index=False)

print("\nSaved:", output_path)
