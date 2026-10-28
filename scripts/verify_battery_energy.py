
import pandas as pd

files = {
    "Reactive only":
        "results/reactive_only_baseline_24h.csv",
    "XGBoost + reactive MPC":
        "results/xgboost_mpc_reactive_safety_24h.csv",
}

capacity = 2000.0
initial_energy = 0.5 * capacity
dt = 10 / 60

eta_charge = 0.95
eta_discharge = 0.95

all_passed = True

for name, path in files.items():

    df = pd.read_csv(path)

    charge_kwh = df["charge_kw"].sum() * dt
    discharge_kwh = df["discharge_kw"].sum() * dt

    final_energy = (
        initial_energy
        + eta_charge * charge_kwh
        - discharge_kwh / eta_discharge
    )

    calculated_soc = (
        100 * final_energy / capacity
    )

    reported_soc = df["soc_percent"].iloc[-1]

    difference = abs(calculated_soc - reported_soc)
    passed = difference < 0.01

    all_passed = all_passed and passed

    print("=" * 55)
    print(name)
    print("=" * 55)

    print(f"Charging: {charge_kwh:.3f} kWh")
    print(f"Discharging: {discharge_kwh:.3f} kWh")
    print(f"Calculated final SOC: {calculated_soc:.3f}%")
    print(f"Reported final SOC:   {reported_soc:.3f}%")
    print(f"Difference: {difference:.6f} percentage points")
    print("Energy balance:", "PASS" if passed else "FAIL")
    print()

print(
    "Overall validation:",
    "PASS" if all_passed else "FAIL"
)
