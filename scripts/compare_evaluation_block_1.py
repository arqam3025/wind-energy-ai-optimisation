
import numpy as np
import pandas as pd

files = {
    "Persistence SOC-aware":
        "results/persistence_mpc_evaluation_block_1.csv",
    "XGBoost SOC-aware":
        "results/xgboost_mpc_evaluation_block_1.csv",
}

source = pd.read_csv(
    "data/processed/evaluation_block_1.csv",
    parse_dates=["timestamp"]
)

initial_export = max(
    0.0, float(source["current_power_kw"].iloc[0])
)

dt = 10 / 60
rows = []

for name, path in files.items():
    df = pd.read_csv(path, parse_dates=["timestamp"])

    expected_times = (
        source["timestamp"] + pd.Timedelta(minutes=10)
    )

    if len(df) != 144 or not np.array_equal(
        df["timestamp"].to_numpy(),
        expected_times.to_numpy()
    ):
        raise ValueError(f"Timestamp alignment failed: {name}")

    grid = df["grid_export_kw"].to_numpy()

    ramps = np.abs(np.diff(
        np.concatenate([[initial_export], grid])
    ))

    charge_kwh = df["charge_kw"].sum() * dt
    discharge_kwh = df["discharge_kw"].sum() * dt

    rows.append({
        "Controller": name,
        "Mean ramp (kW)": round(ramps.mean(), 3),
        "Max ramp (kW)": round(ramps.max(), 3),
        "Violations": int((ramps > 200.001).sum()),
        "Charge (kWh)": round(charge_kwh, 2),
        "Discharge (kWh)": round(discharge_kwh, 2),
        "Throughput (kWh)": round(
            charge_kwh + discharge_kwh, 2
        ),
        "Min SOC (%)": round(df["soc_percent"].min(), 2),
        "Max SOC (%)": round(df["soc_percent"].max(), 2),
        "Final SOC (%)": round(df["soc_percent"].iloc[-1], 2),
    })

comparison = pd.DataFrame(rows)

print("=" * 75)
print("EVALUATION BLOCK 1: CONTROLLER COMPARISON")
print("=" * 75)
print(comparison.to_string(index=False))

output = "results/evaluation_block_1_comparison.csv"
comparison.to_csv(output, index=False)

print("\nSaved:", output)
