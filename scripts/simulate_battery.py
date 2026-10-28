
import pandas as pd

# Illustrative battery specifications, not actual turbine hardware.
capacity_kwh = 2000.0
max_power_kw = 1000.0

min_soc = 0.10
max_soc = 0.90
initial_soc = 0.50

charge_efficiency = 0.95
discharge_efficiency = 0.95

time_step_hours = 10 / 60

# Positive power = charging
# Negative power = discharging
requested_power_kw = [
    800, 800, 800, 800, 800, 800,
    -600, -600, -600, -600, -600, -600,
]

energy_kwh = capacity_kwh * initial_soc

records = []

for step, requested in enumerate(requested_power_kw):

    if requested >= 0:
        available_space = (
            capacity_kwh * max_soc - energy_kwh
        )

        allowed_by_soc = (
            available_space
            / (charge_efficiency * time_step_hours)
        )

        actual_power = min(
            requested,
            max_power_kw,
            max(0.0, allowed_by_soc),
        )

        energy_kwh += (
            actual_power
            * charge_efficiency
            * time_step_hours
        )

    else:
        available_energy = (
            energy_kwh - capacity_kwh * min_soc
        )

        allowed_by_soc = (
            available_energy
            * discharge_efficiency
            / time_step_hours
        )

        discharge_power = min(
            abs(requested),
            max_power_kw,
            max(0.0, allowed_by_soc),
        )

        actual_power = -discharge_power

        energy_kwh -= (
            discharge_power
            / discharge_efficiency
            * time_step_hours
        )

    soc = energy_kwh / capacity_kwh

    records.append({
        "step": step + 1,
        "requested_power_kw": requested,
        "actual_power_kw": actual_power,
        "battery_energy_kwh": energy_kwh,
        "soc_percent": soc * 100,
    })

results = pd.DataFrame(records)

print("=" * 60)
print("BATTERY ENERGY STORAGE SIMULATION")
print("=" * 60)

print(results.round(2).to_string(index=False))

print("\nFinal SOC:", round(soc * 100, 2), "%")
print("Minimum SOC:", round(results["soc_percent"].min(), 2), "%")
print("Maximum SOC:", round(results["soc_percent"].max(), 2), "%")

assert results["soc_percent"].between(
    min_soc * 100 - 1e-8,
    max_soc * 100 + 1e-8,
).all()

assert (
    results["actual_power_kw"].abs()
    <= max_power_kw + 1e-8
).all()

print("\nBattery SOC and power constraints: PASS")
