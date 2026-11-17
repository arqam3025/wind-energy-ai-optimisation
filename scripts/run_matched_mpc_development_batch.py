from pathlib import Path
import argparse
import hashlib
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

CONTROLLERS = {
    "fixed": (
        "scripts/uncertainty_grid_priority_tolerance_development.py",
        "8f161b65d39592680cb4787d48ec0ce387d1bdb9ddea21bfb3e176f91012121a",
        "results/uncertainty_grid_priority_tolerance_development",
    ),
    "adaptive": (
        "scripts/causal_adaptive_grid_priority_mpc_development.py",
        "b969a5d4051d2ebb99feed76f0e13462330adf8a1de8027d302d14f6d3d8be67",
        "results/causal_adaptive_grid_priority_development",
    ),
}

MODULE_HASH = (
    "ee47a8cdb0e97f8be6dbee44a8729b44114c5db55d54375ee1c53dc4c9c9e0e4"
)

CONFIG = ["0.5", "0.1", "1000", "100", "100"]

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def result_path(kind, block):
    base = CONTROLLERS[kind][2]
    return (
        ROOT / base
        / "reserve_1000p000"
        / "penalty_0p100"
        / "reserve_penalty_100p000"
        / "primary_tolerance_100p000"
        / f"adaptive_charging_mpc_block_{block}_weight_0p500.csv"
    )

def validate(path, block):
    input_path = (
        ROOT
        / "data/processed/controller_development_blocks"
        / f"development_block_{block}.csv"
    )

    source = pd.read_csv(input_path, parse_dates=["timestamp"])
    result = pd.read_csv(path, parse_dates=["timestamp"])

    if len(source) != 144 or len(result) != 144:
        raise RuntimeError("Incorrect row count")

    expected_times = (
        source["timestamp"].reset_index(drop=True)
        + pd.Timedelta(minutes=10)
    )

    if not result["timestamp"].reset_index(drop=True).equals(
        expected_times
    ):
        raise RuntimeError("Dispatch timestamp mismatch")

    required = [
        "wind_generation_kw",
        "forecast_generation_kw",
        "grid_export_kw",
        "charge_kw",
        "discharge_kw",
        "curtailment_kw",
        "soc_percent",
    ]

    for column in required:
        if column not in result.columns:
            raise RuntimeError(f"Missing column: {column}")

    arrays = {
        column: result[column].to_numpy(float)
        for column in required
    }

    if not all(np.isfinite(a).all() for a in arrays.values()):
        raise RuntimeError("Non-finite physical output")

    wind = arrays["wind_generation_kw"]
    forecast = arrays["forecast_generation_kw"]
    grid = arrays["grid_export_kw"]
    charge = arrays["charge_kw"]
    discharge = arrays["discharge_kw"]
    curtail = arrays["curtailment_kw"]
    soc = arrays["soc_percent"]

    if not np.allclose(
        wind,
        source["actual_h1_kw"].to_numpy(float),
        rtol=0,
        atol=1e-6
    ):
        raise RuntimeError("Actual wind mismatch")

    if not np.allclose(
        forecast,
        np.maximum(
            source["xgboost_h1_kw"].to_numpy(float), 0
        ),
        rtol=0,
        atol=1e-6
    ):
        raise RuntimeError("Forecast mismatch")

    balance = np.abs(
        wind - charge - curtail + discharge - grid
    )

    if balance.max() > 0.01:
        raise RuntimeError("Power balance violation")

    if (soc < 39.99).any() or (soc > 90.01).any():
        raise RuntimeError("SOC violation")

    if (charge < -0.01).any() or (discharge < -0.01).any():
        raise RuntimeError("Negative battery power")

    if (charge + discharge > 1000.01).any():
        raise RuntimeError("Battery power violation")

    if (grid < -0.01).any():
        raise RuntimeError("Negative export")

    if (curtail < -0.01).any():
        raise RuntimeError("Negative curtailment")

    ramps = np.abs(np.diff(grid))

    return {
        "mean_ramp_kw": float(ramps.mean()),
        "max_ramp_kw": float(ramps.max()),
        "ramp_violations": int((ramps > 200.001).sum()),
        "total_exceedance_kw": float(
            np.maximum(ramps - 200, 0).sum()
        ),
        "battery_throughput_kwh": float(
            (charge + discharge).sum() / 6
        ),
        "minimum_soc_percent": float(soc.min()),
        "final_soc_percent": float(soc[-1]),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--blocks",
        nargs="+",
        type=int,
        required=True
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute missing experiments"
    )
    args = parser.parse_args()

    blocks = list(dict.fromkeys(args.blocks))

    if any(block < 1 or block > 18 for block in blocks):
        raise ValueError("Development block must be 1..18")

    for kind, (relative, expected, _) in CONTROLLERS.items():
        path = ROOT / relative
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(
                f"{kind} controller source integrity failed"
            )

    module = ROOT / "scripts/causal_adaptive_uncertainty.py"
    if not module.is_file() or sha256(module) != MODULE_HASH:
        raise RuntimeError("Adaptive uncertainty module changed")

    print("=" * 72, flush=True)
    print("MATCHED MPC DEVELOPMENT BATCH", flush=True)
    print("Blocks:", blocks, flush=True)
    print("Execution enabled:", args.execute, flush=True)
    print("Parameters:", CONFIG, flush=True)

    for block in blocks:
        input_path = (
            ROOT
            / "data/processed/controller_development_blocks"
            / f"development_block_{block}.csv"
        )

        if not input_path.is_file():
            raise FileNotFoundError(input_path)

        print(f"\nBLOCK {block}", flush=True)

        for kind in ["fixed", "adaptive"]:
            controller = ROOT / CONTROLLERS[kind][0]
            output = result_path(kind, block)

            if output.exists():
                metrics = validate(output, block)
                print(
                    f"  {kind}: EXISTING VERIFIED "
                    f"SHA256={sha256(output)}",
                    flush=True
                )
            elif not args.execute:
                print(
                    f"  {kind}: MISSING - DRY RUN",
                    flush=True
                )
                continue
            else:
                print(
                    f"  {kind}: RUNNING",
                    flush=True
                )

                command = [
                    sys.executable,
                    str(controller),
                    str(block),
                    *CONFIG,
                ]

                subprocess.run(
                    command,
                    cwd=ROOT,
                    check=True
                )

                if not output.is_file():
                    raise RuntimeError(
                        f"Missing generated result: {output}"
                    )

                metrics = validate(output, block)

                print(
                    f"  {kind}: CREATED AND VERIFIED "
                    f"SHA256={sha256(output)}",
                    flush=True
                )

            print(
                f"    mean ramp={metrics['mean_ramp_kw']:.3f} kW, "
                f"exceedance={metrics['total_exceedance_kw']:.3f} kW, "
                f"throughput={metrics['battery_throughput_kwh']:.3f} kWh",
                flush=True
            )

    print("\nBATCH COMPLETE", flush=True)

if __name__ == "__main__":
    main()
