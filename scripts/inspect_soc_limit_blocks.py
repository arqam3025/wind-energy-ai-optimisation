
import pandas as pd

df = pd.read_csv("results/soc_saturation_by_block.csv")

df["total_soc_limit_intervals"] = (
    df["at_min_soc"] + df["at_max_soc"]
)

for controller in ["xgboost", "persistence"]:
    part = df[df["controller"] == controller].copy()

    affected = part[
        part["total_soc_limit_intervals"] > 0
    ].sort_values(
        "total_soc_limit_intervals",
        ascending=False
    )

    print("\n" + "=" * 70)
    print(controller.upper())
    print("=" * 70)

    print("Blocks reaching an SOC boundary:", len(affected))

    print("\nBlocks with most SOC-boundary intervals:")
    print(
        affected[
            [
                "block_id",
                "at_min_soc",
                "at_max_soc",
                "total_soc_limit_intervals",
            ]
        ].head(15).to_string(index=False)
    )

print("\nAnalysis completed.")
