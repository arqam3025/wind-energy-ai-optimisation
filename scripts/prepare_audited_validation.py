
from pathlib import Path

import numpy as np
import pandas as pd

source_path = Path(
    "data/processed/wind_multistep_features.csv"
)
forecast_path = Path(
    "results/multistep_mpc_validation_forecasts.csv"
)
output_path = Path(
    "results/multistep_mpc_validation_audited.csv"
)

if output_path.exists():
    raise FileExistsError(
        f"Output already exists: {output_path}"
    )

source = pd.read_csv(
    source_path,
    parse_dates=["timestamp"]
)

forecasts = pd.read_csv(
    forecast_path,
    parse_dates=["timestamp"]
)

if source["timestamp"].duplicated().any():
    raise ValueError("Duplicate source timestamps")

if forecasts["timestamp"].duplicated().any():
    raise ValueError("Duplicate forecast timestamps")

source = source.sort_values("timestamp")
forecasts = forecasts.sort_values(
    "timestamp"
).reset_index(drop=True)

power_lookup = source.set_index("timestamp")["power_kw"]

valid = np.ones(len(forecasts), dtype=bool)

for h in range(1, 7):
    future_times = (
        forecasts["timestamp"]
        + pd.Timedelta(minutes=10 * h)
    )

    expected = power_lookup.reindex(
        pd.DatetimeIndex(future_times)
    ).to_numpy()

    actual_column = f"actual_h{h}_kw"

    if actual_column not in forecasts:
        raise ValueError(
            f"Missing forecast column: {actual_column}"
        )

    stored_actual = forecasts[
        actual_column
    ].to_numpy()

    horizon_valid = (
        np.isfinite(expected)
        & np.isfinite(stored_actual)
        & np.isclose(
            stored_actual,
            np.maximum(expected, 0.0),
            rtol=1e-7,
            atol=1e-5,
        )
    )

    valid &= horizon_valid

audited = forecasts.loc[valid].copy()

print("=" * 60)
print("STEP 56: AUDITED VALIDATION DATA")
print("=" * 60)

print("Original rows:", len(forecasts))
print("Audited rows:", len(audited))
print("Excluded rows:", int((~valid).sum()))

if audited.empty:
    raise ValueError("No valid rows remain")

if len(audited) != 7474:
    raise ValueError(
        "Unexpected audited row count. "
        "Investigate before continuing."
    )

output_path.parent.mkdir(
    parents=True,
    exist_ok=True
)

with output_path.open(
    "x",
    encoding="utf-8",
    newline=""
) as file:
    audited.to_csv(file, index=False)

print("Saved:", output_path)
print("Step 56 completed.")
