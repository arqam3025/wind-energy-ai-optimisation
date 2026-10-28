
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

ramp_limit = 200.0
horizon = 6

energy_now = 0.50 * capacity
previous_export = max(
    0.0, float(df.iloc[0]["current_power_kw"])
)

records = []

for step, row in df.iterrows():

    forecast = np.array([
        row[f"xgboost_h{h}_kw"]
        for h in range(1, horizon + 1)
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

    abs_ramps = cp.Variable(n, nonneg=True)
    exceedance = cp.Variable(n, nonneg=True)

    constraints += [
        abs_ramps >= ramps,
        abs_ramps >= -ramps,
        exceedance >= abs_ramps - ramp_limit,
    ]

    objective = cp.Minimize(
        cp.sum(abs_ramps)
        + 20.0 * cp.sum(exceedance)
        + 0.1 * dt * cp.sum(charge + discharge)
    )

    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.HIGHS)

    if problem.status != "optimal":
        raise RuntimeError(
            f"MPC failed at step {step}: {problem.status}"
        )

    planned_charge = max(
        0.0, float(charge.value[0])
    )

    planned_discharge = max(
        0.0, float(discharge.value[0])
    )

    # Real-time feasible charging/discharging limits.
    charge_soc_limit = (
        (max_energy - energy_now)
        / (eta_charge * dt)
    )

    discharge_soc_limit = (
        (energy_now - min_energy)
        * eta_discharge / dt
    )

    max_charge = max(
        0.0,
        min(max_power, actual_generation, charge_soc_limit)
    )

    max_discharge = max(
        0.0,
        min(max_power, discharge_soc_limit)
    )

    # Desired grid export closest to the previous
    # export, while respecting the 200 kW ramp band.
    lower_target = max(
        0.0, previous_export - ramp_limit
    )

    upper_target = previous_export + ramp_limit

    # Feasible grid-export range for the battery.
    min_feasible_export = actual_generation - max_charge
    max_feasible_export = actual_generation + max_discharge

    # First preserve the planned MPC export when possible.
    planned_first_export = (
        actual_generation
        - planned_charge
        + planned_discharge
    )

    target_export = float(np.clip(
        planned_first_export,
        lower_target,
        upper_target
    ))

    # Project onto physically feasible export range.
    actual_export = float(np.clip(
        target_export,
        min_feasible_export,
        max_feasible_export
    ))

    if actual_export <= actual_generation:
        first_charge = actual_generation - actual_export
        first_discharge = 0.0
    else:
        first_charge = 0.0
        first_discharge = actual_export - actual_generation

    energy_now += (
        eta_charge * first_charge * dt
        - first_discharge * dt / eta_discharge
    )

    records.append({
        "timestamp": (
            row["timestamp"]
            + pd.Timedelta(minutes=10)
        ),
        "wind_generation_kw": actual_generation,
        "forecast_generation_kw": forecast[0],
        "planned_charge_kw": planned_charge,
        "planned_discharge_kw": planned_discharge,
        "charge_kw": first_charge,
        "discharge_kw": first_discharge,
        "grid_export_kw": actual_export,
        "soc_percent": 100 * energy_now / capacity,
    })

    previous_export = actual_export

results = pd.DataFrame(records)

initial_export = max(
    0.0, float(df.iloc[0]["current_power_kw"])
)

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
    "Nonnegative grid export": (
        results["grid_export_kw"] >= -0.01
    ).all(),
    "No simultaneous operation": (
        overlap <= 0.01
    ).all(),
}

print("=" * 65)
print("XGBOOST MPC WITH REACTIVE RAMP PROTECTION")
print("=" * 65)

print("Controlled intervals:", len(results))

print("\nMean absolute ramp:")
print(f"No battery: {wind_ramps.mean():.3f} kW")
print(f"With control: {grid_ramps.mean():.3f} kW")

print("\nMaximum absolute ramp:")
print(f"No battery: {wind_ramps.max():.3f} kW")
print(f"With control: {grid_ramps.max():.3f} kW")

print("\nViolations above 200 kW:")
print("No battery:", int((wind_ramps > 200.001).sum()))
print("With control:", int((grid_ramps > 200.001).sum()))

print("\nFinal SOC:")
print(f"{results['soc_percent'].iloc[-1]:.2f}%")

print("\nPhysical checks:")
for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

print(
    "\nOverall validation:",
    "PASS" if all(checks.values()) else "FAIL"
)

Path("results").mkdir(exist_ok=True)

output_path = "results/xgboost_mpc_reactive_safety_24h.csv"
results.to_csv(output_path, index=False)

print("\nSaved:", output_path)
