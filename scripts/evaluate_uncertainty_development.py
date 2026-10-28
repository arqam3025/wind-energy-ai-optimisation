
from pathlib import Path

import numpy as np
import pandas as pd

development_path = Path(
    "results/multistep_controller_development_split.csv"
)

calibration_path = Path(
    "results/multistep_uncertainty_calibration_split.csv"
)

output_path = Path(
    "results/multistep_uncertainty_development_evaluation.csv"
)

if output_path.exists():
    raise FileExistsError(
        f"Output already exists: {output_path}"
    )

development = pd.read_csv(
    development_path,
    parse_dates=["timestamp"]
)

calibration = pd.read_csv(calibration_path)

if development.empty:
    raise ValueError("Development dataset is empty")

if development["timestamp"].duplicated().any():
    raise ValueError("Duplicate timestamps detected")

if development["timestamp"].isna().any():
    raise ValueError("Missing timestamps detected")

if calibration["horizon_minutes"].duplicated().any():
    raise ValueError("Duplicate calibration horizons")

if not set(range(10, 61, 10)).issubset(
    set(calibration["horizon_minutes"])
):
    raise ValueError("Missing calibration horizons")

print("=" * 65)
print("STEP 59: DEVELOPMENT UNCERTAINTY EVALUATION")
print("=" * 65)
print("Development observations:", len(development))
print("Nominal interval coverage: 90%")

results = []

for h in range(1, 7):
    horizon_minutes = h * 10

    q = float(
        calibration.loc[
            calibration["horizon_minutes"] == horizon_minutes,
            "calibration_quantile_kw"
        ].iloc[0]
    )

    prediction = development[
        f"xgboost_h{h}_kw"
    ].to_numpy(dtype=float)

    actual = development[
        f"actual_h{h}_kw"
    ].to_numpy(dtype=float)

    if not (
        np.isfinite(prediction).all()
        and np.isfinite(actual).all()
        and np.isfinite(q)
        and q >= 0
    ):
        raise ValueError(
            f"Invalid data at horizon {horizon_minutes}"
        )

    lower = np.maximum(prediction - q, 0.0)
    upper = prediction + q

    covered = (actual >= lower) & (actual <= upper)

    coverage = float(np.mean(covered))
    average_width = float(np.mean(upper - lower))
    mae = float(np.mean(np.abs(actual - prediction)))

    results.append({
        "horizon_minutes": horizon_minutes,
        "observations": len(development),
        "nominal_coverage": 0.90,
        "empirical_coverage": coverage,
        "average_interval_width_kw": average_width,
        "xgboost_mae_kw": mae,
        "calibration_quantile_kw": q,
    })

    print(
        f"{horizon_minutes:2d} min | "
        f"Coverage: {coverage:.2%} | "
        f"Width: {average_width:.2f} kW | "
        f"MAE: {mae:.2f} kW"
    )

results_df = pd.DataFrame(results)

output_path.parent.mkdir(parents=True, exist_ok=True)

with output_path.open(
    "x", newline="", encoding="utf-8"
) as file:
    results_df.to_csv(file, index=False)

print("\nSaved:", output_path)
print("Step 59 completed.")
