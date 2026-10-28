
from pathlib import Path

import numpy as np
import pandas as pd


INPUT_DIR = Path(
    "data/processed/controller_development_blocks"
)

OUTPUT_DIR = Path(
    "results/feedback_forecast_evaluation"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GAINS = [0.0, 0.25, 0.5, 1.0]

records = []
all_errors = []


for block in range(1, 19):

    path = INPUT_DIR / f"development_block_{block}.csv"

    df = pd.read_csv(path)

    actual = df["actual_h1_kw"].to_numpy(dtype=float)

    raw = df["xgboost_h1_kw"].to_numpy(dtype=float)

    if not np.isfinite(actual).all() or not np.isfinite(raw).all():
        raise ValueError(f"Nonfinite values in block {block}")

    original_errors = actual - raw

    # Previous error is available only after the
    # previous interval has finished.
    previous_errors = np.concatenate(
        ([0.0], original_errors[:-1])
    )

    # Correlation pairs stay within each block.
    all_errors.append(original_errors)

    for gain in GAINS:

        corrected = np.maximum(
            0.0,
            raw + gain * previous_errors
        )

        errors = actual - corrected

        records.append({
            "block": block,
            "gain": gain,
            "mae_kw": float(np.mean(np.abs(errors))),
            "rmse_kw": float(
                np.sqrt(np.mean(errors ** 2))
            ),
            "bias_kw": float(np.mean(errors)),
        })


results = pd.DataFrame(records)

summary = (
    results.groupby("gain", as_index=False)
    .agg(
        mean_mae_kw=("mae_kw", "mean"),
        mean_rmse_kw=("rmse_kw", "mean"),
        mean_bias_kw=("bias_kw", "mean"),
    )
)

lagged = np.concatenate(
    [errors[:-1] for errors in all_errors]
)

current = np.concatenate(
    [errors[1:] for errors in all_errors]
)

correlation = np.corrcoef(lagged, current)[0, 1]

print("\nSTEP 82 - FEEDBACK FORECAST EVALUATION")
print("=" * 65)

print(summary.round(3).to_string(index=False))

print(
    "\nWithin-block lag-1 error correlation:",
    round(float(correlation), 4)
)

detail_path = OUTPUT_DIR / "feedback_accuracy_by_block.csv"
summary_path = OUTPUT_DIR / "feedback_accuracy_summary.csv"

for path in (detail_path, summary_path):
    if path.exists():
        raise FileExistsError(
            f"Output already exists: {path}"
        )

results.to_csv(detail_path, index=False)
summary.to_csv(summary_path, index=False)

print("\nSaved:", detail_path)
print("Saved:", summary_path)
print("\nStep 82 completed successfully.")
