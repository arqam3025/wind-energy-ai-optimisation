
import numpy as np
import pandas as pd

files = {
    "Reactive only":
        "results/reactive_only_baseline_24h.csv",
    "Persistence + reactive MPC":
        "results/persistence_mpc_reactive_safety_24h.csv",
    "XGBoost + reactive MPC":
        "results/xgboost_mpc_reactive_safety_24h.csv",
}
capacity = 2000.0
initial_soc = 50.0
dt = 10 / 60

rows = []

for name, path in files.items():

    df = pd.read_csv(path)

    charge = df["charge_kw"].to_numpy(dtype=float)
    discharge = df["discharge_kw"].to_numpy(dtype=float)
    soc = df["soc_percent"].to_numpy(dtype=float)

    charge_energy = charge.sum() * dt
    discharge_energy = discharge.sum() * dt

    rows.append({
        "Controller": name,
        "Charge (kWh)": round(charge_energy, 2),
        "Discharge (kWh)": round(discharge_energy, 2),
        "Throughput (kWh)": round(
            charge_energy + discharge_energy, 2
        ),
        "Min SOC (%)": round(soc.min(), 2),
        "Max SOC (%)": round(soc.max(), 2),
        "Final SOC (%)": round(soc[-1], 2),
        "SOC change (pp)": round(
            soc[-1] - initial_soc, 2
        ),
        "Near 10% SOC": int((soc <= 10.1).sum()),
        "Near 90% SOC": int((soc >= 89.9).sum()),
        "Active intervals": int(
            ((charge > 0.01) | (discharge > 0.01)).sum()
        ),
    })

comparison = pd.DataFrame(rows)

print("=" * 75)
print("BATTERY USAGE COMPARISON")
print("=" * 75)

print(
    comparison.to_string(index=False)
)

print("\nNotes:")
print("- Throughput is charging plus discharging energy.")
print("- SOC change is measured in percentage points.")
print("- Near-limit counts use a 0.1 percentage-point band.")
print("- Both controllers start at 50% SOC.")

output_path = "results/battery_usage_comparison.csv"
comparison.to_csv(output_path, index=False)

print("\nSaved:", output_path)
