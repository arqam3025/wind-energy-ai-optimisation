
from pathlib import Path
import numpy as np
import pandas as pd

CAPACITY_KWH = 2000.0
MIN_SOC = 0.10
INITIAL_SOC = 0.50
MAX_DISCHARGE_KW = 1000.0
ETA_DISCHARGE = 0.95
DT_HOURS = 10 / 60
RAMP_LIMIT_KW = 200.0
TOLERANCE = 0.001

MIN_ENERGY_KWH = CAPACITY_KWH * MIN_SOC
INITIAL_ENERGY_KWH = CAPACITY_KWH * INITIAL_SOC

records = []

for block_id in range(1, 51):
    result_path = Path(
        f"results/curtailment_aware_xgboost_mpc_block_{block_id}.csv"
    )
    input_path = Path(
        f"data/processed/evaluation_block_{block_id}.csv"
    )

    df = pd.read_csv(result_path, parse_dates=["timestamp"])
    original = pd.read_csv(input_path, nrows=1)

    initial_export = max(
        0.0, float(original.iloc[0]["current_power_kw"])
    )

    grid = df["grid_export_kw"].to_numpy(dtype=float)
    wind = df["wind_generation_kw"].to_numpy(dtype=float)
    discharge = df["discharge_kw"].to_numpy(dtype=float)

    previous_export = np.concatenate([
        [initial_export], grid[:-1]
    ])

    # SOC in the results is recorded AFTER dispatch.
    # Reconstruct energy available BEFORE each interval.
    energy_after = (
        df["soc_percent"].to_numpy(dtype=float)
        / 100.0 * CAPACITY_KWH
    )
    energy_before = np.concatenate([
        [INITIAL_ENERGY_KWH], energy_after[:-1]
    ])

    ramp = grid - previous_export

    for i in np.where(ramp < -RAMP_LIMIT_KW - TOLERANCE)[0]:
        required_export = max(
            0.0, previous_export[i] - RAMP_LIMIT_KW
        )

        required_discharge = max(
            0.0, required_export - wind[i]
        )

        available_energy = max(
            0.0, energy_before[i] - MIN_ENERGY_KWH
        )

        soc_limited_discharge = (
            available_energy * ETA_DISCHARGE / DT_HOURS
        )

        feasible_discharge = min(
            MAX_DISCHARGE_KW, soc_limited_discharge
        )

        power_deficit = max(
            0.0, required_discharge - MAX_DISCHARGE_KW
        )

        energy_deficit = max(
            0.0, required_discharge - feasible_discharge
        )

        if required_discharge > MAX_DISCHARGE_KW + TOLERANCE:
            category = "POWER_LIMITED"
        elif required_discharge > feasible_discharge + TOLERANCE:
            category = "ENERGY_LIMITED"
        else:
            category = "REQUIRES_INVESTIGATION"

        records.append({
            "block": block_id,
            "timestamp": df.iloc[i]["timestamp"],
            "category": category,
            "ramp_kw": ramp[i],
            "previous_export_kw": previous_export[i],
            "wind_kw": wind[i],
            "required_discharge_kw": required_discharge,
            "actual_discharge_kw": discharge[i],
            "feasible_discharge_kw": feasible_discharge,
            "soc_before_percent": (
                energy_before[i] / CAPACITY_KWH * 100
            ),
            "soc_after_percent": (
                energy_after[i] / CAPACITY_KWH * 100
            ),
            "power_deficit_kw": power_deficit,
            "dispatch_deficit_kw": energy_deficit,
        })

results = pd.DataFrame(records)

if results.empty:
    print("No downward ramp violations found.")
else:
    print("=" * 65)
    print("BATTERY DISCHARGE LIMITATION ANALYSIS")
    print("=" * 65)

    print("\nTotal violations:", len(results))

    print("\nClassification:")
    print(results["category"].value_counts().to_string())

    print("\nRequired discharge statistics:")
    print(
        results["required_discharge_kw"]
        .describe()
        .round(3)
        .to_string()
    )

    print("\nViolations requiring investigation:")
    subset = results[
        results["category"] == "REQUIRES_INVESTIGATION"
    ]
    print(
        subset.to_string(index=False)
        if not subset.empty else "None"
    )

    print("\nLargest 15 violations:")
    largest = results.loc[
        results["ramp_kw"].abs()
        .sort_values(ascending=False).index
    ].head(15)

    print(
        largest[
            [
                "block", "timestamp", "category",
                "ramp_kw", "required_discharge_kw",
                "feasible_discharge_kw",
                "soc_before_percent"
            ]
        ].round(3).to_string(index=False)
    )

    Path("results").mkdir(exist_ok=True)
    output = "results/discharge_limitation_analysis.csv"
    results.to_csv(output, index=False)

    print("\nSaved:", output)
