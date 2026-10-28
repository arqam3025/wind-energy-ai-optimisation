
import pandas as pd

schedule = pd.read_csv("results/evaluation_schedule.csv")

block_ids = schedule.loc[
    schedule["evaluation_role"] == "evaluation",
    "block_id"
].astype(int)

records = []

for block_id in block_ids:
    for controller in ["xgboost", "persistence"]:
        df = pd.read_csv(
            f"results/{controller}_mpc_evaluation_block_{block_id}.csv"
        )

        soc = df["soc_percent"]

        records.append({
            "block_id": block_id,
            "controller": controller,
            "intervals": len(df),
            "at_min_soc": int((soc <= 10.1).sum()),
            "at_max_soc": int((soc >= 89.9).sum()),
            "within_limits": int(
                ((soc > 10.1) & (soc < 89.9)).sum()
            ),
            "mean_soc": soc.mean(),
        })

results = pd.DataFrame(records)

summary = results.groupby("controller").agg(
    total_intervals=("intervals", "sum"),
    min_soc_intervals=("at_min_soc", "sum"),
    max_soc_intervals=("at_max_soc", "sum"),
    mean_soc=("mean_soc", "mean"),
)

summary["soc_limit_intervals"] = (
    summary["min_soc_intervals"]
    + summary["max_soc_intervals"]
)

summary["soc_limit_percent"] = (
    100 * summary["soc_limit_intervals"]
    / summary["total_intervals"]
)

print("=" * 75)
print("SOC SATURATION ANALYSIS — 49 EVALUATION BLOCKS")
print("=" * 75)
print(summary.round(3).to_string())

results.to_csv(
    "results/soc_saturation_by_block.csv",
    index=False
)

print("\nSaved: results/soc_saturation_by_block.csv")
