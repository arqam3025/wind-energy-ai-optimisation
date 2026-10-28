
import cvxpy as cp
import numpy as np
import pandas as pd

df = pd.read_csv(
    "data/processed/real_wind_mpc_24h.csv"
)

wind = df["generation_kw"].to_numpy(dtype=float)

# Same battery specifications as the reactive controller.
capacity = 2000.0
max_power = 1000.0
min_energy = 0.10 * capacity
max_energy = 0.90 * capacity
eta_charge = 0.95
eta_discharge = 0.95
dt = 10 / 60

horizon = 6
energy_now = 0.50 * capacity
previous_export = None

records = []

for step in range(len(wind)):

    # Perfect future measurements: benchmark only.
    forecast = wind[step:step + horizon]
    n = len(forecast)

    charge = cp.Variable(n, nonneg=True)
    discharge = cp.Variable(n, nonneg=True)
    energy = cp.Variable(n + 1)

    export = forecast - charge + discharge

    constraints = [
        energy[0] == energy_now,
        energy >= min_energy,
        energy <= max_energy,
        charge + discharge <= max_power,
        export >= 0,
    ]

    for t in range(n):
        constraints.append(
            energy[t + 1] ==
            energy[t]
            + eta_charge * charge[t] * dt
            - discharge[t] * dt / eta_discharge
        )

    if previous_export is None:
        ramps = export[1:] - export[:-1]
    else:
        ramps = cp.hstack([
            export[0] - previous_export,
            export[1:] - export[:-1],
        ])

    objective = cp.Minimize(
        cp.sum_squares(ramps)
        + 0.1 * cp.sum(charge + discharge)
    )

    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.CLARABEL)

    if problem.status not in [
        "optimal", "optimal_inaccurate"
    ]:
        raise RuntimeError(
            f"Optimisation failed at step {step}"
        )

    first_charge = max(0.0, float(charge.value[0]))
    first_discharge = max(
        0.0, float(discharge.value[0])
    )

    actual_export = (
        wind[step] - first_charge + first_discharge
    )

    energy_now += (
        eta_charge * first_charge * dt
        - first_discharge * dt / eta_discharge
    )

    records.append({
        "timestamp": df["timestamp"].iloc[step],
        "wind_generation_kw": wind[step],
        "charge_kw": first_charge,
        "discharge_kw": first_discharge,
        "grid_export_kw": actual_export,
        "soc_percent": 100 * energy_now / capacity,
    })

    previous_export = actual_export

results = pd.DataFrame(records)

wind_ramps = results[
    "wind_generation_kw"
].diff().abs().dropna()

grid_ramps = results[
    "grid_export_kw"
].diff().abs().dropna()

print("=" * 60)
print("REAL WIND PERFECT-FORECAST MPC")
print("=" * 60)

print("Observations:", len(results))

print("\nMean absolute ramp:")
print(f"Without battery: {wind_ramps.mean():.3f} kW")
print(f"With MPC:        {grid_ramps.mean():.3f} kW")

print("\nMaximum absolute ramp:")
print(f"Without battery: {wind_ramps.max():.3f} kW")
print(f"With MPC:        {grid_ramps.max():.3f} kW")

print("\nRamp violations above 200 kW:")
print(int((grid_ramps > 200.001).sum()))

print("\nBattery SOC:")
print(
    f"Minimum: {results['soc_percent'].min():.2f}%"
)
print(
    f"Maximum: {results['soc_percent'].max():.2f}%"
)
print(
    f"Final: {results['soc_percent'].iloc[-1]:.2f}%"
)

tol = 0.01

checks = {
    "SOC limits": results["soc_percent"].between(
        10 - tol, 90 + tol
    ).all(),
    "Power limit": (
        results["charge_kw"]
        + results["discharge_kw"]
        <= max_power + tol
    ).all(),
    "Nonnegative grid export": (
        results["grid_export_kw"] >= -tol
    ).all(),
    "No significant simultaneous charging/discharging": (
        np.minimum(
            results["charge_kw"].to_numpy(),
            results["discharge_kw"].to_numpy()
        ) <= tol
    ).all(),
}

print("\nPhysical checks:")
for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

print(
    "\nOverall validation:",
    "PASS" if all(checks.values()) else "FAIL"
)

output_path = "results/real_wind_mpc_24h.csv"
results.to_csv(output_path, index=False)
print("\nSaved:", output_path)
