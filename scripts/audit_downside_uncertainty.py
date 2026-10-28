
from pathlib import Path

import numpy as np
import pandas as pd


BLOCK_DIR = Path(
    "data/processed/controller_development_blocks"
)

CALIBRATION_PATH = Path(
    "results/multistep_uncertainty_calibration_split.csv"
)

OUTPUT_DIR = Path(
    "results/downside_uncertainty_audit"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

calibration = pd.read_csv(CALIBRATION_PATH)

required_columns = {
    "horizon_minutes",
    "calibration_quantile_kw",
}

if not required_columns.issubset(calibration.columns):
    raise ValueError(
        "Calibration file is missing required columns."
    )

quantiles = dict(
    zip(
        calibration["horizon_minutes"],
        calibration["calibration_quantile_kw"],
    )
)

blocks = [
    pd.read_csv(
        BLOCK_DIR / f"development_block_{i}.csv"
    )
    for i in range(1, 19)
]

data = pd.concat(blocks, ignore_index=True)

records = []

for horizon in range(1, 7):

    minutes = horizon * 10

    forecast = data[
        f"xgboost_h{horizon}_kw"
    ].to_numpy(dtype=float)

    actual = data[
        f"actual_h{horizon}_kw"
    ].to_numpy(dtype=float)

    q = float(quantiles[minutes])

    downside_bound = np.maximum(
        0.0,
        forecast - q
    )

    covered = actual >= downside_bound

    records.append({
        "horizon_minutes": minutes,
        "quantile_kw": q,
        "observations": len(actual),
        "empirical_downside_coverage": float(
            covered.mean()
        ),
        "downside_breaches": int(
            (~covered).sum()
        ),
        "mean_downside_shortfall_kw": float(
            np.maximum(
                downside_bound - actual,
                0.0
            ).mean()
        ),
    })

results = pd.DataFrame(records)

print("\nSTEP 84 - DOWNSIDE UNCERTAINTY AUDIT")
print("=" * 75)

print(
    results.round(4).to_string(index=False)
)

output_path = (
    OUTPUT_DIR / "downside_coverage_by_horizon.csv"
)

if output_path.exists():
    raise FileExistsError(
        f"Output already exists: {output_path}"
    )

results.to_csv(output_path, index=False)

print("\nSaved:", output_path)
print("\nStep 84 completed successfully.")
