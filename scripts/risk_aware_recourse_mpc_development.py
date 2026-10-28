
from pathlib import Path
import sys

import cvxpy as cp
import numpy as np
import pandas as pd

# Exploratory simulation:
# python scripts/risk_aware_recourse_mpc.py 6 0.5

block_id = int(sys.argv[1]) if len(sys.argv) > 1 else 6
risk_weight = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

if not np.isfinite(risk_weight) or not 0 <= risk_weight <= 1:
    raise ValueError("Risk weight must be between 0 and 1.")

df = pd.read_csv(
    f"data/processed/controller_development_blocks/development_block_{block_id}.csv",
    parse_dates=["timestamp"],
)
calibration = pd.read_csv(
    "results/multistep_uncertainty_calibration_split.csv"
)

if df.empty:
    raise ValueError("Evaluation block is empty.")

capacity = 2000.0
max_power = 1000.0
min_energy = 200.0
max_energy = 1800.0
reserve_energy = 800.0  # 40% SOC

eta_charge = 0.95
eta_discharge = 0.95
dt = 1.0 / 6.0
ramp_limit = 200.0
horizon = 6

curtailment_penalty = 50.0
reserve_penalty = 10.0
export_tracking_penalty = 10.0

quantiles = []

for h in range(1, horizon + 1):
    values = calibration.loc[
        calibration["horizon_minutes"] == h * 10,
        "calibration_quantile_kw",
    ]
    if len(values) != 1:
        raise ValueError(f"Invalid calibration horizon {h}")
    quantiles.append(float(values.iloc[0]))

quantiles = np.asarray(quantiles, dtype=float)

if not np.isfinite(quantiles).all() or (quantiles < 0).any():
    raise ValueError("Invalid quantiles.")

energy_now = 0.5 * capacity
previous_export = max(0.0, float(df.iloc[0]["current_power_kw"]))
initial_export = previous_export

records = []

