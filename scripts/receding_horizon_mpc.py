
import cvxpy as cp
import numpy as np

# Illustrative generation scenario, not AI forecasts.
wind = np.array([
    1200, 1600, 2100, 1500, 900, 1400,
    1800, 2300, 1700, 1100, 800, 1500
], dtype=float)

capacity = 2000.0
max_power = 1000.0
min_energy = 0.10 * capacity
max_energy = 0.90 * capacity
eta_charge = 0.95
eta_discharge = 0.95
dt = 10 / 60

horizon = 6
energy_now = 0.50 * capacity
previous_export = 1200.0

records = []

for step in range(len(wind)):

    # Perfect future information for initial testing only.
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
            f"MPC failed at step {step + 1}"
        )

    # Apply ONLY the first planned action.
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
        "step": step + 1,
        "wind": wind[step],
        "charge": first_charge,
        "discharge": first_discharge,
        "export": actual_export,
        "soc": 100 * energy_now / capacity,
    })

    previous_export = actual_export

print("=" * 65)
print("RECEDING-HORIZON BATTERY MPC")
print("=" * 65)

print("Step | Wind | Charge | Discharge | Export | SOC")
print("-" * 65)

for row in records:
    print(
        f"{row['step']:4d} | "
        f"{row['wind']:4.0f} | "
        f"{row['charge']:6.1f} | "
        f"{row['discharge']:9.1f} | "
        f"{row['export']:6.1f} | "
        f"{row['soc']:5.1f}%"
    )

exports = np.array([r["export"] for r in records])
winds = np.array([r["wind"] for r in records])

grid_ramps = np.abs(np.diff(exports))
wind_ramps = np.abs(np.diff(winds))

print("\nMean absolute wind ramp:")
print(f"{wind_ramps.mean():.3f} kW")

print("\nMean absolute grid ramp:")
print(f"{grid_ramps.mean():.3f} kW")

print("\nMaximum grid ramp:")
print(f"{grid_ramps.max():.3f} kW")

print("\nFinal SOC:")
print(f"{records[-1]['soc']:.2f}%")

print("\nReceding-horizon simulation completed.")

print("\n" + "=" * 65)
print("RECEDING-HORIZON PHYSICAL VALIDATION")
print("=" * 65)

charges = np.array([r["charge"] for r in records])
discharges = np.array([r["discharge"] for r in records])
soc_values = np.array([r["soc"] for r in records])
exports = np.array([r["export"] for r in records])

tol = 0.01

# Reconstruct the battery energy trajectory.
reconstructed_energy = initial = 0.50 * capacity
energy_errors = []

for i in range(len(records)):
    expected_next = (
        reconstructed_energy
        + eta_charge * charges[i] * dt
        - discharges[i] * dt / eta_discharge
    )

    reported_next = soc_values[i] * capacity / 100
    energy_errors.append(
        abs(expected_next - reported_next)
    )
    reconstructed_energy = reported_next

simultaneous = np.minimum(charges, discharges)

checks = {
    "SOC within 10%-90%": (
        np.all(soc_values >= 10 - tol)
        and np.all(soc_values <= 90 + tol)
    ),
    "Battery power within 1000 kW": (
        np.all(charges + discharges <= max_power + tol)
    ),
    "Energy balance": (
        max(energy_errors) < tol
    ),
    "Grid export nonnegative": (
        np.all(exports >= -tol)
    ),
    "No significant simultaneous charge/discharge": (
        np.all(simultaneous <= tol)
    ),
}

for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

print(
    f"\nMaximum energy balance error: "
    f"{max(energy_errors):.8f} kWh"
)

print(
    f"Maximum simultaneous charge/discharge: "
    f"{simultaneous.max():.6f} kW"
)

print(
    "\nOverall validation:",
    "PASS" if all(checks.values()) else "FAIL"
)
