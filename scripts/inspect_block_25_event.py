
import numpy as np
import pandas as pd

block_id = 25

source = pd.read_csv(
    f"data/processed/evaluation_block_{block_id}.csv",
    parse_dates=["timestamp"]
)

initial_export = max(
    0.0, float(source["current_power_kw"].iloc[0])
)

for controller in ["xgboost", "persistence"]:

    df = pd.read_csv(
        f"results/{controller}_mpc_evaluation_block_{block_id}.csv",
        parse_dates=["timestamp"]
    )

    grid = df["grid_export_kw"].to_numpy()

    ramps = np.diff(
        np.concatenate([[initial_export], grid])
    )

    worst_idx = int(np.argmax(np.abs(ramps)))

    print("\n" + "=" * 65)
    print(f"BLOCK 25 — {controller.upper()}")
    print("=" * 65)

    print("Worst interval index:", worst_idx)
    print("Timestamp:", df["timestamp"].iloc[worst_idx])
    print("Signed grid ramp:", round(ramps[worst_idx], 3), "kW")
    print("Absolute grid ramp:", round(abs(ramps[worst_idx]), 3), "kW")

    start = max(0, worst_idx - 2)
    end = min(len(df), worst_idx + 3)

    columns = [
        "timestamp",
        "grid_export_kw",
        "charge_kw",
        "discharge_kw",
        "soc_percent",
    ]

    print("\nBattery operation around the event:")
    print(df.iloc[start:end][columns].to_string(index=False))

    print("\nWind power around the event:")

    wind = source.iloc[start:end][
        ["timestamp", "current_power_kw", "actual_h1_kw"]
    ]

    print(wind.to_string(index=False))

print("\nInvestigation completed.")
