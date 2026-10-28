
from pathlib import Path
import sys

import cvxpy as cp
import numpy as np
import pandas as pd

# STEP 66: Causal, fixed-command scenario MPC.
# Usage:
# python scripts/causal_scenario_mpc_development.py 1 0.0

block_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
risk_weight = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0

if not 1 <= block_id <= 18:
    raise ValueError("Block must be between 1 and 18.")
if not np.isfinite(risk_weight) or not 0 <= risk_weight <= 1:
    raise ValueError("Risk weight must be between 0 and 1.")

input_path = Path(
    f"data/processed/controller_development_blocks/"
    f"development_block_{block_id}.csv"
)

calibration_path = Path(
    "results/multistep_uncertainty_calibration_split.csv"
)

df = pd.read_csv(input_path, parse_dates=["timestamp"])
calibration = pd.read_csv(calibration_path)

CAPACITY = 2000.0
MAX_POWER = 1000.0
MIN_ENERGY = 800.0
MAX_ENERGY = 1800.0
RESERVE_ENERGY = 800.0

ETA_C = 0.95
ETA_D = 0.95
DT = 1.0 / 6.0
RAMP_LIMIT = 200.0
HORIZON = 6

quantiles = []

for h in range(1, HORIZON + 1):
    selected = calibration.loc[
        calibration["horizon_minutes"] == h * 10,
        "calibration_quantile_kw"
    ]
    if len(selected) != 1:
        raise ValueError(f"Invalid calibration horizon {h}")
    quantiles.append(float(selected.iloc[0]))

quantiles = np.asarray(quantiles, dtype=float)

if not np.isfinite(quantiles).all() or (quantiles < 0).any():
    raise ValueError("Invalid calibration quantiles.")

energy_now = 1000.0
previous_export = max(0.0, float(df.iloc[0]["current_power_kw"]))
initial_export = previous_export

records = []

for step, row in df.iterrows():
    nominal = np.maximum(
        0.0,
        np.array(
            [row[f"xgboost_h{h}_kw"] for h in range(1, 7)],
            dtype=float
        )
    )
    downside = np.maximum(0.0, nominal - quantiles)

    if not np.isfinite(nominal).all():
        raise ValueError(f"Invalid forecasts at step {step}")

    # A true nominal-only baseline has no downside constraints.
    if risk_weight == 0.0:
        scenarios = [nominal]
        weights = [1.0]
    else:
        scenarios = [nominal, downside]
        weights = [1.0 - risk_weight, risk_weight]

    # First-stage commands: identical across all scenarios.
    charge_first = cp.Variable(nonneg=True)
    discharge_first = cp.Variable(nonneg=True)
    curtail_first = cp.Variable(nonneg=True)
    mode_first = cp.Variable(boolean=True)

    constraints = [
        charge_first <= MAX_POWER * mode_first,
        discharge_first <= MAX_POWER * (1 - mode_first),
        charge_first <= (
            MAX_ENERGY - energy_now
        ) / (ETA_C * DT),
        discharge_first <= (
            energy_now - MIN_ENERGY
        ) * ETA_D / DT,
    ]

    scenario_costs = []

    for forecast in scenarios:
        charge = cp.Variable(HORIZON, nonneg=True)
        discharge = cp.Variable(HORIZON, nonneg=True)
        curtailment = cp.Variable(HORIZON, nonneg=True)
        energy = cp.Variable(HORIZON + 1)
        mode = cp.Variable(HORIZON, boolean=True)

        export = forecast - curtailment - charge + discharge

        constraints += [
            energy[0] == energy_now,
            energy >= MIN_ENERGY,
            energy <= MAX_ENERGY,
            charge <= MAX_POWER * mode,
            discharge <= MAX_POWER * (1 - mode),
            curtailment <= forecast,
            charge <= forecast - curtailment,
            export >= 0,

            # Nonanticipativity at the first interval.
            discharge[0] == discharge_first,
            curtailment[0] == curtail_first,
            mode[0] == mode_first,
        ]

        # Exact minimum of requested charge and scenario wind.
        # Binary selector keeps this formulation compatible
        # with the mixed-integer HiGHS solver.
        charge_selector = cp.Variable(boolean=True)
        big_m = MAX_POWER + max(float(forecast[0]), MAX_POWER)

        constraints += [
            charge[0] <= charge_first,
            charge[0] <= forecast[0],
            charge[0] >= charge_first - big_m * charge_selector,
            charge[0] >= forecast[0] - big_m * (1 - charge_selector),
        ]

        for t in range(HORIZON):
            constraints += [
                energy[t + 1] == (
                    energy[t]
                    + ETA_C * charge[t] * DT
                    - discharge[t] * DT / ETA_D
                )
            ]

        ramps = cp.hstack([
            export[0] - previous_export,
            export[1:] - export[:-1]
        ])

        abs_ramps = cp.Variable(HORIZON, nonneg=True)
        exceedance = cp.Variable(HORIZON, nonneg=True)
        reserve_shortfall = cp.Variable(HORIZON, nonneg=True)

        constraints += [
            abs_ramps >= ramps,
            abs_ramps >= -ramps,
            exceedance >= abs_ramps - RAMP_LIMIT,
            energy[1:] + reserve_shortfall >= RESERVE_ENERGY,
        ]

        scenario_cost = (
            cp.sum(abs_ramps)
            + 20.0 * cp.sum(exceedance)
            + 0.1 * DT * cp.sum(charge + discharge)
            + 2.0 * cp.abs(energy[HORIZON] - 1000.0)
            + 50.0 * cp.sum(curtailment)
            + 10.0 * cp.sum(reserve_shortfall)
        )

        scenario_costs.append(scenario_cost)

    objective = sum(
        w * cost
        for w, cost in zip(weights, scenario_costs)
    )

    problem = cp.Problem(cp.Minimize(objective), constraints)
    problem.solve(solver=cp.HIGHS)

    if problem.status not in ("optimal", "optimal_inaccurate"):
        raise RuntimeError(
            f"Block {block_id}, step {step}: {problem.status}"
        )

    # COMMIT COMMANDS BEFORE REVEALING ACTUAL WIND.
    committed_charge = max(0.0, float(charge_first.value))
    committed_discharge = max(0.0, float(discharge_first.value))
    committed_curtail = max(0.0, float(curtail_first.value))

    # Actual wind is revealed only in the simulation stage.
    actual_generation = max(0.0, float(row["actual_h1_kw"]))

    # Physical fallback: insufficient wind reduces charging,
    # then curtailment. Discharge remains committed.
    # Physical charging limit: respect wind availability,
    # battery power rating, and the 90% maximum SOC.
    available_energy_capacity = max(
        0.0,
        MAX_ENERGY - energy_now
    )

    maximum_safe_charge = (
        available_energy_capacity / (ETA_C * DT)
    )

    actual_charge = min(
        committed_charge,
        actual_generation,
        MAX_POWER,
        maximum_safe_charge
    )
    # Physical safety limit: preserve the 40% SOC reserve.
    available_energy_for_discharge = max(
        0.0,
        energy_now + ETA_C * actual_charge * DT - MIN_ENERGY
    )

    maximum_safe_discharge = (
        available_energy_for_discharge * ETA_D / DT
    )

    actual_discharge = min(
        committed_discharge,
        MAX_POWER,
        maximum_safe_discharge
    )
    available_after_charge = max(
        0.0, actual_generation - actual_charge
    )
    actual_curtail = min(
        committed_curtail, available_after_charge
    )

    actual_export = (
        actual_generation
        - actual_charge
        - actual_curtail
        + actual_discharge
    )

    energy_now += (
        ETA_C * actual_charge * DT
        - actual_discharge * DT / ETA_D
    )

    records.append({
        "timestamp": row["timestamp"] + pd.Timedelta(minutes=10),
        "wind_generation_kw": actual_generation,
        "forecast_generation_kw": nominal[0],
        "downside_forecast_kw": downside[0],
        "committed_charge_kw": committed_charge,
        "committed_discharge_kw": committed_discharge,
        "committed_curtailment_kw": committed_curtail,
        "charge_kw": actual_charge,
        "discharge_kw": actual_discharge,
        "curtailment_kw": actual_curtail,
        "grid_export_kw": actual_export,
        "soc_percent": 100.0 * energy_now / CAPACITY,
        "reserve_energy_kwh": RESERVE_ENERGY,
    })

    previous_export = actual_export

