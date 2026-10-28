
import numpy as np
import pandas as pd

SOURCE = "data/processed/wind_multistep_features.csv"
FORECASTS = "results/multistep_mpc_validation_forecasts.csv"

start = pd.Timestamp("2018-09-09 02:50:00")
end = pd.Timestamp("2018-11-05 15:10:00")

df = pd.read_csv(SOURCE, parse_dates=["timestamp"])
forecasts = pd.read_csv(
    FORECASTS, parse_dates=["timestamp"]
)

if df["timestamp"].duplicated().any():
    raise ValueError("Duplicate source timestamps")

if forecasts["timestamp"].duplicated().any():
    raise ValueError("Duplicate forecast timestamps")

validation = df.loc[
    (df["timestamp"] >= start)
    & (df["timestamp"] < end)
].copy()

validation = validation.sort_values(
    "timestamp"
).reset_index(drop=True)

print("=" * 65)
print("STEP 55: VALIDATION TARGET ALIGNMENT AUDIT")
print("=" * 65)

print("Source rows:", len(df))
print("Validation rows:", len(validation))
print("Forecast rows:", len(forecasts))

if not validation["timestamp"].equals(
    forecasts["timestamp"]
):
    raise ValueError(
        "Forecast timestamps do not match validation rows"
    )

# Compare each target against actual power at its
# exact intended future timestamp.
power_lookup = df.set_index("timestamp")["power_kw"]

for h in range(1, 7):
    horizon_minutes = h * 10

    future_timestamps = (
        validation["timestamp"]
        + pd.Timedelta(minutes=horizon_minutes)
    )

    expected = power_lookup.reindex(
        pd.DatetimeIndex(future_timestamps)
    ).to_numpy()

    stored = validation[
        f"target_h{h}_kw"
    ].to_numpy()

    available = np.isfinite(expected)

    matches = np.zeros(len(validation), dtype=bool)

    matches[available] = np.isclose(
        stored[available],
        expected[available],
        rtol=1e-7,
        atol=1e-5,
    )

    missing_future = int((~available).sum())
    mismatches = int(
        (available & ~matches).sum()
    )

    print(f"\nHorizon: {horizon_minutes} minutes")
    print("Missing future timestamps:", missing_future)
    print("Target mismatches:", mismatches)
    print("Verified matches:", int(matches.sum()))

    if mismatches:
        bad_indices = np.where(
            available & ~matches
        )[0][:5]

        for idx in bad_indices:
            print(
                "Mismatch:",
                validation.loc[idx, "timestamp"],
                "stored=", stored[idx],
                "expected=", expected[idx],
            )

print("\nChecking six-horizon completeness...")

# A row is usable for a six-step MPC horizon only
# when all six future 10-minute timestamps exist.
complete = np.ones(len(validation), dtype=bool)

for h in range(1, 7):
    future = (
        validation["timestamp"]
        + pd.Timedelta(minutes=10 * h)
    )

    complete &= pd.Index(future).isin(
        power_lookup.index
    )

print("Rows with all six future timestamps:", int(complete.sum()))
print("Rows missing at least one future timestamp:",
      int((~complete).sum()))

print("\nAudit completed. No files were modified.")
