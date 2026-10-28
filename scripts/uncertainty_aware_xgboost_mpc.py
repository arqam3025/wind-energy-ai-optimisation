
from pathlib import Path
import sys

import cvxpy as cp
import numpy as np
import pandas as pd

# Usage:
# python scripts/uncertainty_aware_xgboost_mpc.py 6 1.0

block_id = int(sys.argv[1]) if len(sys.argv) > 1 else 6
reserve_strength = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0

if not np.isfinite(reserve_strength) or reserve_strength < 0:
    raise ValueError("Reserve strength must be finite and nonnegative.")

input_path = Path(f"data/processed/evaluation_block_{block_id}.csv")
calibration_path = Path("results/multistep_uncertainty_calibration.csv")

df = pd.read_csv(input_path, parse_dates=["timestamp"])
calibration = pd.read_csv(calibration_path)

if df.empty:
    raise ValueError("Evaluation block is empty.")

capacity = 2000.0
max_power = 1000.0
min_energy = 0.10 * capacity
max_energy = 0.90 * capacity

eta_charge = 0.95
eta_discharge = 0.95
dt = 10 / 60
ramp_limit = 200.0
horizon = 6

curtailment_penalty = 50.0
reserve_penalty = 5.0

quantiles = []

for h in range(1, horizon + 1):
    match = calibration.loc[
        calibration["horizon_minutes"] == h * 10,
        "calibration_quantile_kw",
    ]
    if len(match) != 1:
        raise ValueError(f"Missing or duplicate quantile for horizon {h}.")
    quantiles.append(float(match.iloc[0]))

quantiles = np.asarray(quantiles, dtype=float)

if not np.isfinite(quantiles).all() or (quantiles < 0).any():
    raise ValueError("Invalid calibration quantiles.")

# Reserve above minimum operating energy.
reserve_targets = np.minimum(
    max_energy,
    min_energy + reserve_strength * quantiles * dt / eta_discharge,
)

energy_now = 0.50 * capacity
previous_export = max(0.0, float(df.iloc[0]["current_power_kw"]))
initial_export = previous_export

records = []

for step, row in df.iterrows():

    forecast = np.maximum(
        0.0,
        np.array(
            [row[f"xgboost_h{h}_kw"] for h in range(1, horizon + 1)],
            dtype=float,
        ),
    )

    actual_generation = max(0.0, float(row["actual_h1_kw"]))

    if not np.isfinite(forecast).all() or not np.isfinite(actual_generation):
        raise ValueError(f"Non-finite forecast or generation at step {step}.")

    n = len(forecast)

    charge = cp.Variable(n, nonneg=True)
    discharge = cp.Variable(n, nonneg=True)
    curtailment = cp.Variable(n, nonneg=True)
    energy = cp.Variable(n + 1)
    mode = cp.Variable(n, boolean=True)

    reserve_shortfall = cp.Variable(n, nonneg=True)

    planned_export = forecast - curtailment - charge + discharge

    constraints = [
        energy[0] == energy_now,
        energy >= min_energy,
        energy <= max_energy,
        charge <= max_power * mode,
        discharge <= max_power * (1 - mode),
        curtailment <= forecast,
        charge <= forecast - curtailment,
        planned_export >= 0,
    ]

    for t in range(n):
        constraints += [
            energy[t + 1] == (
                energy[t]
                + eta_charge * charge[t] * dt
                - discharge[t] * dt / eta_discharge
            ),
            energy[t + 1] + reserve_shortfall[t] >= reserve_targets[t],
        ]

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
        + 2.0 * cp.abs(energy[n] - 0.50 * capacity)
        + curtailment_penalty * cp.sum(curtailment)
        + reserve_penalty * cp.sum(reserve_shortfall)
    )

    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.HIGHS)

    if problem.status not in ("optimal", "optimal_inaccurate"):
        raise RuntimeError(
            f"Uncertainty-aware MPC failed at step {step}: {problem.status}"
        )

    planned_charge = max(0.0, float(charge.value[0]))
    planned_discharge = max(0.0, float(discharge.value[0]))
    planned_curtailment = max(0.0, float(curtailment.value[0]))

    charge_soc_limit = (
        (max_energy - energy_now) / (eta_charge * dt)
    )
    discharge_soc_limit = (
        (energy_now - min_energy) * eta_discharge / dt
    )

    max_charge = max(
        0.0,
        min(max_power, actual_generation, charge_soc_limit),
    )
    max_discharge = max(
        0.0,
        min(max_power, discharge_soc_limit),
    )

    lower_target = max(0.0, previous_export - ramp_limit)
    upper_target = previous_export + ramp_limit

    planned_first_export = (
        actual_generation
        - planned_curtailment
        - planned_charge
        + planned_discharge
    )

    target_export = float(
        np.clip(planned_first_export, lower_target, upper_target)
    )

    min_feasible_export = 0.0
    max_feasible_export = actual_generation + max_discharge

    actual_export = float(
        np.clip(
            target_export,
            min_feasible_export,
            max_feasible_export,
        )
    )

    if actual_export <= actual_generation:
        required_reduction = actual_generation - actual_export
        first_charge = min(max_charge, required_reduction)
        first_discharge = 0.0
        first_curtailment = max(
            0.0, required_reduction - first_charge
        )
    else:
        first_charge = 0.0
        first_discharge = actual_export - actual_generation
        first_curtailment = 0.0

    energy_now += (
        eta_charge * first_charge * dt
        - first_discharge * dt / eta_discharge
    )

    records.append({
        "timestamp": row["timestamp"] + pd.Timedelta(minutes=10),
        "wind_generation_kw": actual_generation,
        "forecast_generation_kw": forecast[0],
        "planned_charge_kw": planned_charge,
        "planned_discharge_kw": planned_discharge,
        "planned_curtailment_kw": planned_curtailment,
        "charge_kw": first_charge,
        "discharge_kw": first_discharge,
        "curtailment_kw": first_curtailment,
        "grid_export_kw": actual_export,
        "soc_percent": 100 * energy_now / capacity,
        "reserve_target_kwh": reserve_targets[0],
        "planned_reserve_shortfall_kwh": max(
            0.0, float(reserve_shortfall.value[0])
        ),
    })

    previous_export = actual_export

