
import numpy as np
import pandas as pd

df = pd.read_csv(
    "data/raw/T1.csv"
)

df["timestamp"] = pd.to_datetime(
    df["Date/Time"],
    format="%d %m %Y %H:%M",
)

df = df.sort_values("timestamp").reset_index(drop=True)

# Use the first seven days of real turbine measurements.
start = df["timestamp"].min()
end = start + pd.Timedelta(days=7)

day = df[
    (df["timestamp"] >= start)
    & (df["timestamp"] < end)
].copy()

# Battery specifications (illustrative).
capacity_kwh = 2000.0
max_power_kw = 1000.0

min_soc = 0.10
max_soc = 0.90
soc = 0.50

charge_efficiency = 0.95
discharge_efficiency = 0.95

dt = 10 / 60

# Maximum desired export change per 10-minute interval.
ramp_limit_kw = 200.0

energy_kwh = capacity_kwh * soc

previous_export = None
previous_timestamp = None
records = []

for _, row in day.iterrows():

    timestamp = row["timestamp"]
    generation = max(0.0, row["LV ActivePower (kW)"])

    # A missing interval cannot be treated as a normal
    # 10-minute ramp measurement.
    consecutive = (
        previous_timestamp is not None
        and timestamp - previous_timestamp
        == pd.Timedelta(minutes=10)
    )

    if previous_export is None or not consecutive:
        desired_export = generation
    else:
        desired_export = np.clip(
            generation,
            previous_export - ramp_limit_kw,
            previous_export + ramp_limit_kw,
        )

    # Positive battery power means charging.
    requested_battery_power = generation - desired_export

    if requested_battery_power >= 0:

        available_space = (
            capacity_kwh * max_soc - energy_kwh
        )

        max_charge_by_soc = (
            available_space / (charge_efficiency * dt)
        )

        battery_power = min(
            requested_battery_power,
            max_power_kw,
            max(0.0, max_charge_by_soc),
        )

        energy_kwh += (
            battery_power * charge_efficiency * dt
        )

    else:

        available_energy = (
            energy_kwh - capacity_kwh * min_soc
        )

        max_discharge_by_soc = (
            available_energy * discharge_efficiency / dt
        )

        discharge_power = min(
            abs(requested_battery_power),
            max_power_kw,
            max(0.0, max_discharge_by_soc),
        )

        battery_power = -discharge_power

        energy_kwh -= (
            discharge_power / discharge_efficiency * dt
        )

    export_power = generation - battery_power

    records.append({
        "timestamp": timestamp,
        "wind_generation_kw": generation,
        "battery_power_kw": battery_power,
        "grid_export_kw": export_power,
        "soc_percent": 100 * energy_kwh / capacity_kwh,
    })

    previous_export = export_power
    previous_timestamp = timestamp

results = pd.DataFrame(records)

# Evaluate only consecutive 10-minute measurements.
consecutive = (
    results["timestamp"].diff()
    == pd.Timedelta(minutes=10)
)

raw_ramps = results["wind_generation_kw"].diff().abs()
smoothed_ramps = results["grid_export_kw"].diff().abs()

raw_ramps = raw_ramps[consecutive]
smoothed_ramps = smoothed_ramps[consecutive]

print("=" * 60)
print("WIND TURBINE + BATTERY SMOOTHING")
print("=" * 60)

print("Observations:", len(results))
print("Valid ramp intervals:", len(raw_ramps))

print("\nMean absolute ramp:")
print(f"Without battery: {raw_ramps.mean():.3f} kW")
print(f"With battery:    {smoothed_ramps.mean():.3f} kW")

print("\nMaximum absolute ramp:")
print(f"Without battery: {raw_ramps.max():.3f} kW")
print(f"With battery:    {smoothed_ramps.max():.3f} kW")

print("\nBattery SOC summary:")
print(f"Initial SOC: 50.00%")
print(f"Final SOC: {results['soc_percent'].iloc[-1]:.2f}%")
print(f"Minimum SOC: {results['soc_percent'].min():.2f}%")
print(f"Maximum SOC: {results['soc_percent'].max():.2f}%")

