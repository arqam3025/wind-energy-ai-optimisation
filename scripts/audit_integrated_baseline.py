
from pathlib import Path
import numpy as np
import pandas as pd

SOURCE = Path("results/risk_aware_recourse_development")
OUTPUT = Path("results/integrated_baseline_audit")

DT_H = 1.0 / 6.0
CAPACITY_KWH = 2000.0
CHARGE_EFF = 0.95
DISCHARGE_EFF = 0.95
RAMP_LIMIT_KW = 200.0

REQUIRED = [
    "timestamp",
    "wind_generation_kw",
    "forecast_generation_kw",
    "downside_forecast_kw",
    "planned_export_kw",
    "charge_kw",
    "discharge_kw",
    "curtailment_kw",
    "grid_export_kw",
    "soc_percent",
    "reserve_energy_kwh",
]

records = []

for block in range(1, 19):
    for weight, suffix in [(0.0, "0p000"), (0.5, "0p500")]:
        filename = (
            f"recourse_mpc_block_{block}_weight_{suffix}.csv"
        )
        path = SOURCE / filename

        df = pd.read_csv(path)

        missing = set(REQUIRED) - set(df.columns)
        if missing:
            raise ValueError(f"{filename}: missing {missing}")

        if len(df) != 144:
            raise ValueError(f"{filename}: expected 144 rows")

        df["timestamp"] = pd.to_datetime(df["timestamp"])

        if not df["timestamp"].diff().dropna().eq(
            pd.Timedelta(minutes=10)
        ).all():
            raise ValueError(f"{filename}: timestamp gaps")

        values = df[REQUIRED[1:]].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"{filename}: nonfinite values")

        charge = df["charge_kw"].to_numpy(dtype=float)
        discharge = df["discharge_kw"].to_numpy(dtype=float)
        soc = df["soc_percent"].to_numpy(dtype=float)
        grid = df["grid_export_kw"].to_numpy(dtype=float)

        power_balance = (
            df["wind_generation_kw"]
            - df["charge_kw"]
            + df["discharge_kw"]
            - df["curtailment_kw"]
            - df["grid_export_kw"]
        )

        if power_balance.abs().max() > 0.01:
            raise ValueError(f"{filename}: power balance error")

        if (
            (charge < -0.01).any()
            or (discharge < -0.01).any()
            or (charge > 1000.01).any()
            or (discharge > 1000.01).any()
            or (soc < 9.99).any()
            or (soc > 90.01).any()
        ):
            raise ValueError(f"{filename}: battery limits")

        # Check SOC changes from row to row.
        expected_delta = (
            CHARGE_EFF * charge[1:]
            - discharge[1:] / DISCHARGE_EFF
        ) * DT_H / CAPACITY_KWH * 100.0

        observed_delta = np.diff(soc)

        # This check assumes SOC at each row is post-dispatch.
        soc_error = np.max(
            np.abs(observed_delta - expected_delta)
        )

        # Ramps within the block only; first boundary excluded
        # because previous-block export is not stored here.
        ramps = np.abs(np.diff(grid))

        throughput = (
            charge.sum() + discharge.sum()
        ) * DT_H

        records.append({
            "block": block,
            "risk_weight": weight,
            "mean_internal_ramp_kw": ramps.mean(),
            "max_internal_ramp_kw": ramps.max(),
            "internal_ramp_violations": int(
                (ramps > RAMP_LIMIT_KW + 0.001).sum()
            ),
            "battery_throughput_kwh": throughput,
            "equivalent_full_cycles": (
                throughput / (2.0 * CAPACITY_KWH)
            ),
            "curtailed_energy_kwh": (
                df["curtailment_kw"].sum() * DT_H
            ),
            "minimum_soc_percent": soc.min(),
            "maximum_soc_percent": soc.max(),
            "final_soc_percent": soc[-1],
            "soc_step_error_max_pp": soc_error,
            "power_balance_error_max_kw": (
                power_balance.abs().max()
            ),
        })

results = pd.DataFrame(records)

summary = results.groupby(
    "risk_weight", as_index=False
).agg(
    mean_internal_ramp_kw=(
        "mean_internal_ramp_kw", "mean"
    ),
    maximum_internal_ramp_kw=(
        "max_internal_ramp_kw", "max"
    ),
    internal_ramp_violations=(
        "internal_ramp_violations", "sum"
    ),
    total_throughput_kwh=(
        "battery_throughput_kwh", "sum"
    ),
    total_equivalent_full_cycles=(
        "equivalent_full_cycles", "sum"
    ),
    total_curtailment_kwh=(
        "curtailed_energy_kwh", "sum"
    ),
    mean_final_soc_percent=(
        "final_soc_percent", "mean"
    ),
    max_soc_step_error_pp=(
        "soc_step_error_max_pp", "max"
    ),
)

baseline = results[
    results["risk_weight"] == 0.0
].set_index("block")

risk = results[
    results["risk_weight"] == 0.5
].set_index("block")

comparison = pd.DataFrame({
    "block": baseline.index,
    "ramp_reduction_kw": (
        baseline["mean_internal_ramp_kw"]
        - risk["mean_internal_ramp_kw"]
    ).to_numpy(),
    "throughput_change_kwh": (
        risk["battery_throughput_kwh"]
        - baseline["battery_throughput_kwh"]
    ).to_numpy(),
    "curtailment_change_kwh": (
        risk["curtailed_energy_kwh"]
        - baseline["curtailed_energy_kwh"]
    ).to_numpy(),
    "final_soc_difference_pp": (
        risk["final_soc_percent"]
        - baseline["final_soc_percent"]
    ).to_numpy(),
})

OUTPUT.mkdir(parents=True, exist_ok=True)

for name, frame in [
    ("block_results.csv", results),
    ("controller_summary.csv", summary),
    ("paired_comparison.csv", comparison),
]:
    path = OUTPUT / name
    with path.open("x", newline="", encoding="utf-8") as f:
        frame.to_csv(f, index=False)

print("\n" + "=" * 70)
print("STEP 64 - INTEGRATED ENGINEERING BASELINE AUDIT")
print("=" * 70)

print("\nCONTROLLER SUMMARY")
print(summary.round(3).to_string(index=False))

print("\nPAIRED COMPARISON")
print(comparison.round(3).to_string(index=False))

print("\nBlocks with lower mean ramp at weight 0.5:",
      int((comparison["ramp_reduction_kw"] > 0).sum()))

print("Blocks with higher battery throughput at weight 0.5:",
      int((comparison["throughput_change_kwh"] > 0).sum()))

print("\nSaved results to:", OUTPUT)
print("Step 64 complete.")
