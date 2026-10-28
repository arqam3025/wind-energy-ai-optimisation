
from pathlib import Path
import pandas as pd

df = pd.read_csv(
    "results/multistep_mpc_test_forecasts.csv",
    parse_dates=["timestamp"]
)

df = df.sort_values("timestamp").reset_index(drop=True)

expected_interval = pd.Timedelta(minutes=10)

segment_id = (
    df["timestamp"].diff().ne(expected_interval)
).cumsum()

development_start = pd.Timestamp("2018-11-14 13:00:00")
development_end = pd.Timestamp("2018-11-15 12:50:00")

records = []
block_id = 0

for segment_number, (_, segment) in enumerate(
    df.groupby(segment_id), start=1
):
    segment = segment.reset_index(drop=True)

    complete_blocks = len(segment) // 144

    for block_number in range(complete_blocks):

        start_row = block_number * 144
        block = segment.iloc[start_row:start_row + 144]

        start = block["timestamp"].iloc[0]
        end = block["timestamp"].iloc[-1]

        block_id += 1

        is_development = (
            start <= development_end
            and end >= development_start
        )

        records.append({
            "block_id": block_id,
            "segment_id": segment_number,
            "start_timestamp": start,
            "end_timestamp": end,
            "forecast_origins": len(block),
            "evaluation_role": (
                "development"
                if is_development
                else "evaluation"
            )
        })

schedule = pd.DataFrame(records)

Path("results").mkdir(exist_ok=True)

output_path = "results/evaluation_schedule.csv"
schedule.to_csv(output_path, index=False)

print("=" * 75)
print("INDEPENDENT EVALUATION SCHEDULE")
print("=" * 75)

print("Total complete blocks:", len(schedule))

print(
    "Development blocks:",
    int((schedule["evaluation_role"] == "development").sum())
)

print(
    "Evaluation blocks:",
    int((schedule["evaluation_role"] == "evaluation").sum())
)

print("\nDevelopment block:")
print(
    schedule[
        schedule["evaluation_role"] == "development"
    ].to_string(index=False)
)

print("\nFirst five evaluation blocks:")
print(
    schedule[
        schedule["evaluation_role"] == "evaluation"
    ].head(5).to_string(index=False)
)

print("\nLast five evaluation blocks:")
print(
    schedule[
        schedule["evaluation_role"] == "evaluation"
    ].tail(5).to_string(index=False)
)

print("\nSaved:", output_path)