print("\nBattery activity:")
print(
    "Charging intervals:",
    (results["battery_power_kw"] > 0.001).sum()
)
print(
    "Discharging intervals:",
    (results["battery_power_kw"] < -0.001).sum()
)

print(
    "Intervals at minimum SOC:",
    (results["soc_percent"] <= 10.001).sum()
)
print(
    "Intervals at maximum SOC:",
    (results["soc_percent"] >= 89.999).sum()
)

assert results["soc_percent"].between(
    min_soc * 100 - 1e-8,
    max_soc * 100 + 1e-8,
).all()

assert (
    results["battery_power_kw"].abs()
    <= max_power_kw + 1e-8
).all()

# Compare requested smoothing power with delivered power.
# Reconstruct requested power using the same ramp target.
previous_export = None
previous_timestamp = None
unmet_charge = 0
unmet_discharge = 0
unmet_charge_energy_kwh = 0.0
unmet_discharge_energy_kwh = 0.0

for _, row in results.iterrows():
    timestamp = row["timestamp"]
    generation = row["wind_generation_kw"]
    actual_battery_power = row["battery_power_kw"]

    consecutive = (
        previous_timestamp is not None
        and timestamp - previous_timestamp
        == pd.Timedelta(minutes=10)
    )

    if previous_export is None or not consecutive:
        desired_export = generation
    else:
        desired_export = np.clip(
            generation,
            previous_export - ramp_limit_kw,
            previous_export + ramp_limit_kw,
        )

    requested = generation - desired_export
    unmet = requested - actual_battery_power

    if unmet > 0.001:
        unmet_charge += 1
        unmet_charge_energy_kwh += unmet * dt

    elif unmet < -0.001:
        unmet_discharge += 1
        unmet_discharge_energy_kwh += abs(unmet) * dt

    previous_export = row["grid_export_kw"]
    previous_timestamp = timestamp

print("\nSmoothing requests not fully met:")
print("Charging requests:", unmet_charge)
print("Discharging requests:", unmet_discharge)
print(
    f"Unmet charging energy: "
    f"{unmet_charge_energy_kwh:.2f} kWh"
)
print(
    f"Unmet discharging energy: "
    f"{unmet_discharge_energy_kwh:.2f} kWh"
)

print("\nRamp-limit violations:")
violations = (smoothed_ramps > ramp_limit_kw + 0.001).sum()
print("Intervals exceeding 200 kW:", violations)
print(
    f"Violation rate: "
    f"{100 * violations / len(smoothed_ramps):.2f}%"
)

# Diagnose whether unmet discharge requests were caused
# by the battery power limit or insufficient stored energy.

power_limited = 0
soc_limited = 0

previous_export = None
previous_timestamp = None

for _, row in results.iterrows():

    timestamp = row["timestamp"]
    generation = row["wind_generation_kw"]

    consecutive = (
        previous_timestamp is not None
        and timestamp - previous_timestamp
        == pd.Timedelta(minutes=10)
    )

    if previous_export is None or not consecutive:
        desired_export = generation
    else:
        desired_export = np.clip(
            generation,
            previous_export - ramp_limit_kw,
            previous_export + ramp_limit_kw,
        )

    requested = generation - desired_export
    actual = row["battery_power_kw"]

    if requested < 0 and actual > requested + 0.001:

        if abs(requested) > max_power_kw + 0.001:
            power_limited += 1

        # This is an SOC-limited case only when the
        # requested discharge is within the power rating.
        else:
            soc_limited += 1

    previous_export = row["grid_export_kw"]
    previous_timestamp = timestamp

print("\nDischarge limitation diagnosis:")
print("Requests exceeding power rating:", power_limited)
print("Requests limited by available SOC:", soc_limited)
print("Total unmet discharge requests:",
      power_limited + soc_limited)

print("\nBattery constraints: PASS")
