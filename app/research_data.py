"""Read-only access and accounting for the local research demonstration."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN_NAME = "final_20261029"
CONTROLLERS = {"adaptive_one_sided": "Adaptive one-sided MPC", "fixed": "Fixed-margin MPC"}
TABLE_DIRECTORY = Path("docs/tables_v2")
RAMP_LIMIT_KW = 200.0
VIOLATION_THRESHOLD_KW = 200.001

def load_table(name, root=ROOT):
    """Load the Git-visible v2 summary, with an explicit missing-artifact error."""
    allowed = {"aggregate_metrics", "block_metrics", "forecast_metrics", "paired_differences", "paired_summary", "uncertainty_coverage", "uncontrolled_wind_baseline"}
    if name not in allowed:
        raise ValueError("Unknown research table")
    return pd.read_csv(Path(root) / TABLE_DIRECTORY / f"{name}.csv")

def available_blocks(root=ROOT):
    data = load_table("block_metrics", root)
    blocks = sorted(data.block_id.astype(int).unique().tolist())
    return [block for block in blocks if block != 6]

def load_replay(block_id, root=ROOT):
    """Require both frozen traces and the input needed for exact first-ramp accounting."""
    if block_id not in available_blocks(root):
        raise ValueError("Block is not eligible for the frozen comparison")
    root = Path(root)
    source = root / f"data/processed/evaluation_block_{block_id}.csv"
    paths = {kind: root / "results/frozen_heldout" / RUN_NAME / kind / f"adaptive_charging_mpc_block_{block_id}_weight_0p500.csv" for kind in CONTROLLERS}
    missing = [str(path.relative_to(root)) for path in [source, *paths.values()] if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing local replay artifacts: " + "; ".join(missing))
    inputs = pd.read_csv(source, parse_dates=["timestamp"])
    traces = {kind: pd.read_csv(path, parse_dates=["timestamp"]) for kind, path in paths.items()}
    expected = inputs.timestamp + pd.Timedelta(minutes=10)
    for kind, trace in traces.items():
        if len(trace) != 144 or not np.array_equal(trace.timestamp.to_numpy(), expected.to_numpy()):
            raise ValueError(f"Replay timestamp alignment failed for {kind}")
    return inputs, traces

def interval_accounting(inputs, trace):
    """Compute display fields with the frozen transition and AC-energy conventions."""
    result = trace.copy()
    previous = np.r_[max(0.0, float(inputs.current_power_kw.iloc[0])), result.grid_export_kw.to_numpy()[:-1]]
    result["absolute_grid_ramp_kw"] = np.abs(result.grid_export_kw.to_numpy() - previous)
    result["ramp_exceedance_kw"] = np.maximum(result.absolute_grid_ramp_kw - RAMP_LIMIT_KW, 0)
    result["ramp_violation"] = result.absolute_grid_ramp_kw > VIOLATION_THRESHOLD_KW
    wind = np.maximum(0, inputs.actual_h1_kw.to_numpy())
    result["uncontrolled_ramp_kw"] = np.abs(np.diff(np.r_[max(0.0, float(inputs.current_power_kw.iloc[0])), wind]))
    result["battery_net_power_kw"] = result.discharge_kw - result.charge_kw
    result["throughput_kwh"] = (result.charge_kw + result.discharge_kw) / 6
    result["conversion_loss_kwh"] = (.05 * result.charge_kw + (1/.95-1) * result.discharge_kw) / 6
    return result

def fixed_margins(root=ROOT):
    calibration = Path(root) / "results/multistep_uncertainty_calibration_split.csv"
    if not calibration.is_file():
        return None
    values = pd.read_csv(calibration).sort_values("horizon_minutes")
    return values.calibration_quantile_kw.to_numpy()

def aggregate_comparison(root=ROOT):
    totals = load_table("aggregate_metrics", root).set_index("controller")
    baseline = load_table("uncontrolled_wind_baseline", root)
    rows = []
    for kind, label in CONTROLLERS.items():
        row = totals.loc[kind]
        rows.append({"Strategy": label, "Ramp violations": int(row.ramp_violations), "Ramp exceedance (kW sum)": row.ramp_exceedance_kw,
            "Throughput (MWh AC)": row.throughput_kwh/1000, "Conversion losses (MWh)": row.conversion_losses_kwh/1000,
            "Actual export (MWh)": row.export_kwh/1000, "Terminal-adjusted export (MWh)": row.terminal_adjusted_export_kwh/1000,
            "Curtailment (MWh)": row.curtailment_kwh/1000, "Inventory change (MWh stored)": row.terminal_energy_delta_kwh/1000})
    rows.append({"Strategy": "Uncontrolled wind", "Ramp violations": int(baseline.ramp_violations.sum()),
        "Ramp exceedance (kW sum)": baseline.ramp_exceedance_kw.sum(), "Throughput (MWh AC)": 0., "Conversion losses (MWh)": 0.,
        "Actual export (MWh)": baseline.wind_energy_kwh.sum()/1000, "Terminal-adjusted export (MWh)": np.nan,
        "Curtailment (MWh)": 0., "Inventory change (MWh stored)": 0.})
    return pd.DataFrame(rows).set_index("Strategy")
