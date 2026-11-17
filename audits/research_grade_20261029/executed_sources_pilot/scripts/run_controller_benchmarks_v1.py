"""Run predeclared versioned studies without changing the frozen research study.

Example: .venv/Scripts/python scripts/run_controller_benchmarks_v1.py --mode pilot
 --output results/research_grade_v1_20261029/pilot --retrospective
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cvxpy
import highspy
import numpy as np
import pandas as pd

from windresearch.experiments import block_path, run_job, sha256, study_jobs
from windresearch.mpc import MPCConfig
from windresearch.protocol import (require_cohort_interpretation, require_new_output_directory,
                                   role_target_overlap)
from prepare_frozen_heldout import verify as verify_frozen_artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("pilot", "benchmark", "sensitivity", "ablations"), required=True)
    parser.add_argument("--output", type=Path, required=True, help="New exclusive directory; existing directories are rejected")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/mpc_research_v1.json")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--blocks", type=int, nargs="+", help="Explicit subset for a smoke test; never silently called the complete cohort")
    parser.add_argument("--intervals", type=int, help="Explicit truncated episode smoke test; pilot/benchmark normally use all144")
    parser.add_argument("--retrospective", action="store_true", help="Acknowledge historical cohort exposure/target overlap")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    specification = json.loads(args.config.read_text(encoding="utf-8"))
    if args.workers < 1 or args.workers > 3:
        raise ValueError("Use one to three independent processes; each solver has one thread")
    if args.intervals is not None and not 1 <= args.intervals <= 144:
        raise ValueError("--intervals must be from one to144")
    frozen_manifest = ROOT / "results/development_controller_freeze_manifest.json"
    if sha256(frozen_manifest) != "b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a":
        raise ValueError("Frozen manifest SHA256 does not match the required reference")
    verify_frozen_artifacts()
    schedule = pd.read_csv(ROOT / "results/evaluation_schedule.csv")
    period = "evaluation" if args.mode == "benchmark" else "development"
    default_blocks = schedule.loc[schedule.evaluation_role.eq("evaluation"), "block_id"].astype(int).tolist() if period == "evaluation" else (
        specification["pilot_blocks"] if args.mode == "pilot" else specification["development_study_blocks"])
    blocks = args.blocks or default_blocks
    if len(set(blocks)) != len(blocks) or not set(blocks).issubset(default_blocks):
        raise ValueError("Blocks must be a unique subset of the predeclared eligible blocks")
    if 1 in blocks and period == "development":
        raise ValueError("Development block1 starts before all frozen calibration targets are observable")
    overlap = pd.DataFrame()
    if period == "evaluation":
        all_frames = {int(b): pd.read_csv(block_path("evaluation", int(b)), parse_dates=["timestamp"])
                      for b in schedule.block_id}
        overlap = role_target_overlap(schedule, all_frames)
        require_cohort_interpretation(overlap, retrospective=args.retrospective)
    intervals = args.intervals or (specification["sensitivity_intervals"] if args.mode in ("sensitivity", "ablations") else 144)
    base = MPCConfig(**specification["base_controller"])
    variants = study_jobs(args.mode, base)
    output = require_new_output_directory(args.output.resolve())
    start = perf_counter()
    uncertainty_paths = [ROOT / "results/multistep_calibration_split.csv",
                         ROOT / "results/multistep_uncertainty_calibration_split.csv",
                         ROOT / "results/evaluation_schedule.csv"]
    uncertainty_paths += [block_path("development", b) for b in range(1, 19)]
    if period == "evaluation":
        uncertainty_paths += [block_path("evaluation", int(b)) for b in schedule.block_id]
    metadata = {"schema_version": 1, "mode": args.mode, "period": period, "blocks": blocks,
        "intervals_per_block": intervals, "episode_hours": intervals / 6,
        "full_predeclared_cohort": blocks == default_blocks and intervals == 144,
        "interpretation": "versioned exploratory retrospective comparison; not a fresh untouched holdout",
        "retrospective_acknowledged": args.retrospective, "workers": args.workers,
        "created_utc": datetime.now(timezone.utc).isoformat(), "specification": specification,
        "variants": variants, "config_sha256": sha256(args.config),
        "frozen_manifest_sha256": sha256(frozen_manifest),
        "python": platform.python_version(), "cvxpy": cvxpy.__version__,
        "highs": highspy.Highs().version(), "numpy": np.__version__, "pandas": pd.__version__,
        "solver_profile_warning": "Cached DPP and declared deterministic HiGHS options may select different tied optima from frozen scripts. Original results remain authoritative.",
        "oracle_warning": "Perfect forecasts are nondeployable; finite horizon/mixed operational objectives do not guarantee superiority for every reported metric.",
        "input_source_sha256": {str(block_path(period, b).relative_to(ROOT)): sha256(block_path(period, b)) for b in blocks},
        "uncertainty_history_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in uncertainty_paths},
        "implementation_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in
            [Path(__file__), ROOT / "src/windresearch/mpc.py", ROOT / "src/windresearch/experiments.py", ROOT / "src/windresearch/forecast_audit.py", ROOT / "src/windresearch/protocol.py"]}}
    (output / "protocol.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    if not overlap.empty:
        overlap.to_csv(output / "historical_development_target_overlap.csv", index=False)
    payloads = [{**variant, "period": period, "block_id": b, "intervals": intervals, "output": str(output)}
                for variant in variants for b in blocks]
    metrics, failures = [], []
    def record(payload: dict, result: dict | None = None, error: Exception | None = None) -> None:
        if error is not None:
            failure = {"variant": payload["variant"], "controller": payload["controller"], "block_id": payload["block_id"],
                       "error_type": type(error).__name__, "error": str(error)}
            failures.append(failure)
            print(json.dumps({"FAILED": failure}), flush=True)
        else:
            metrics.append(result)
            print(json.dumps({"completed": len(metrics), "total_jobs": len(payloads), "controller": payload["controller"],
                "variant": payload["variant"], "block": payload["block_id"], "seconds": round(result["block_wall_seconds"], 2),
                "throughput_kwh": round(result["throughput_kwh"], 3), "exceedance_kw": round(result["total_ramp_exceedance_kw"], 3)}), flush=True)
    if args.workers == 1:
        for payload in payloads:
            try:
                record(payload, run_job(payload))
            except Exception as error:
                record(payload, error=error)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_job, payload): payload for payload in payloads}
            for future in as_completed(futures):
                payload = futures[future]
                try:
                    record(payload, future.result())
                except Exception as error:
                    record(payload, error=error)
    table = pd.DataFrame(metrics)
    if not table.empty:
        table.sort_values(["variant", "controller", "block_id"]).to_csv(output / "block_metrics.csv", index=False)
        measures = ["ramp_violations", "total_ramp_exceedance_kw", "throughput_kwh", "charge_energy_kwh", "discharge_energy_kwh",
            "conversion_losses_kwh", "curtailment_kwh", "actual_export_kwh", "hypothetical_terminal_adjusted_export_kwh",
            "reference_200kw_violations", "reference_200kw_exceedance_kw", "soc_violations", "solver_failures", "decision_seconds"]
        aggregate = table.groupby(["variant", "controller"], as_index=False)[measures].sum()
        counts = table.groupby(["variant", "controller"]).size().rename("completed_blocks").reset_index()
        aggregate = aggregate.merge(counts, on=["variant", "controller"])
        descriptive = table.assign(weighted_ramp=table.mean_grid_ramp_kw * table.intervals).groupby(["variant", "controller"]).agg(
            weighted_ramp=("weighted_ramp", "sum"), intervals=("intervals", "sum"), max_grid_ramp_kw=("max_grid_ramp_kw", "max"),
            max_solver_constraint_residual=("max_solver_constraint_residual", "max"),
            max_abs_energy_conservation_residual_kwh=("energy_conservation_residual_kwh", lambda values: values.abs().max())).reset_index()
        descriptive["mean_grid_ramp_kw"] = descriptive.weighted_ramp / descriptive.intervals
        aggregate = aggregate.merge(descriptive.drop(columns=["weighted_ramp"]), on=["variant", "controller"])
        aggregate["expected_blocks"] = len(blocks)
        aggregate["complete"] = aggregate.completed_blocks.eq(len(blocks))
        aggregate.to_csv(output / "aggregate_metrics.csv", index=False)
    pd.DataFrame(failures, columns=["variant", "controller", "block_id", "error_type", "error"]).to_csv(output / "failures.csv", index=False)
    summary = {"completed_jobs": len(metrics), "expected_jobs": len(payloads), "failed_jobs": len(failures),
        "wall_seconds": perf_counter() - start, "complete": len(metrics) == len(payloads) and not failures,
        "max_physical_energy_residual_kwh": float(table.energy_conservation_residual_kwh.abs().max()) if len(table) else None}
    if args.mode == "pilot" and len(table):
        controlled = table.loc[table.controller.ne("uncontrolled"), "block_wall_seconds"]
        summary["estimated_full49_sequential_seconds"] = float(controlled.mean() * 49 * 5)
        summary["estimated_full49_three_worker_seconds_lower_bound"] = float(controlled.mean() * 49 * 5 / 3)
        summary["timing_warning"] = "Pilot is one development episode. Runtime depends on MILP difficulty; division by workers is optimistic."
    (output / "completion.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
