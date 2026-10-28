
import numpy as np
import pandas as pd

CAPACITY_KWH = 2000.0
MIN_ENERGY_KWH = 0.10 * CAPACITY_KWH
MAX_ENERGY_KWH = 0.90 * CAPACITY_KWH

MAX_POWER_KW = 1000.0
DT_HOURS = 1.0 / 6.0
ETA_CHARGE = 0.95
ETA_DISCHARGE = 0.95
RAMP_LIMIT_KW = 200.0

schedule = pd.read_csv("results/evaluation_schedule.csv")

block_ids = schedule.loc[
    schedule["evaluation_role"] == "evaluation",
    "block_id"
].astype(int)

records = []

for block_id in block_ids:

    source = pd.read_csv(
        f"data/processed/evaluation_block_{block_id}.csv"
    )

    wind = source["actual_h1_kw"].to_numpy()

    initial_export = max(
        0.0, float(source["current_power_kw"].iloc[0])
    )

    for controller in ["xgboost", "persistence"]:

        sim = pd.read_csv(
            f"results/{controller}_mpc_evaluation_block_{block_id}.csv"
        )

        grid = sim["grid_export_kw"].to_numpy()
        soc = sim["soc_percent"].to_numpy()

        previous_grid = np.r_[initial_export, grid[:-1]]
        previous_soc = np.r_[50.0, soc[:-1]]

        ramps = np.abs(grid - previous_grid)

        for i in np.where(ramps > RAMP_LIMIT_KW + 0.001)[0]:

            energy_before = (
                previous_soc[i] / 100.0 * CAPACITY_KWH
            )

            max_charge = min(
                MAX_POWER_KW,
                max(
                    0.0,
                    (MAX_ENERGY_KWH - energy_before)
                    / (ETA_CHARGE * DT_HOURS)
                )
            )

            max_discharge = min(
                MAX_POWER_KW,
                max(
                    0.0,
                    (energy_before - MIN_ENERGY_KWH)
                    * ETA_DISCHARGE / DT_HOURS
                )
            )

            max_discharge = min(
                max_discharge,
                max(0.0, wind[i] * 0 + MAX_POWER_KW)
            )

            minimum_export = max(
                0.0, wind[i] - max_charge
            )

            maximum_export = (
                wind[i] + max_discharge
            )

            # The battery cannot charge more than
            # the available wind generation.
            minimum_export = wind[i] - min(
                max_charge, wind[i]
            )

            allowed_low = max(
                0.0, previous_grid[i] - RAMP_LIMIT_KW
            )

            allowed_high = (
                previous_grid[i] + RAMP_LIMIT_KW
            )

            feasible = (
                minimum_export <= allowed_high + 0.001
                and maximum_export >= allowed_low - 0.001
            )

            records.append({
                "block_id": block_id,
                "controller": controller,
                "timestamp": sim["timestamp"].iloc[i],
                "ramp_kw": ramps[i],
                "physically_avoidable": feasible,
                "previous_soc_percent": previous_soc[i],
                "wind_kw": wind[i],
                "previous_grid_kw": previous_grid[i],
            })

results = pd.DataFrame(records)

print("=" * 75)
print("PHYSICAL FEASIBILITY OF RECORDED RAMP VIOLATIONS")
print("=" * 75)

for controller in ["xgboost", "persistence"]:

    part = results[
        results["controller"] == controller
    ]

    avoidable = int(
        part["physically_avoidable"].sum()
    )

    unavoidable = len(part) - avoidable

    print(f"\n{controller.upper()}")
    print("Total recorded violations:", len(part))
    print("Feasible alternative at that interval:", avoidable)
    print("No feasible alternative at that interval:", unavoidable)

results.to_csv(
    "results/ramp_violation_feasibility.csv",
    index=False
)

print("\nSaved: results/ramp_violation_feasibility.csv")
