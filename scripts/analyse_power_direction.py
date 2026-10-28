
import pandas as pd

df = pd.read_csv("results/required_battery_power.csv")

df["direction"] = "Neither"

df.loc[
    df["required_charge_kw"] > 0.001,
    "direction"
] = "Charging"

df.loc[
    df["required_discharge_kw"] > 0.001,
    "direction"
] = "Discharging"

summary = pd.crosstab(
    df["direction"],
    df["controller"]
)

print("=" * 70)
print("BATTERY POWER REQUIREMENTS BY DIRECTION")
print("=" * 70)
print(summary.to_string())

print("\nEvents requiring more than 1 MW:")

high_power = df[df["required_power_kw"] > 1000.001]

high_summary = pd.crosstab(
    high_power["direction"],
    high_power["controller"]
)

print(high_summary.to_string())

print("\nMaximum required power by direction:")
print(
    df.groupby(
        ["controller", "direction"]
    )["required_power_kw"]
    .max()
    .round(3)
    .to_string()
)

print("\nAnalysis completed.")