results = pd.DataFrame(records)

grid = results["grid_export_kw"].to_numpy()
ramps = np.abs(
    np.diff(np.concatenate([[initial_export], grid]))
)

balance_error = (
    results["wind_generation_kw"]
    - results["charge_kw"]
    - results["curtailment_kw"]
    + results["discharge_kw"]
    - results["grid_export_kw"]
).abs().max()

checks = {
    "SOC bounds": results["soc_percent"].between(
        9.99, 90.01
    ).all(),
    "Battery power": (
        results["charge_kw"] + results["discharge_kw"]
        <= MAX_POWER + 0.01
    ).all(),
    "No simultaneous charging/discharging": (
        np.minimum(
            results["charge_kw"],
            results["discharge_kw"]
        ) <= 0.01
    ).all(),
    "Power balance": balance_error <= 0.01,
    "Nonnegative export": (
        results["grid_export_kw"] >= -0.01
    ).all(),
    "Curtailment bounds": (
        (results["curtailment_kw"] >= -0.01)
        & (
            results["curtailment_kw"]
            <= results["wind_generation_kw"] + 0.01
        )
    ).all(),
}

print("=" * 65)
print("STEP 110 - ADAPTIVE-CHARGING CAUSAL MPC")
print("=" * 65)
print("Block:", block_id)
print("Risk weight:", risk_weight)
print("Controlled intervals:", len(results))
print("Mean absolute grid ramp:", round(ramps.mean(), 3), "kW")
print("Maximum grid ramp:", round(ramps.max(), 3), "kW")
print("Ramp violations >200 kW:", int((ramps > 200.001).sum()))
print(
    "Battery throughput:",
    round(
        (
            results["charge_kw"] + results["discharge_kw"]
        ).sum() * DT,
        3
    ),
    "kWh"
)
print(
    "Curtailment:",
    round(results["curtailment_kw"].sum() * DT, 3),
    "kWh"
)
print("Final SOC:", round(results["soc_percent"].iloc[-1], 3), "%")

print("\nPhysical checks:")
for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

if not all(checks.values()):
    raise RuntimeError("Physical validation failed.")

output_dir = Path("results/adaptive_charging_mpc_development")
output_dir.mkdir(parents=True, exist_ok=True)

weight_label = f"{risk_weight:.3f}".replace(".", "p")
output_path = output_dir / (
    f"adaptive_charging_mpc_block_{block_id}_weight_{weight_label}.csv"
)

# Never overwrite previous experiment results.
with output_path.open("x", encoding="utf-8", newline="") as f:
    results.to_csv(f, index=False)

print("\nSaved:", output_path)
print("Step 66 completed successfully.")






