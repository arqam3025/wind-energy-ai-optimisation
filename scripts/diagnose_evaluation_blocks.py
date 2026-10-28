
import numpy as np
import pandas as pd

schedule = pd.read_csv(
    "results/evaluation_schedule.csv",
    parse_dates=["start_timestamp", "end_timestamp"]
)

forecasts = pd.read_csv(
    "results/multistep_mpc_test_forecasts.csv",
    parse_dates=["timestamp"]
)

failed_blocks = [23, 24, 28, 37, 50]

for block_id in failed_blocks:

    info = schedule.loc[
        schedule["block_id"] == block_id
    ].iloc[0]

    block = forecasts[
        forecasts["timestamp"].between(
            info["start_timestamp"],
            info["end_timestamp"]
        )
    ].sort_values("timestamp").reset_index(drop=True)

    required = ["timestamp", "current_power_kw"]

    for h in range(1, 7):
        required.extend([
            f"persistence_h{h}_kw",
            f"xgboost_h{h}_kw",
            f"actual_h{h}_kw"
        ])

    checks = {
        "144 rows": len(block) == 144,
        "No missing values": not block[required].isna().any().any(),
        "Correct start": (
            len(block) > 0
            and block["timestamp"].iloc[0]
            == info["start_timestamp"]
        ),
        "Correct end": (
            len(block) > 0
            and block["timestamp"].iloc[-1]
            == info["end_timestamp"]
        ),
        "Continuous timestamps": (
            block["timestamp"].diff().iloc[1:]
            == pd.Timedelta(minutes=10)
        ).all(),
        "Persistence alignment": np.allclose(
            block["persistence_h1_kw"],
            block["current_power_kw"],
            atol=0.001
        ),
        "Actual alignment": np.allclose(
            block["actual_h1_kw"].iloc[:-1],
            block["current_power_kw"].iloc[1:],
            atol=0.001
        ),
    }

    print("\n" + "=" * 65)
    print(f"BLOCK {block_id}")
    print("=" * 65)

    print("Rows:", len(block))
    print("Start:", info["start_timestamp"])
    print("End:", info["end_timestamp"])

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    if len(block) > 1:
        differences = (
            block["actual_h1_kw"].iloc[:-1].to_numpy()
            - block["current_power_kw"].iloc[1:].to_numpy()
        )

        print(
            "Maximum actual alignment error:",
            f"{np.max(np.abs(differences)):.6f} kW"
        )

    print("Missing values:", int(block[required].isna().sum().sum()))

print("\nDiagnosis completed.")
