
import numpy as np
import pandas as pd
from pathlib import Path

source = pd.read_csv(
    "data/processed/forecast_mpc_24h.csv"
)

initial_export = max(
    0.0, float(source["current_power_kw"].iloc[0])
)

files = {
    "Persistence SOC-aware":
        "results/persistence_mpc_soc_aware_24h.csv",
    "XGBoost SOC-aware":
        "results/xgboost_mpc_soc_aware_24h.csv",
}

dt = 10 / 60
rows = []

for name, path in files.items():

    df = pd.read_csv(path, parse_dates=["timestamp"])

    export = df["grid_export_kw"].to_numpy()
    ramps = np.abs(np.diff(
        np.concatenate([[initial_export], export])
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
        "Min SOC (%)": round(
            df["soc_percent"].min(), 2
        ),
        "Max SOC (%)": round(
            df["soc_percent"].max(), 2
        ),
        "Final SOC (%)": round(
            df["soc_percent"].iloc[-1], 2
        ),
        "Near min SOC": int(
            (df["soc_percent"] <= 10.1).sum()
        ),
        "Near max SOC": int(
            (df["soc_percent"] >= 89.9).sum()
        ),
    })

comparison = pd.DataFrame(rows)

print("=" * 80)
print("SOC-AWARE CONTROLLER COMPARISON")
print("=" * 80)

print(comparison.to_string(index=False))

Path("results").mkdir(exist_ok=True)

output = "results/soc_aware_controller_comparison.csv"
comparison.to_csv(output, index=False)

print("\nSaved:", output)
