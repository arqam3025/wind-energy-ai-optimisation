
from pathlib import Path

import numpy as np
import pandas as pd


# STEP 86 - RISK-WEIGHT MPC AUDIT

BLOCK_DIR = Path(
    "data/processed/controller_development_blocks"
)

RESULT_DIR = Path(
    "results/causal_scenario_mpc_development"
)

OUTPUT_DIR = Path(
    "results/risk_weight_mpc_audit"
)

DT = 1.0 / 6.0
BATTERY_CAPACITY_KWH = 2000.0
RAMP_LIMIT_KW = 200.0
RESERVE_SOC_PERCENT = 40.0

WEIGHTS = [0.0, 0.5]
BLOCKS = range(1, 19)

records = []


def calculate_metrics(df, initial_export):

    required = [
        "grid_export_kw",
        "charge_kw",
        "discharge_kw",
        "curtailment_kw",
        "soc_percent",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns: {missing}"
        )

    if len(df) != 144:
        raise ValueError(
            f"Expected 144 intervals, found {len(df)}"
        )

    for column in required:
        if not np.isfinite(
            df[column].to_numpy(dtype=float)
        ).all():
            raise ValueError(
                f"Nonfinite values in {column}"
            )

    export = df["grid_export_kw"].to_numpy(
        dtype=float
    )

    # Include transition from initial export
    # to the first controlled interval.
    ramps = np.abs(
        np.diff(
            np.concatenate(
                ([initial_export], export)
            )
        )
    )

    charge = df["charge_kw"].to_numpy(
        dtype=float
    )

    discharge = df["discharge_kw"].to_numpy(
        dtype=float
    )

    curtailment = df["curtailment_kw"].to_numpy(
        dtype=float
    )

    soc = df["soc_percent"].to_numpy(
        dtype=float
    )

    throughput = float(
        np.sum(charge + discharge) * DT
    )

    exceedance = np.maximum(
        ramps - RAMP_LIMIT_KW,
        0.0
    )

    return {
        "mean_ramp_kw": float(
            np.mean(ramps)
        ),
        "maximum_ramp_kw": float(
            np.max(ramps)
        ),
        "ramp_violations": int(
            np.sum(ramps > RAMP_LIMIT_KW + 0.001)
        ),
        "ramp_exceedance_sum_kw": float(
            np.sum(exceedance)
        ),
        "battery_throughput_kwh": throughput,
        "equivalent_full_cycles": (
            throughput / (2 * BATTERY_CAPACITY_KWH)
        ),
        "curtailment_kwh": float(
            np.sum(curtailment) * DT
        ),
        "final_soc_percent": float(
            soc[-1]
        ),
        "minimum_soc_percent": float(
            np.min(soc)
        ),
        "intervals_below_reserve": int(
            np.sum(soc < RESERVE_SOC_PERCENT - 0.001)
        ),
        "hours_below_reserve": float(
            np.sum(soc < RESERVE_SOC_PERCENT - 0.001)
            * DT
        ),
    }


for block in BLOCKS:

    input_path = (
        BLOCK_DIR
        / f"development_block_{block}.csv"
    )

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    input_df = pd.read_csv(input_path)

    initial_export = max(
        0.0,
        float(
            input_df.iloc[0]["current_power_kw"]
        )
    )

    for weight in WEIGHTS:

        weight_label = (
            f"{weight:.3f}".replace(".", "p")
        )

        path = (
            RESULT_DIR
            / (
                f"causal_mpc_block_{block}_"
                f"weight_{weight_label}.csv"
            )
        )

        if not path.exists():
            raise FileNotFoundError(path)

        df = pd.read_csv(path)

        metrics = calculate_metrics(
            df,
            initial_export
        )

        records.append({
            "block": block,
            "risk_weight": weight,
            **metrics,
        })


details = pd.DataFrame(records)

