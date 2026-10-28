
import pandas as pd

path = "results/multistep_mpc_test_forecasts.csv"

df = pd.read_csv(path, parse_dates=["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)

print("=" * 65)
print("AVAILABLE TEST PERIODS")
print("=" * 65)

print("Total forecast origins:", len(df))
print("First timestamp:", df["timestamp"].min())
print("Last timestamp:", df["timestamp"].max())

time_difference = df["timestamp"].diff()

gap_count = int(
    (time_difference.iloc[1:] != pd.Timedelta(minutes=10)).sum()
)

print("Non-continuous 10-minute gaps:", gap_count)

# Identify uninterrupted sequences of forecast origins.
segment_id = (
    time_difference.ne(pd.Timedelta(minutes=10))
).cumsum()

segments = []

for _, group in df.groupby(segment_id):
    rows = len(group)
    complete_days = rows // 144

    segments.append({
        "Start": group["timestamp"].iloc[0],
        "End": group["timestamp"].iloc[-1],
        "Rows": rows,
        "Complete 24h blocks": complete_days,
    })

summary = pd.DataFrame(segments)

print("\nContinuous segments:")
print(summary.to_string(index=False))

total_blocks = int(summary["Complete 24h blocks"].sum())

print("\nTotal non-overlapping complete 24h blocks:", total_blocks)

selected_start = pd.Timestamp("2018-11-14 13:00:00")
selected_end = pd.Timestamp("2018-11-15 12:50:00")

selected = df[
    df["timestamp"].between(selected_start, selected_end)
]

print("\nPreviously evaluated period:")
print("Start:", selected_start)
print("End:", selected_end)
print("Available rows:", len(selected))

print("\nInspection completed.")
