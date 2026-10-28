
import pandas as pd

events = pd.read_csv(
    "results/ramp_saturation_events.csv"
)

selected = events[
    (events["controller"] == "persistence")
    & (~events["charging_at_limit"])
    & (~events["discharging_at_limit"])
].copy()

selected["absolute_ramp_kw"] = (
    selected["signed_ramp_kw"].abs()
)

selected = selected.sort_values(
    "absolute_ramp_kw",
    ascending=False
)

print("=" * 75)
print("PERSISTENCE: VIOLATIONS WITHOUT BATTERY POWER SATURATION")
print("=" * 75)

print("Total events:", len(selected))

print("\nTop 15 events:")
print(
    selected[
        [
            "block_id",
            "timestamp",
            "signed_ramp_kw",
            "charge_kw",
            "discharge_kw",
            "soc_percent",
        ]
    ].head(15).to_string(index=False)
)

print("\nSOC analysis:")
print(
    "Events at or near 10% SOC:",
    int((selected["soc_percent"] <= 10.1).sum())
)

print(
    "Events at or near 90% SOC:",
    int((selected["soc_percent"] >= 89.9).sum())
)

print(
    "Events between 10.1% and 89.9% SOC:",
    int(
        (
            (selected["soc_percent"] > 10.1)
            & (selected["soc_percent"] < 89.9)
        ).sum()
    )
)
