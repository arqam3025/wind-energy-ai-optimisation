
import numpy as np
import pandas as pd

df = pd.read_csv("results/real_wind_mpc_24h.csv")

charge = df["charge_kw"].to_numpy()
discharge = df["discharge_kw"].to_numpy()

# Simultaneous power is the smaller of charging
# and discharging power at each interval.
simultaneous = np.minimum(charge, discharge)

tolerance = 0.01
mask = simultaneous > tolerance

print("=" * 60)
print("MPC SIMULTANEOUS OPERATION DIAGNOSIS")
print("=" * 60)

print("Total intervals:", len(df))
print("Affected intervals:", int(mask.sum()))

print("\nSimultaneous charging/discharging:")
print(f"Maximum overlap: {simultaneous.max():.3f} kW")
print(
    f"Total overlapping energy: "
    f"{simultaneous.sum() * (10 / 60):.3f} kWh"
)

print("\nAffected intervals:")
if mask.any():
    columns = [
        "timestamp",
        "charge_kw",
        "discharge_kw",
        "soc_percent",
    ]

    print(
        df.loc[mask, columns].to_string(index=False)
    )
else:
    print("None")

print("\nDiagnostic completed.")
