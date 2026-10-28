
import numpy as np
import pandas as pd

events = pd.read_csv(
    "results/ramp_violation_feasibility.csv"
)

RAMP_LIMIT_KW = 200.0

records = []

for _, row in events.iterrows():

    wind = float(row["wind_kw"])
    previous_grid = float(row["previous_grid_kw"])

    allowed_low = max(
        0.0, previous_grid - RAMP_LIMIT_KW
    )

    allowed_high = previous_grid + RAMP_LIMIT_KW

    if wind > allowed_high:
        required_charge_kw = wind - allowed_high
        required_discharge_kw = 0.0

    elif wind < allowed_low:
        required_charge_kw = 0.0
        required_discharge_kw = allowed_low - wind

    else:
        required_charge_kw = 0.0
        required_discharge_kw = 0.0

    records.append({
        "controller": row["controller"],
        "block_id": row["block_id"],
        "timestamp": row["timestamp"],
        "required_charge_kw": required_charge_kw,
        "required_discharge_kw": required_discharge_kw,
        "required_power_kw": max(
            required_charge_kw,
            required_discharge_kw
        ),
        "exceeds_1000_kw": (
            max(
                required_charge_kw,
                required_discharge_kw
            ) > 1000.001
        ),
    })

results = pd.DataFrame(records)

print("=" * 75)
print("BATTERY POWER REQUIREMENT AT RAMP VIOLATIONS")
print("=" * 75)

for controller in ["xgboost", "persistence"]:

    part = results[
        results["controller"] == controller
    ]

    print(f"\n{controller.upper()}")
    print("Total violations:", len(part))

    print(
        "Require more than 1000 kW:",
        int(part["exceeds_1000_kw"].sum())
    )

    print(
        "Require 1000 kW or less:",
        int((~part["exceeds_1000_kw"]).sum())
    )

    print(
        "Maximum required battery power:",
        round(part["required_power_kw"].max(), 3),
        "kW"
    )

    print(
        "Median required battery power:",
        round(part["required_power_kw"].median(), 3),
        "kW"
    )

results.to_csv(
    "results/required_battery_power.csv",
    index=False
)

print("\nSaved: results/required_battery_power.csv")
