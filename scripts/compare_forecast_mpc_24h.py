
import numpy as np
import pandas as pd

source = pd.read_csv(
    "data/processed/forecast_mpc_24h.csv",
    parse_dates=["timestamp"],
)

persistence = pd.read_csv(
    "results/persistence_driven_mpc_24h.csv",
    parse_dates=["timestamp"],
)

xgboost = pd.read_csv(
    "results/xgboost_safe_mpc_24h.csv",
    parse_dates=["timestamp"],
)

initial_time = source["timestamp"].iloc[0]
initial_export = max(
    0.0, float(source["current_power_kw"].iloc[0])
)

expected_times = (
    source["timestamp"] + pd.Timedelta(minutes=10)
)

assert len(source) == len(persistence) == len(xgboost)
assert persistence["timestamp"].reset_index(drop=True).equals(
    expected_times.reset_index(drop=True)
)
assert xgboost["timestamp"].reset_index(drop=True).equals(
    expected_times.reset_index(drop=True)
)

wind = source["actual_h1_kw"].to_numpy(dtype=float)

assert np.allclose(
    wind,
    persistence["wind_generation_kw"].to_numpy()
)
assert np.allclose(
    wind,
    xgboost["wind_generation_kw"].to_numpy()
)

def calculate_metrics(name, exports, soc=None):
    exports = np.asarray(exports, dtype=float)

    # Include initial transition.
    full_exports = np.concatenate([
        [initial_export],
        exports,
    ])

    ramps = np.abs(np.diff(full_exports))

    return {
        "Controller": name,
        "Mean ramp (kW)": round(ramps.mean(), 3),
        "Max ramp (kW)": round(ramps.max(), 3),
        "Violations >200 kW": int(
            (ramps > 200.001).sum()
        ),
        "Negative export intervals": int(
            (exports < -0.01).sum()
        ),
        "Final SOC (%)": (
            round(float(soc), 3)
            if soc is not None else np.nan
        ),
    }

rows = [
    calculate_metrics(
        "No battery",
        wind,
    ),
    calculate_metrics(
        "Persistence MPC",
        persistence["grid_export_kw"],
        persistence["soc_percent"].iloc[-1],
    ),
    calculate_metrics(
        "XGBoost Safe MPC",
        xgboost["grid_export_kw"],
        xgboost["soc_percent"].iloc[-1],
    ),
]

comparison = pd.DataFrame(rows)

print("=" * 72)
print("FORECAST-DRIVEN MPC: CONSISTENT 24-HOUR COMPARISON")
print("=" * 72)

print("Initial timestamp:", initial_time)
print("Initial grid export:", f"{initial_export:.3f} kW")
print("Controlled intervals:", len(wind))

print("\nResults:")
print(comparison.to_string(index=False))

baseline = rows[0]["Mean ramp (kW)"]
safe_mpc = rows[2]["Mean ramp (kW)"]

improvement = 100 * (baseline - safe_mpc) / baseline

print(
    "\nXGBoost Safe MPC mean-ramp reduction:",
    f"{improvement:.2f}%"
)

output_path = "results/forecast_mpc_24h_comparison.csv"
comparison.to_csv(output_path, index=False)

print("\nSaved:", output_path)
