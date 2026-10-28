
import numpy as np
import pandas as pd

schedule = pd.read_csv("results/evaluation_schedule.csv")
blocks = schedule.loc[
    schedule["evaluation_role"] == "evaluation",
    "block_id"
].astype(int)

records = []

for block_id in blocks:
    source = pd.read_csv(
        f"data/processed/evaluation_block_{block_id}.csv"
    )

    initial_export = max(
        0.0, float(source["current_power_kw"].iloc[0])
    )

    for controller in ["xgboost", "persistence"]:
        df = pd.read_csv(
            f"results/{controller}_mpc_evaluation_block_{block_id}.csv"
        )

        grid = df["grid_export_kw"].to_numpy()
        ramps = np.diff(
            np.r_[initial_export, grid]
        )

        for i in np.where(np.abs(ramps) > 200.001)[0]:
            charge = float(df["charge_kw"].iloc[i])
            discharge = float(df["discharge_kw"].iloc[i])

            records.append({
                "block_id": block_id,
                "controller": controller,
                "timestamp": df["timestamp"].iloc[i],
                "signed_ramp_kw": ramps[i],
                "charge_kw": charge,
                "discharge_kw": discharge,
                "charging_at_limit": charge >= 999.9,
                "discharging_at_limit": discharge >= 999.9,
                "soc_percent": df["soc_percent"].iloc[i],
            })

events = pd.DataFrame(records)

print("=" * 70)
print("RAMP VIOLATION AND BATTERY SATURATION ANALYSIS")
print("=" * 70)

for controller in ["xgboost", "persistence"]:
    part = events[events["controller"] == controller]

    print(f"\n{controller.upper()}")
    print("Total violations:", len(part))
    print(
        "Charging at 1000 kW:",
        int(part["charging_at_limit"].sum())
    )
    print(
        "Discharging at 1000 kW:",
        int(part["discharging_at_limit"].sum())
    )
    print(
        "Neither power limit reached:",
        int((
            ~part["charging_at_limit"]
            & ~part["discharging_at_limit"]
        ).sum())
    )

events.to_csv(
    "results/ramp_saturation_events.csv",
    index=False
)

print("\nSaved: results/ramp_saturation_events.csv")
