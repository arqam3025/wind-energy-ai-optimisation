
import pandas as pd
import numpy as np

# Load original wind turbine measurements.
df = pd.read_csv("data/raw/T1.csv")

df["timestamp"] = pd.to_datetime(
    df["Date/Time"],
    format="%d %m %Y %H:%M",
)

df = df.sort_values("timestamp").reset_index(drop=True)

# Use nonnegative generation for battery simulation.
df["generation_kw"] = np.maximum(
    df["LV ActivePower (kW)"],
    0.0,
)

# Identify uninterrupted 10-minute sequences.
is_consecutive = (
    df["timestamp"].diff()
    == pd.Timedelta(minutes=10)
)

df["segment"] = (~is_consecutive).cumsum()

# Find the first uninterrupted 144-observation segment.
segment_sizes = df.groupby("segment").size()

eligible = segment_sizes[segment_sizes >= 144]

if eligible.empty:
    raise RuntimeError(
        "No continuous 24-hour sequence found."
    )

selected_segment = eligible.index[0]

selected = (
    df[df["segment"] == selected_segment]
    .head(144)
    .copy()
)

selected = selected[
    ["timestamp", "generation_kw"]
].reset_index(drop=True)

# Verify continuity.
assert len(selected) == 144

assert (
    selected["timestamp"].diff().iloc[1:]
    == pd.Timedelta(minutes=10)
).all()

output_path = "data/processed/real_wind_mpc_24h.csv"
selected.to_csv(output_path, index=False)

ramps = selected["generation_kw"].diff().abs().dropna()

print("=" * 60)
print("REAL WIND DATA FOR MPC")
print("=" * 60)

print("Observations:", len(selected))
print("Start:", selected["timestamp"].iloc[0])
print("End:", selected["timestamp"].iloc[-1])

print("\nGeneration statistics:")
print(
    f"Minimum: {selected['generation_kw'].min():.3f} kW"
)
print(
    f"Maximum: {selected['generation_kw'].max():.3f} kW"
)
print(
    f"Mean: {selected['generation_kw'].mean():.3f} kW"
)

print("\nUncontrolled wind ramps:")
print(f"Mean absolute ramp: {ramps.mean():.3f} kW")
print(f"Maximum ramp: {ramps.max():.3f} kW")

print("\nContinuity validation: PASS")
print("Saved:", output_path)
