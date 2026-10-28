
import pandas as pd

block_id = 34

for controller in ["xgboost", "persistence"]:

    df = pd.read_csv(
        f"results/{controller}_mpc_evaluation_block_{block_id}.csv"
    )

    indices = df.index[
        df["soc_percent"] <= 10.1
    ].tolist()

    print("\n" + "=" * 70)
    print(f"BLOCK 34 — {controller.upper()}")
    print("=" * 70)

    print("Intervals near minimum SOC:", len(indices))

    for idx in indices:
        print(f"\nSOC boundary at row {idx}")

        start = max(0, idx - 2)
        end = min(len(df), idx + 2)

        print(
            df.iloc[start:end][
                [
                    "timestamp",
                    "grid_export_kw",
                    "charge_kw",
                    "discharge_kw",
                    "soc_percent",
                ]
            ].to_string(index=False)
        )

print("\nInvestigation completed.")
