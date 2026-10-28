
import numpy as np
import pandas as pd

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

    current = source["current_power_kw"].to_numpy()
    actual = source["actual_h1_kw"].to_numpy()

    wind_changes = np.abs(actual - current)

    initial_export = max(0.0, float(current[0]))

    for controller in ["xgboost", "persistence"]:

        simulation = pd.read_csv(
            f"results/{controller}_mpc_evaluation_block_{block_id}.csv"
        )

        grid = simulation["grid_export_kw"].to_numpy()

        if len(grid) != len(wind_changes):
            raise ValueError(
                f"Length mismatch: block {block_id}, {controller}"
            )

        grid_ramps = np.abs(
            np.diff(np.r_[initial_export, grid])
        )

        forecast = source[
            f"{controller}_h1_kw"
        ].to_numpy()

        forecast_errors = np.abs(forecast - actual)

        for i in range(len(grid)):
            records.append({
                "block_id": block_id,
                "controller": controller,
                "violation": grid_ramps[i] > 200.001,
                "wind_change_kw": wind_changes[i],
                "forecast_error_kw": forecast_errors[i],
            })

results = pd.DataFrame(records)

summary = results.groupby(
    ["controller", "violation"]
).agg(
    intervals=("wind_change_kw", "size"),
    mean_wind_change_kw=("wind_change_kw", "mean"),
    median_wind_change_kw=("wind_change_kw", "median"),
    mean_forecast_error_kw=("forecast_error_kw", "mean"),
)

print("=" * 75)
print("ACTUAL WIND CHANGES AND GRID RAMP VIOLATIONS")
print("=" * 75)

print(summary.round(3).to_string())

results.to_csv(
    "results/wind_changes_and_violations.csv",
    index=False
)

print("\nSaved: results/wind_changes_and_violations.csv")
