"""Exclusive, versioned forecast/uncertainty experiment; inference only."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "windresearch_mpl_v1"))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from windresearch.forecast_audit import run_forecast_audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/research_grade_v1/forecast_uncertainty")
    parser.add_argument("--figures", type=Path, default=ROOT / "figures/research_grade_v1/forecast_uncertainty")
    args = parser.parse_args()
    for path in [args.output, args.figures]:
        if not path.resolve().is_relative_to(ROOT):
            parser.error("Outputs must stay within this workspace")
    summary = run_forecast_audit(ROOT, args.output, args.figures)
    print(json.dumps({k: summary[k] for k in ["scored_origins", "scored_horizon_pairs",
        "strict_target_eligibility_all_pass", "adaptive_floor_binding_fraction", "protected_inputs_unchanged"]}, indent=2))
    print(f"Results: {args.output}")
    print(f"Figures: {args.figures}")


if __name__ == "__main__":
    main()
