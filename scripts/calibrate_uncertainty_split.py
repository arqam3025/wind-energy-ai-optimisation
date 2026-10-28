
from pathlib import Path
import numpy as np
import pandas as pd

input_path = Path("results/multistep_calibration_split.csv")
output_path = Path("results/multistep_uncertainty_calibration_split.csv")

if output_path.exists():
    raise FileExistsError(f"Output already exists: {output_path}")

df = pd.read_csv(input_path, parse_dates=["timestamp"])

if df.empty:
    raise ValueError("Calibration dataset is empty")

if df["timestamp"].duplicated().any():
    raise ValueError("Duplicate timestamps detected")

alpha = 0.10
n = len(df)

# Split-conformal finite-sample rank
rank = int(np.ceil((n + 1) * (1 - alpha)))

if rank > n:
    raise ValueError("Insufficient calibration observations")

rows = []

print("=" * 65)
print("STEP 58: CALIBRATE SIX-HORIZON FORECAST UNCERTAINTY")
print("=" * 65)
print("Calibration observations:", n)
print("Target nominal coverage: 90%")
print("Conformal rank:", rank)

for h in range(1, 7):
    prediction = df[f"xgboost_h{h}_kw"].to_numpy()
    actual = df[f"actual_h{h}_kw"].to_numpy()

    if not (
        np.isfinite(prediction).all()
        and np.isfinite(actual).all()
    ):
        raise ValueError(f"Non-finite values at horizon {h}")

    errors = np.abs(actual - prediction)

    quantile = float(np.sort(errors)[rank - 1])

    lower = np.maximum(prediction - quantile, 0.0)
    upper = prediction + quantile

    empirical_coverage = float(
        np.mean((actual >= lower) & (actual <= upper))
    )

    rows.append({
        "horizon_minutes": h * 10,
        "calibration_samples": n,
        "alpha": alpha,
        "calibration_quantile_kw": quantile,
        "calibration_coverage": empirical_coverage,
    })

    print(
        f"{h * 10:2d} min | "
        f"q={quantile:.3f} kW | "
        f"calibration coverage={empirical_coverage:.2%}"
    )

results = pd.DataFrame(rows)

output_path.parent.mkdir(parents=True, exist_ok=True)

with output_path.open(
    "x", newline="", encoding="utf-8"
) as file:
    results.to_csv(file, index=False)

print("\nSaved:", output_path)
print("Step 58 completed.")
