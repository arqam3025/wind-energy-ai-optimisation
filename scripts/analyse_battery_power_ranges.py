
import pandas as pd

df = pd.read_csv("results/required_battery_power.csv")

bins = [0, 500, 1000, 1500, 2000, 3000, float("inf")]

labels = [
    "0–500 kW",
    "500–1000 kW",
    "1000–1500 kW",
    "1500–2000 kW",
    "2000–3000 kW",
    "Above 3000 kW",
]

df["power_range"] = pd.cut(
    df["required_power_kw"],
    bins=bins,
    labels=labels,
    include_lowest=True,
)

summary = pd.crosstab(
    df["power_range"],
    df["controller"]
).reindex(labels, fill_value=0)

print("=" * 70)
print("REQUIRED BATTERY POWER DISTRIBUTION")
print("=" * 70)
print(summary.to_string())

print("\nPercentage distribution:")
print(
    (
        summary.div(summary.sum(axis=0), axis=1) * 100
    ).round(2).to_string()
)

summary.to_csv(
    "results/required_battery_power_distribution.csv"
)

print("\nSaved: results/required_battery_power_distribution.csv")