for step, row in df.iterrows():

    nominal = np.maximum(
        0.0,
        np.array(
            [row[f"xgboost_h{h}_kw"] for h in range(1, 7)],
            dtype=float,
        ),
    )
    downside = np.maximum(0.0, nominal - quantiles)

    actual_generation = max(0.0, float(row["actual_h1_kw"]))

    if not np.isfinite(nominal).all() or not np.isfinite(actual_generation):
        raise ValueError(f"Invalid data at step {step}")

    scenarios = [nominal, downside]
    weights = [1.0 - risk_weight, risk_weight]

    # Shared export target for the next interval.
    shared_export = cp.Variable(nonneg=True)

    constraints = [
        shared_export >= max(0.0, previous_export - ramp_limit),
        shared_export <= previous_export + ramp_limit,
    ]

    scenario_costs = []

    for forecast in scenarios:

        charge = cp.Variable(horizon, nonneg=True)
        discharge = cp.Variable(horizon, nonneg=True)
        curtailment = cp.Variable(horizon, nonneg=True)
        energy = cp.Variable(horizon + 1)
        mode = cp.Variable(horizon, boolean=True)

        export = forecast - curtailment - charge + discharge

        tracking_error = cp.Variable(nonneg=True)
        reserve_shortfall = cp.Variable(horizon, nonneg=True)

        constraints += [
            energy[0] == energy_now,
            energy >= min_energy,
            energy <= max_energy,
            charge <= max_power * mode,
            discharge <= max_power * (1 - mode),
            curtailment <= forecast,
            charge <= forecast - curtailment,
            export >= 0,
            tracking_error >= export[0] - shared_export,
            tracking_error >= shared_export - export[0],
        ]

        for t in range(horizon):
            constraints += [
                energy[t + 1] == (
                    energy[t]
                    + eta_charge * charge[t] * dt
                    - discharge[t] * dt / eta_discharge
                ),
                energy[t + 1] + reserve_shortfall[t]
                >= reserve_energy,
            ]

        ramps = cp.hstack([
            export[0] - previous_export,
            export[1:] - export[:-1],
        ])

        abs_ramps = cp.Variable(horizon, nonneg=True)
        exceedance = cp.Variable(horizon, nonneg=True)

        constraints += [
            abs_ramps >= ramps,
            abs_ramps >= -ramps,
            exceedance >= abs_ramps - ramp_limit,
        ]

        scenario_cost = (
            cp.sum(abs_ramps)
            + 20.0 * cp.sum(exceedance)
            + 0.1 * dt * cp.sum(charge + discharge)
            + 2.0 * cp.abs(energy[horizon] - 1000.0)
            + curtailment_penalty * cp.sum(curtailment)
            + reserve_penalty * cp.sum(reserve_shortfall)
            + export_tracking_penalty * tracking_error
        )

        scenario_costs.append(scenario_cost)

    problem = cp.Problem(
        cp.Minimize(
            weights[0] * scenario_costs[0]
            + weights[1] * scenario_costs[1]
        ),
        constraints,
    )
    problem.solve(solver=cp.HIGHS)

    if problem.status != "optimal":
        raise RuntimeError(
            f"MPC failed at step {step}: {problem.status}"
        )

    planned_export = max(0.0, float(shared_export.value))

    # Simulated real-time recourse.
    # The actual next-step wind value is revealed here,
    # after the advance optimisation has been solved.
    max_charge = max(
        0.0,
        min(
            max_power,
            actual_generation,
            (max_energy - energy_now) / (eta_charge * dt),
        ),
    )
    max_discharge = max(
        0.0,
        min(
            max_power,
            (energy_now - min_energy) * eta_discharge / dt,
        ),
    )

    # Enforce the operational reserve when feasible.
    reserve_discharge_limit = max(
        0.0,
        (energy_now - reserve_energy) * eta_discharge / dt,
    )

    preferred_discharge = min(
        max_discharge,
        reserve_discharge_limit,
    )

    lower_ramp_target = max(
        0.0, previous_export - ramp_limit
    )
    upper_ramp_target = previous_export + ramp_limit

    # First try to satisfy the ramp with reserve-protected
    # discharge; release reserve only if necessary.
    required_discharge_for_ramp = max(
        0.0, lower_ramp_target - actual_generation
    )

    if required_discharge_for_ramp > preferred_discharge:
        available_discharge = max_discharge
    else:
        available_discharge = preferred_discharge

    target_export = float(
        np.clip(
            planned_export,
            lower_ramp_target,
            upper_ramp_target,
        )
    )

    actual_export = float(
        np.clip(
            target_export,
            0.0,
            actual_generation + available_discharge,
        )
    )

    if actual_export <= actual_generation:
        reduction = actual_generation - actual_export
        charge_now = min(max_charge, reduction)
        discharge_now = 0.0
        curtail_now = max(0.0, reduction - charge_now)
    else:
        charge_now = 0.0
        discharge_now = actual_export - actual_generation
        curtail_now = 0.0

    energy_now += (
        eta_charge * charge_now * dt
        - discharge_now * dt / eta_discharge
    )

    records.append({
        "timestamp": row["timestamp"] + pd.Timedelta(minutes=10),
        "wind_generation_kw": actual_generation,
        "forecast_generation_kw": nominal[0],
        "downside_forecast_kw": downside[0],
        "planned_export_kw": planned_export,
        "charge_kw": charge_now,
        "discharge_kw": discharge_now,
        "curtailment_kw": curtail_now,
        "grid_export_kw": actual_export,
        "soc_percent": 100.0 * energy_now / capacity,
        "reserve_energy_kwh": reserve_energy,
    })

    previous_export = actual_export

results = pd.DataFrame(records)

grid = results["grid_export_kw"].to_numpy()
ramps = np.abs(
    np.diff(np.concatenate([[initial_export], grid]))
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
    "No simultaneous operation": (
        np.minimum(results["charge_kw"], results["discharge_kw"])
        <= 0.01
    ).all(),
    "Curtailment limits": (
        (results["curtailment_kw"] >= -0.01)
        & (
            results["curtailment_kw"]
            <= results["wind_generation_kw"] + 0.01
        )
    ).all(),
    "Power balance": (balance_error <= 0.01).all(),
}

print("=" * 65)
print(f"RISK-AWARE MPC WITH RECOURSE: BLOCK {block_id}")
print("=" * 65)
print("Risk weight:", risk_weight)
print("Controlled intervals:", len(results))
print("Mean absolute grid ramp:", round(ramps.mean(), 3), "kW")
print("Maximum grid ramp:", round(ramps.max(), 3), "kW")
print("Ramp violations >200 kW:", int((ramps > 200.001).sum()))
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
print("Minimum SOC:", round(results["soc_percent"].min(), 3), "%")
print("Final SOC:", round(results["soc_percent"].iloc[-1], 3), "%")

print("\nPhysical checks:")
for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
print("Overall validation:", "PASS" if all(checks.values()) else "FAIL")

output_dir = Path("results/risk_aware_recourse_development")
output_dir.mkdir(parents=True, exist_ok=True)
weight_label = f"{risk_weight:.3f}".replace(".", "p")
output_path = output_dir / (
    f"recourse_mpc_block_{block_id}_weight_{weight_label}.csv"
)

if output_path.exists():
    raise FileExistsError(f"Output already exists: {output_path}")

results.to_csv(output_path, index=False)
print("Saved:", output_path)
