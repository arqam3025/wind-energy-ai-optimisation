
from pathlib import Path
import numpy as np
import pandas as pd

schedule = pd.read_csv("results/evaluation_schedule.csv")

evaluation = schedule[
    schedule["evaluation_role"] == "evaluation"
]

records = []
dt = 10 / 60

for block_id in evaluation["block_id"].astype(int):

    source = pd.read_csv(
        f"data/processed/evaluation_block_{block_id}.csv",
        parse_dates=["timestamp"]
    )

    initial_export = max(
        0.0, float(source["current_power_kw"].iloc[0])
    )

    for controller in ["xgboost", "persistence"]:

        path = Path(
            f"results/{controller}_mpc_evaluation_block_{block_id}.csv"
        )

        df = pd.read_csv(path, parse_dates=["timestamp"])

        expected_times = (
            source["timestamp"] + pd.Timedelta(minutes=10)
        )

        if len(df) != 144 or not np.array_equal(
            df["timestamp"].to_numpy(),
            expected_times.to_numpy()
        ):
            raise ValueError(
                f"Timestamp mismatch: {controller}, block {block_id}"
            )

        grid = df["grid_export_kw"].to_numpy()

        ramps = np.abs(np.diff(
            np.concatenate([[initial_export], grid])
        ))

        charge = df["charge_kw"].sum() * dt
        discharge = df["discharge_kw"].sum() * dt

        records.append({
            "block_id": block_id,
            "controller": controller,
            "mean_ramp_kw": ramps.mean(),
            "max_ramp_kw": ramps.max(),
            "ramp_violations": int((ramps > 200.001).sum()),
            "battery_throughput_kwh": charge + discharge,
            "final_soc_percent": df["soc_percent"].iloc[-1],
            "min_soc_percent": df["soc_percent"].min(),
            "max_soc_percent": df["soc_percent"].max(),
        })

results = pd.DataFrame(records)

results.to_csv(
    "results/all_evaluation_metrics.csv",
    index=False
)

summary = results.groupby("controller").agg(
    mean_ramp_kw=("mean_ramp_kw", "mean"),
    max_ramp_kw=("max_ramp_kw", "max"),
    total_violations=("ramp_violations", "sum"),
    mean_throughput_kwh=("battery_throughput_kwh", "mean"),
    mean_final_soc_percent=("final_soc_percent", "mean"),
)

print("=" * 75)
print("COMPLETE EVALUATION SUMMARY")
print("=" * 75)
print(summary.round(3).to_string())

paired = results.pivot(
    index="block_id",
    columns="controller",
    values="mean_ramp_kw"
)

difference = paired["persistence"] - paired["xgboost"]

print("\nPAIRED COMPARISON")
print("XGBoost better blocks:", int((difference > 0.001).sum()))
print("Persistence better blocks:", int((difference < -0.001).sum()))
print("Approximately tied blocks:", int((difference.abs() <= 0.001).sum()))
print("Mean ramp advantage of XGBoost:",
      f"{difference.mean():.3f} kW")

print("\nSaved: results/all_evaluation_metrics.csv")
