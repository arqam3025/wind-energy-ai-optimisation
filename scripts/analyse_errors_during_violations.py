
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

    initial_export = max(
        0.0, float(source["current_power_kw"].iloc[0])
    )

    actual = source["actual_h1_kw"].to_numpy()

    for controller in ["xgboost", "persistence"]:

        simulation = pd.read_csv(
            f"results/{controller}_mpc_evaluation_block_{block_id}.csv"
        )

        grid = simulation["grid_export_kw"].to_numpy()

        if len(grid) != len(actual):
            raise ValueError(
                f"Length mismatch: block {block_id}, {controller}"
            )

        ramps = np.abs(
            np.diff(np.r_[initial_export, grid])
        )

        forecast = source[
            f"{controller}_h1_kw"
        ].to_numpy()

        errors = np.abs(forecast - actual)

        for i in range(len(grid)):
            records.append({
                "block_id": block_id,
                "controller": controller,
                "violation": ramps[i] > 200.001,
                "absolute_forecast_error_kw": errors[i],
            })

results = pd.DataFrame(records)

summary = results.groupby(
    ["controller", "violation"]
).agg(
    intervals=("absolute_forecast_error_kw", "size"),
    mean_absolute_error_kw=(
        "absolute_forecast_error_kw", "mean"
    ),
    median_absolute_error_kw=(
        "absolute_forecast_error_kw", "median"
    ),
)

print("=" * 75)
print("ONE-STEP FORECAST ERRORS AND RAMP VIOLATIONS")
print("=" * 75)
print(summary.round(3).to_string())

results.to_csv(
    "results/forecast_errors_and_violations.csv",
    index=False
)

print("\nSaved: results/forecast_errors_and_violations.csv")
