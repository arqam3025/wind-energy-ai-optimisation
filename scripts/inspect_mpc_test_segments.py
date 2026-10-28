
import pandas as pd

DATA_PATH = "results/multistep_mpc_test_forecasts.csv"

df = pd.read_csv(
    DATA_PATH,
    parse_dates=["timestamp"],
)

df = df.sort_values("timestamp").reset_index(drop=True)

# A new segment begins whenever the timestamp
# difference is not exactly 10 minutes.
time_difference = df["timestamp"].diff()

new_segment = (
    time_difference.ne(pd.Timedelta(minutes=10))
)

df["segment_id"] = new_segment.cumsum()

segments = (
    df.groupby("segment_id")
    .agg(
        start=("timestamp", "min"),
        end=("timestamp", "max"),
        observations=("timestamp", "size"),
    )
    .reset_index(drop=True)
)

segments = segments.sort_values(
    "observations", ascending=False
).reset_index(drop=True)

print("=" * 65)
print("MPC TEST DATA CONTINUITY ANALYSIS")
print("=" * 65)

print("Total forecast windows:", len(df))
print("Continuous segments:", len(segments))

print("\nTen longest continuous segments:")

print(
    segments.head(10).to_string(index=False)
)

print("\nSegments with at least 144 observations:")

eligible = segments[
    segments["observations"] >= 144
]

print("Count:", len(eligible))

if not eligible.empty:
    selected = eligible.iloc[0]

    print("\nLongest eligible segment:")
    print("Start:", selected["start"])
    print("End:", selected["end"])
    print("Observations:", selected["observations"])

    print("\nFirst 24-hour simulation:")
    print("Start:", selected["start"])
    print(
        "Last forecast origin:",
        selected["start"]
        + pd.Timedelta(minutes=1430)
    )
else:
    print(
        "\nNo uninterrupted 144-observation "
        "segment is available."
    )

print("\nStep 54 completed.")