summary = (
    details.groupby(
        "risk_weight",
        as_index=False
    )
    .agg(
        mean_ramp_kw=(
            "mean_ramp_kw", "mean"
        ),
        maximum_ramp_kw=(
            "maximum_ramp_kw", "max"
        ),
        total_ramp_violations=(
            "ramp_violations", "sum"
        ),
        total_ramp_exceedance_kw=(
            "ramp_exceedance_sum_kw", "sum"
        ),
        total_battery_throughput_kwh=(
            "battery_throughput_kwh", "sum"
        ),
        total_equivalent_full_cycles=(
            "equivalent_full_cycles", "sum"
        ),
        total_curtailment_kwh=(
            "curtailment_kwh", "sum"
        ),
        mean_final_soc_percent=(
            "final_soc_percent", "mean"
        ),
        minimum_soc_percent=(
            "minimum_soc_percent", "min"
        ),
        total_hours_below_reserve=(
            "hours_below_reserve", "sum"
        ),
    )
)

baseline = (
    details[details["risk_weight"] == 0.0]
    .set_index("block")
)

risk_aware = (
    details[details["risk_weight"] == 0.5]
    .set_index("block")
)

metrics_to_compare = [
    "mean_ramp_kw",
    "maximum_ramp_kw",
    "ramp_violations",
    "ramp_exceedance_sum_kw",
    "battery_throughput_kwh",
    "final_soc_percent",
    "hours_below_reserve",
]

comparison = pd.DataFrame({
    "block": list(BLOCKS)
})

for metric in metrics_to_compare:

    comparison[
        f"baseline_{metric}"
    ] = baseline.loc[
        list(BLOCKS), metric
    ].to_numpy()

    comparison[
        f"risk_aware_{metric}"
    ] = risk_aware.loc[
        list(BLOCKS), metric
    ].to_numpy()

    comparison[
        f"delta_{metric}"
    ] = (
        comparison[f"risk_aware_{metric}"]
        - comparison[f"baseline_{metric}"]
    )


print("\nSTEP 86 - RISK-WEIGHT MPC AUDIT")
print("=" * 90)

print("\nAGGREGATE RESULTS")
print(
    summary.round(3).to_string(index=False)
)

print("\nBLOCK-LEVEL COMPARISON")
print(
    comparison[
        [
            "block",
            "delta_mean_ramp_kw",
            "delta_ramp_violations",
            "delta_battery_throughput_kwh",
            "delta_final_soc_percent",
            "delta_hours_below_reserve",
        ]
    ].round(3).to_string(index=False)
)

print("\nBLOCK WIN COUNTS (RISK WEIGHT 0.5)")

for metric in [
    "mean_ramp_kw",
    "ramp_violations",
    "ramp_exceedance_sum_kw",
    "battery_throughput_kwh",
    "hours_below_reserve",
]:

    delta = comparison[
        f"delta_{metric}"
    ]

    print(
        f"{metric}: "
        f"improved={(delta < -0.001).sum()}, "
        f"worsened={(delta > 0.001).sum()}, "
        f"tied={(delta.abs() <= 0.001).sum()}"
    )


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

paths = {
    "details": (
        OUTPUT_DIR / "risk_weight_by_block.csv"
    ),
    "summary": (
        OUTPUT_DIR / "risk_weight_summary.csv"
    ),
    "comparison": (
        OUTPUT_DIR / "risk_weight_block_differences.csv"
    ),
}

existing = [
    str(path)
    for path in paths.values()
    if path.exists()
]

if existing:
    raise FileExistsError(
        "Refusing to overwrite existing files: "
        + ", ".join(existing)
    )

details.to_csv(
    paths["details"],
    index=False
)

summary.to_csv(
    paths["summary"],
    index=False
)

comparison.to_csv(
    paths["comparison"],
    index=False
)

for name, path in paths.items():
    print(f"\nSaved {name}: {path}")

print("\nStep 86 completed successfully.")
