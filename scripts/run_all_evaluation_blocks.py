
import argparse
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument(
    "--block",
    type=int,
    default=None,
    help="Run one block for testing"
)
args = parser.parse_args()

schedule = pd.read_csv(
    "results/evaluation_schedule.csv"
)

evaluation = schedule[
    schedule["evaluation_role"] == "evaluation"
]

block_ids = sorted(
    evaluation["block_id"].astype(int).tolist()
)

if args.block is not None:
    if args.block not in block_ids:
        raise ValueError(
            f"Block {args.block} is not an evaluation block."
        )
    block_ids = [args.block]

controllers = {
    "xgboost": "scripts/xgboost_mpc_evaluation.py",
    "persistence": "scripts/persistence_mpc_evaluation.py",
}

log_dir = Path("results/evaluation_logs")
log_dir.mkdir(parents=True, exist_ok=True)

records = []

for block_id in block_ids:
    for controller, script in controllers.items():

        print(
            f"\nRunning Block {block_id} - {controller}",
            flush=True
        )

        start = time.perf_counter()

        result = subprocess.run(
            [sys.executable, script, str(block_id)],
            capture_output=True,
            text=True
        )

        elapsed = time.perf_counter() - start

        log_path = (
            log_dir / f"block_{block_id}_{controller}.txt"
        )

        log_path.write_text(
            result.stdout + "\n" + result.stderr,
            encoding="utf-8"
        )

        expected_output = Path(
            f"results/{controller}_mpc_evaluation_block_{block_id}.csv"
        )

        validation_passed = (
            result.returncode == 0
            and "Overall validation: PASS" in result.stdout
            and expected_output.exists()
        )

        status = "PASS" if validation_passed else "FAIL"

        print(
            f"{status} | {elapsed:.1f} seconds | {log_path}",
            flush=True
        )

        records.append({
            "block_id": block_id,
            "controller": controller,
            "status": status,
            "runtime_seconds": round(elapsed, 2),
            "log_file": str(log_path),
        })

        if not validation_passed:
            print("Stopping after failed validation.")
            pd.DataFrame(records).to_csv(
                "results/evaluation_run_status.csv",
                index=False
            )
            sys.exit(1)

        pd.DataFrame(records).to_csv(
            "results/evaluation_run_status.csv",
            index=False
        )

print("\nAll requested experiments completed.")
