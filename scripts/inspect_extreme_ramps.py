
import pandas as pd

df = pd.read_csv(
    "results/all_evaluation_metrics.csv"
)

print("=" * 75)
print("TOP 10 BLOCKS BY MAXIMUM RAMP")
print("=" * 75)

worst = df.sort_values(
    "max_ramp_kw",
    ascending=False
).head(10)

print(
    worst[
        [
            "block_id",
            "controller",
            "max_ramp_kw",
            "ramp_violations",
            "min_soc_percent",
            "max_soc_percent",
            "final_soc_percent"
        ]
    ].to_string(index=False)
)

print("\n" + "=" * 75)
print("BLOCKS WITH RAMP VIOLATIONS")
print("=" * 75)

violations = df[
    df["ramp_violations"] > 0
].sort_values(
    ["block_id", "controller"]
)

print(
    violations[
        [
            "block_id",
            "controller",
            "max_ramp_kw",
            "ramp_violations"
        ]
    ].to_string(index=False)
)

print("\nTotal controller-block records:", len(df))
print("Records with violations:", len(violations))
