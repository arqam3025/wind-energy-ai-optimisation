
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path("results")
CAUSAL_DIR = BASE / "causal_scenario_mpc_development"
FEEDBACK_DIR = BASE / "feedback_scenario_mpc_development"
OUTPUT_DIR = BASE / "feedback_mpc_comparison"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DT = 1.0 / 6.0
CAPACITY = 2000.0
RAMP_LIMIT = 200.0

records = []


def calculate_metrics(df, initial_export):
    export = df["grid_export_kw"].to_numpy(dtype=float)

    ramps = np.abs(
        np.diff(
            np.concatenate(([initial_export], export))
        )
    )

    throughput = (
        df["charge_kw"].sum()
        + df["discharge_kw"].sum()
    ) * DT

    return {
        "mean_ramp_kw": float(ramps.mean()),
        "maximum_ramp_kw": float(ramps.max()),
        "ramp_violations": int(
            (ramps > RAMP_LIMIT + 0.001).sum()
        ),
        "ramp_exceedance_sum_kw": float(
            np.maximum(ramps - RAMP_LIMIT, 0).sum()
        ),
        "throughput_kwh": float(throughput),
        "equivalent_full_cycles": float(
            throughput / (2 * CAPACITY)
        ),
        "curtailment_kwh": float(
            df["curtailment_kw"].sum() * DT
        ),
        "final_soc_percent": float(
            df["soc_percent"].iloc[-1]
        ),
    }


for block in range(1, 19):
    block_input = pd.read_csv(
        "data/processed/controller_development_blocks/"
        f"development_block_{block}.csv"
    )

    initial_export = max(
        0.0,
        float(block_input.iloc[0]["current_power_kw"])
    )

    configurations = [
        (
            "Option A",
            0.0,
            CAUSAL_DIR
            / f"causal_mpc_block_{block}_weight_0p000.csv",
        )
    ]

    for gain in (0.25, 0.5, 1.0):
        gain_label = f"{gain:.3f}".replace(".", "p")

        configurations.append(
            (
                "Option B",
                gain,
                FEEDBACK_DIR
                / (
                    f"feedback_mpc_block_{block}_"
                    f"weight_0p000_gain_{gain_label}.csv"
                ),
            )
        )

    for controller, gain, path in configurations:
        if not path.exists():
            raise FileNotFoundError(path)

        df = pd.read_csv(path)

        if len(df) != 144:
            raise ValueError(
                f"Unexpected number of rows in {path}"
            )

        metrics = calculate_metrics(df, initial_export)

        records.append({
            "block": block,
            "controller": controller,
            "feedback_gain": gain,
            **metrics,
        })


details = pd.DataFrame(records)

summary = (
    details.groupby(
        ["controller", "feedback_gain"],
        as_index=False
    )
    .agg(
        mean_ramp_kw=("mean_ramp_kw", "mean"),
        maximum_ramp_kw=("maximum_ramp_kw", "max"),
        total_ramp_violations=("ramp_violations", "sum"),
        total_ramp_exceedance_kw=(
            "ramp_exceedance_sum_kw", "sum"
        ),
        total_throughput_kwh=("throughput_kwh", "sum"),
        total_equivalent_full_cycles=(
            "equivalent_full_cycles", "sum"
        ),
        total_curtailment_kwh=("curtailment_kwh", "sum"),
        mean_final_soc_percent=("final_soc_percent", "mean"),
    )
)

detail_path = OUTPUT_DIR / "comparison_by_block.csv"
summary_path = OUTPUT_DIR / "comparison_summary.csv"

for path in (detail_path, summary_path):
    if path.exists():
        raise FileExistsError(
            f"Output already exists: {path}"
        )

details.to_csv(detail_path, index=False)
summary.to_csv(summary_path, index=False)

print("\nSTEP 79 — MPC COMPARISON")
print("=" * 80)

print(
    summary.round(3).to_string(index=False)
)

print("\nSaved:", detail_path)
print("Saved:", summary_path)
print("\nStep 79 completed successfully.")
