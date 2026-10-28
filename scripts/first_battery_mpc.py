
import cvxpy as cp
import numpy as np

# Illustrative future wind generation (kW).
# These are scenario values, NOT actual AI forecasts.
wind_forecast = np.array([
    1200, 1600, 2100, 1500, 900, 1400
], dtype=float)

horizon = len(wind_forecast)
dt = 10 / 60

# Battery specifications.
capacity = 2000.0
max_power = 1000.0
min_energy = capacity * 0.10
max_energy = capacity * 0.90
initial_energy = capacity * 0.50

eta_charge = 0.95
eta_discharge = 0.95

# Initial grid export before the planning horizon.
previous_export = 1200.0

# Nonnegative charging and discharging powers.
charge = cp.Variable(horizon, nonneg=True)
discharge = cp.Variable(horizon, nonneg=True)

# Battery energy at each time boundary.
energy = cp.Variable(horizon + 1)

# Grid export.
grid_export = (
    wind_forecast - charge + discharge
)

constraints = [
    energy[0] == initial_energy,
    energy >= min_energy,
    energy <= max_energy,
    charge <= max_power,
    discharge <= max_power,
    charge + discharge <= max_power,
    grid_export >= 0,
]

for t in range(horizon):
    constraints.append(
        energy[t + 1] ==
        energy[t]
        + eta_charge * charge[t] * dt
        - discharge[t] * dt / eta_discharge
    )

# Include the ramp from the previous export.
ramps = cp.hstack([
    grid_export[0] - previous_export,
    grid_export[1:] - grid_export[:-1],
])

# Penalise simultaneous charging/discharging
# through a small energy-throughput cost.
objective = cp.Minimize(
    cp.sum_squares(ramps)
    + 0.1 * cp.sum(charge + discharge)
)

problem = cp.Problem(objective, constraints)
problem.solve(solver=cp.CLARABEL)

print("=" * 60)
print("FIRST BATTERY MPC OPTIMISATION")
print("=" * 60)

print("Solver status:", problem.status)

if problem.status not in ["optimal", "optimal_inaccurate"]:
    raise RuntimeError("Optimisation failed")

print("\nTime | Wind | Charge | Discharge | Grid | SOC")
print("-" * 60)

for t in range(horizon):
    soc = 100 * energy.value[t + 1] / capacity

    print(
        f"{t+1:4d} | "
        f"{wind_forecast[t]:5.0f} | "
        f"{charge.value[t]:6.1f} | "
        f"{discharge.value[t]:9.1f} | "
        f"{grid_export.value[t]:6.1f} | "
        f"{soc:5.1f}%"
    )

print("\nMaximum planned grid ramp:")
print(f"{np.max(np.abs(ramps.value)):.2f} kW")

print("\nFinal battery SOC:")
print(f"{100 * energy.value[-1] / capacity:.2f}%")

print("\nOptimisation completed.")

print("\n" + "=" * 60)
print("PHYSICAL CONSTRAINT VALIDATION")
print("=" * 60)

charge_values = np.asarray(charge.value)
discharge_values = np.asarray(discharge.value)
energy_values = np.asarray(energy.value)
export_values = np.asarray(grid_export.value)

# Check the energy balance at every time step.
expected_energy = (
    energy_values[:-1]
    + eta_charge * charge_values * dt
    - discharge_values * dt / eta_discharge
)

max_energy_error = np.max(
    np.abs(energy_values[1:] - expected_energy)
)

# Check power balance.
expected_export = (
    wind_forecast - charge_values + discharge_values
)

max_power_balance_error = np.max(
    np.abs(export_values - expected_export)
)

# Check simultaneous charging/discharging.
simultaneous_power = np.minimum(
    charge_values, discharge_values
)

max_simultaneous = np.max(simultaneous_power)

tolerance = 0.01

checks = {
    "Battery SOC bounds": (
        np.all(energy_values >= min_energy - tolerance)
        and np.all(energy_values <= max_energy + tolerance)
    ),
    "Charge power limit": (
        np.all(charge_values <= max_power + tolerance)
    ),
    "Discharge power limit": (
        np.all(discharge_values <= max_power + tolerance)
    ),
    "Combined power limit": (
        np.all(
            charge_values + discharge_values
            <= max_power + tolerance
        )
    ),
    "Energy balance": max_energy_error < tolerance,
    "Grid power balance": (
        max_power_balance_error < tolerance
    ),
    "Nonnegative grid export": (
        np.all(export_values >= -tolerance)
    ),
}

for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

print(
    f"\nMaximum energy balance error: "
    f"{max_energy_error:.8f} kWh"
)

print(
    f"Maximum grid power balance error: "
    f"{max_power_balance_error:.8f} kW"
)

print(
    f"Maximum simultaneous charge/discharge: "
    f"{max_simultaneous:.6f} kW"
)

print(
    "Simultaneous operation detected:",
    bool(np.any(simultaneous_power > tolerance))
)

print(
    "\nOverall constraint validation:",
    "PASS" if all(checks.values()) else "FAIL"
)
