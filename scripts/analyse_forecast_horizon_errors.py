
import numpy as np
import pandas as pd

schedule = pd.read_csv("results/evaluation_schedule.csv")

block_ids = schedule.loc[
    schedule["evaluation_role"] == "evaluation",
    "block_id"
].astype(int)

frames = [
    pd.read_csv(
        f"data/processed/evaluation_block_{block_id}.csv"
    )
    for block_id in block_ids
]

data = pd.concat(frames, ignore_index=True)

results = []

for horizon in range(1, 7):
    actual = data[f"actual_h{horizon}_kw"].to_numpy()

    for method in ["xgboost", "persistence"]:
        predicted = data[
            f"{method}_h{horizon}_kw"
        ].to_numpy()

        errors = predicted - actual

        results.append({
            "horizon_minutes": horizon * 10,
            "method": method,
            "mae_kw": np.mean(np.abs(errors)),
            "rmse_kw": np.sqrt(np.mean(errors ** 2)),
            "mean_signed_error_kw": np.mean(errors),
        })

summary = pd.DataFrame(results)

print("=" * 75)
print("FORECAST ACCURACY BY HORIZON")
print("=" * 75)

print(
    summary.round(3).to_string(index=False)
)

summary.to_csv(
    "results/forecast_horizon_error_summary.csv",
    index=False
)

print("\nSaved: results/forecast_horizon_error_summary.csv")
