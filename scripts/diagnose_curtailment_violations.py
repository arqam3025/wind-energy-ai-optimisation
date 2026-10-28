import numpy as np
import pandas as pd

records = []

for block_id in range(1, 51):
    path = (
        f"results/curtailment_aware_xgboost_mpc_block_{block_id}.csv"
    )
    df = pd.read_csv(path, parse_dates=["timestamp"])

    initial = pd.read_csv(
        f"data/processed/evaluation_block_{block_id}.csv",
        nrows=1,
    )["current_power_kw"].iloc[0]

    previous = np.concatenate([
        [max(0.0, float(initial))],
        df["grid_export_kw"].to_numpy()[:-1],
    ])

    grid = df["grid_export_kw"].to_numpy()
    ramps = grid - previous

    for i in np.where(np.abs(ramps) > 200.001)[0]:
        records.append({
            "block": block_id,
            "timestamp": df.iloc[i]["timestamp"],
            "direction": "UP" if ramps[i] > 0 else "DOWN",
            "ramp_kw": ramps[i],
            "wind_kw": df.iloc[i]["wind_generation_kw"],
            "grid_export_kw": grid[i],
            "previous_export_kw": previous[i],
            "charge_kw": df.iloc[i]["charge_kw"],
            "discharge_kw": df.iloc[i]["discharge_kw"],
            "soc_percent": df.iloc[i]["soc_percent"],
        })

results = pd.DataFrame(records)

print("\nTotal violations:", len(results))
print("\nViolations by direction:")
print(results["direction"].value_counts())

print("\nLargest violations:")
print(
    results.reindex(
        results["ramp_kw"].abs().sort_values(
            ascending=False
        ).index
    ).head(15).to_string(index=False)
)

results.to_csv(
    "results/curtailment_violation_diagnostics.csv",
    index=False,
)