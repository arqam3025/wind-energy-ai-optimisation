
from pathlib import Path
import numpy as np
import pandas as pd

SOURCE = Path("results/causal_scenario_mpc_development")
OUTPUT = Path("results/causal_mpc_audit")

CAPACITY = 2000.0
MAX_POWER = 1000.0
MIN_SOC = 10.0
MAX_SOC = 90.0
ETA_C = 0.95
ETA_D = 0.95
DT = 1.0 / 6.0
RAMP_LIMIT = 200.0

OUTPUT.mkdir(parents=True, exist_ok=True)

block_results = []

for block in range(1, 19):
    input_block = pd.read_csv(
        "data/processed/controller_development_blocks/"
        f"development_block_{block}.csv",
        parse_dates=["timestamp"]
    )

    if len(input_block) != 144:
        raise ValueError(f"Block {block}: unexpected input length")

    initial_export = float(
        input_block.iloc[0]["current_power_kw"]
    )

    for weight in (0.0, 0.5):
        label = f"{weight:.3f}".replace(".", "p")
        path = SOURCE / (
            f"causal_mpc_block_{block}_weight_{label}.csv"
        )

        df = pd.read_csv(path, parse_dates=["timestamp"])

        if len(df) != 144:
            raise ValueError(
                f"Block {block}, weight {weight}: "
                "unexpected number of rows"
            )

        numeric = df.select_dtypes(include="number")
        if not np.isfinite(numeric.to_numpy()).all():
            raise ValueError(f"Nonfinite values in {path}")

        expected_timestamps = (
            input_block["timestamp"]
            + pd.Timedelta(minutes=10)
        )

        if not df["timestamp"].reset_index(drop=True).equals(
            expected_timestamps.reset_index(drop=True)
        ):
            raise ValueError(f"Timestamp mismatch: {path}")

        wind = df["wind_generation_kw"].to_numpy()
        charge = df["charge_kw"].to_numpy()
        discharge = df["discharge_kw"].to_numpy()
        curtail = df["curtailment_kw"].to_numpy()
        export = df["grid_export_kw"].to_numpy()
        soc = df["soc_percent"].to_numpy()

        balance = wind - charge - curtail + discharge - export

        if np.max(np.abs(balance)) > 0.01:
            raise ValueError(f"Power balance failure: {path}")

        if (
            np.min(soc) < MIN_SOC - 0.01
            or np.max(soc) > MAX_SOC + 0.01
        ):
            raise ValueError(f"SOC failure: {path}")

        if (
            np.min(charge) < -0.01
            or np.min(discharge) < -0.01
            or np.max(charge + discharge) > MAX_POWER + 0.01
        ):
            raise ValueError(f"Battery power failure: {path}")

        if np.max(np.minimum(charge, discharge)) > 0.01:
            raise ValueError(f"Simultaneous battery operation: {path}")

        if np.min(curtail) < -0.01 or np.max(
            curtail - wind
        ) > 0.01:
            raise ValueError(f"Curtailment failure: {path}")

        # Verify SOC evolution, including the first interval.
        previous_energy = np.concatenate((
            [1000.0],
            soc[:-1] * CAPACITY / 100.0
        ))

        expected_energy = (
            previous_energy
            + ETA_C * charge * DT
            - discharge * DT / ETA_D
        )

        actual_energy = soc * CAPACITY / 100.0

        max_soc_error = float(
            np.max(np.abs(expected_energy - actual_energy))
        )

        if max_soc_error > 0.02:
            raise ValueError(f"SOC dynamics failure: {path}")

        # Internal ramps: excludes the initial block boundary.
        internal_ramps = np.abs(np.diff(export))

        # Includes the first ramp from initial measured wind.
        all_ramps = np.abs(
            np.diff(
                np.concatenate(([initial_export], export))
            )
        )

        throughput = float(np.sum(charge + discharge) * DT)
        curtailment = float(np.sum(curtail) * DT)

        block_results.append({
            "block": block,
            "risk_weight": weight,
            "mean_internal_ramp_kw": float(
                np.mean(internal_ramps)
            ),
            "maximum_internal_ramp_kw": float(
                np.max(internal_ramps)
            ),
            "internal_ramp_violations": int(
                np.sum(internal_ramps > RAMP_LIMIT + 0.001)
            ),
            "total_ramp_violations_including_boundary": int(
                np.sum(all_ramps > RAMP_LIMIT + 0.001)
            ),
            "ramp_exceedance_sum_kw": float(
                np.maximum(
                    internal_ramps - RAMP_LIMIT, 0.0
                ).sum()
            ),
            "battery_throughput_kwh": throughput,
            "equivalent_full_cycles": (
                throughput / (2.0 * CAPACITY)
            ),
            "curtailment_kwh": curtailment,
            "final_soc_percent": float(soc[-1]),
            "max_soc_energy_error_kwh": max_soc_error,
        })

block_df = pd.DataFrame(block_results)

summary = (
    block_df.groupby("risk_weight", as_index=False)
    .agg(
        mean_internal_ramp_kw=(
            "mean_internal_ramp_kw", "mean"
        ),
        maximum_internal_ramp_kw=(
            "maximum_internal_ramp_kw", "max"
        ),
        internal_ramp_violations=(
            "internal_ramp_violations", "sum"
        ),
        ramp_exceedance_sum_kw=(
            "ramp_exceedance_sum_kw", "sum"
        ),
        total_throughput_kwh=(
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
        max_soc_energy_error_kwh=(
            "max_soc_energy_error_kwh", "max"
        ),
    )
)

nominal = (
    block_df[block_df["risk_weight"] == 0.0]
    .set_index("block")
)

risk = (
    block_df[block_df["risk_weight"] == 0.5]
    .set_index("block")
)

paired = pd.DataFrame({
    "block": nominal.index,
    "ramp_reduction_kw": (
        nominal["mean_internal_ramp_kw"]
        - risk["mean_internal_ramp_kw"]
    ).to_numpy(),
    "violation_reduction": (
        nominal["internal_ramp_violations"]
        - risk["internal_ramp_violations"]
    ).to_numpy(),
    "throughput_change_kwh": (
        risk["battery_throughput_kwh"]
        - nominal["battery_throughput_kwh"]
    ).to_numpy(),
    "curtailment_change_kwh": (
        risk["curtailment_kwh"]
        - nominal["curtailment_kwh"]
    ).to_numpy(),
    "final_soc_difference_pp": (
        risk["final_soc_percent"]
        - nominal["final_soc_percent"]
    ).to_numpy(),
})

print("=" * 70)
print("STEP 70 - CAUSAL MPC ENGINEERING AUDIT")
print("=" * 70)

print("\nCONTROLLER SUMMARY")
print(summary.round(3).to_string(index=False))

print("\nPAIRED COMPARISON")
print(paired.round(3).to_string(index=False))

print(
    "\nBlocks with lower mean ramp at risk 0.5:",
    int((paired["ramp_reduction_kw"] > 0).sum())
)

print(
    "Blocks with fewer ramp violations at risk 0.5:",
    int((paired["violation_reduction"] > 0).sum())
)

print(
    "Blocks with higher throughput at risk 0.5:",
    int((paired["throughput_change_kwh"] > 0).sum())
)

# Exclusive creation: never overwrite existing audit files.
for name, data in (
    ("block_results.csv", block_df),
    ("controller_summary.csv", summary),
    ("paired_comparison.csv", paired),
):
    path = OUTPUT / name
    with path.open("x", encoding="utf-8", newline="") as f:
        data.to_csv(f, index=False)

print("\nSaved audit files to:", OUTPUT)
print("Step 70 complete.")
