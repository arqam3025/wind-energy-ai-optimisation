
import numpy as np
import pandas as pd

df = pd.read_csv("data/raw/T1.csv")

df["timestamp"] = pd.to_datetime(
    df["Date/Time"],
    format="%d %m %Y %H:%M",
)

df = df.sort_values("timestamp").reset_index(drop=True)

start = df["timestamp"].min()
day7 = df[
    df["timestamp"] < start + pd.Timedelta(days=7)
].copy()

capacity = 2000.0
max_power = 1000.0
min_soc = 0.10
max_soc = 0.90
dt = 10 / 60
eta_charge = 0.95
eta_discharge = 0.95
ramp_limit = 200.0


def simulate(soc_aware=False):
    energy = capacity * 0.50
    previous_export = None
    previous_time = None
    records = []

    for _, row in day7.iterrows():
        timestamp = row["timestamp"]
        generation = max(
            0.0, row["LV ActivePower (kW)"]
        )

        consecutive = (
            previous_time is not None
            and timestamp - previous_time
            == pd.Timedelta(minutes=10)
        )

        if previous_export is None or not consecutive:
            desired_export = generation
        else:
            desired_export = np.clip(
                generation,
                previous_export - ramp_limit,
                previous_export + ramp_limit,
            )

        requested = generation - desired_export
        soc = energy / capacity

        # Reserve discharge energy as SOC approaches 30%.
        # This is a heuristic, not an optimal policy.
        if soc_aware and requested < 0:
            reserve_factor = np.clip(
                (soc - min_soc) / (0.30 - min_soc),
                0.0,
                1.0,
            )
            requested *= reserve_factor

        if requested >= 0:
            available_space = capacity * max_soc - energy
            allowed = available_space / (eta_charge * dt)

            battery_power = min(
                requested,
                max_power,
                max(0.0, allowed),
            )

            energy += battery_power * eta_charge * dt

        else:
            available_energy = energy - capacity * min_soc
            allowed = (
                available_energy * eta_discharge / dt
            )

            discharge = min(
                abs(requested),
                max_power,
                max(0.0, allowed),
            )

            battery_power = -discharge
            energy -= discharge / eta_discharge * dt

        export = generation - battery_power

        records.append({
            "timestamp": timestamp,
            "generation": generation,
            "export": export,
            "battery_power": battery_power,
            "soc": energy / capacity,
        })

        previous_export = export
        previous_time = timestamp

    result = pd.DataFrame(records)

    valid = (
        result["timestamp"].diff()
        == pd.Timedelta(minutes=10)
    )

    ramps = result["export"].diff().abs()[valid]

    assert result["soc"].between(
        min_soc - 1e-8, max_soc + 1e-8
    ).all()

    assert (
        result["battery_power"].abs()
        <= max_power + 1e-8
    ).all()

    return {
        "mean_ramp": ramps.mean(),
        "max_ramp": ramps.max(),
        "violations": int(
            (ramps > ramp_limit + 0.001).sum()
        ),
        "final_soc": result["soc"].iloc[-1] * 100,
        "min_soc": result["soc"].min() * 100,
    }


baseline = simulate(soc_aware=False)
aware = simulate(soc_aware=True)

print("=" * 60)
print("BATTERY CONTROLLER COMPARISON")
print("=" * 60)

for name, result in [
    ("Reactive controller", baseline),
    ("SOC-aware controller", aware),
]:
    print(f"\n{name}")
    print(f"Mean absolute ramp: {result['mean_ramp']:.3f} kW")
    print(f"Maximum ramp: {result['max_ramp']:.3f} kW")
    print(f"Ramp violations: {result['violations']}")
    print(f"Final SOC: {result['final_soc']:.2f}%")
    print(f"Minimum SOC: {result['min_soc']:.2f}%")

print("\nBattery constraints: PASS")