results = pd.DataFrame(records)

wind = results["wind_generation_kw"].to_numpy()
grid = results["grid_export_kw"].to_numpy()

wind_ramps = np.abs(
    np.diff(np.concatenate([[initial_export], wind]))
)
grid_ramps = np.abs(
    np.diff(np.concatenate([[initial_export], grid]))
)

overlap = np.minimum(
    results["charge_kw"], results["discharge_kw"]
)

balance_error = (
    results["wind_generation_kw"]
    - results["curtailment_kw"]
    - results["charge_kw"]
    + results["discharge_kw"]
    - results["grid_export_kw"]
).abs()

checks = {
    "SOC limits": results["soc_percent"].between(9.99, 90.01).all(),
    "Battery power limit": (
        results["charge_kw"] + results["discharge_kw"]
        <= max_power + 0.01
    ).all(),
    "Nonnegative grid export": (
        results["grid_export_kw"] >= -0.01
    ).all(),
    "No simultaneous operation": (overlap <= 0.01).all(),
    "Curtailment limits": (
        (results["curtailment_kw"] >= -0.01)
        & (
            results["curtailment_kw"]
            <= results["wind_generation_kw"] + 0.01
        )
    ).all(),
    "Power balance": (balance_error <= 0.01).all(),
}

violations = int((grid_ramps > ramp_limit + 0.001).sum())

print("=" * 65)
print(
    f"UNCERTAINTY-AWARE XGBOOST MPC: BLOCK {block_id}"
)
print("=" * 65)
print("Reserve strength:", reserve_strength)
print("Controlled intervals:", len(results))
print("Mean absolute grid ramp:", round(grid_ramps.mean(), 3), "kW")
print("Maximum grid ramp:", round(grid_ramps.max(), 3), "kW")
print("Ramp violations >200 kW:", violations)
print(
    "Battery throughput:",
    round(
        (results["charge_kw"] + results["discharge_kw"]).sum() * dt,
        3,
    ),
    "kWh",
)
print(
    "Curtailed energy:",
    round(results["curtailment_kw"].sum() * dt, 3),
    "kWh",
)
print(
    "Final SOC:",
    round(results["soc_percent"].iloc[-1], 2),
    "%",
)

print("\nPhysical checks:")
for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

print(
    "Overall validation:",
    "PASS" if all(checks.values()) else "FAIL",
)

output_dir = Path("results/uncertainty_aware")
output_dir.mkdir(parents=True, exist_ok=True)

strength_label = f"{reserve_strength:.3f}".replace(".", "p")

output_path = output_dir / (
    f"uncertainty_mpc_block_{block_id}_lambda_{strength_label}.csv"
)

if output_path.exists():
    raise FileExistsError(
        f"Output already exists; refusing to overwrite: {output_path}"
    )

results.to_csv(output_path, index=False)
print("Saved:", output_path)
