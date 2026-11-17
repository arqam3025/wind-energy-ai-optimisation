"""Validated read-only research data for WindGrid AI.

No optimisation, model fitting, output writes, or replacement of frozen artifacts
occurs here. The uncontrolled trace is a defined no-battery reference calculated
from measured wind; its nonexistent battery state is explicitly missing.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import platform
import sys

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RUN_NAME = "final_20261029"
CASES = {"adaptive_one_sided": "Adaptive one-sided MPC", "fixed": "Fixed-margin MPC", "uncontrolled": "Uncontrolled wind"}
EXPECTED_FREEZE_SHA256 = "b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a"
ELIGIBLE_BLOCKS = tuple(b for b in range(1, 51) if b != 6)
HORIZONS = tuple(range(10, 61, 10))
DT_HOURS = 1 / 6
CAPACITY_KWH = 2000.0
RAMP_LIMIT_KW = 200.0
VIOLATION_THRESHOLD_KW = 200.001


class ArtifactError(ValueError):
    """A missing or invalid research artifact, safe to explain in the UI."""


@dataclass
class ReplayBundle:
    inputs: pd.DataFrame
    traces: dict[str, pd.DataFrame]
    block_id: int


TABLE_SCHEMAS = {
    "aggregate_metrics": {"controller", "intervals", "transitions", "ramp_violations", "ramp_exceedance_kw", "throughput_kwh", "charge_kwh", "discharge_kwh", "conversion_losses_kwh", "export_kwh", "terminal_adjusted_export_kwh", "curtailment_kwh", "terminal_energy_delta_kwh"},
    "block_metrics": {"block_id", "controller", "intervals", "transitions", "ramp_violations", "ramp_exceedance_kw", "throughput_kwh", "conversion_losses_kwh", "export_kwh", "terminal_adjusted_export_kwh", "curtailment_kwh", "terminal_energy_delta_kwh", "final_soc_percent"},
    "forecast_metrics": {"model", "horizon_minutes", "mae_kw", "rmse_kw", "mse_kw"},
    "paired_differences": {"block_id", "throughput_kwh", "conversion_losses_kwh", "ramp_exceedance_kw", "ramp_violations", "terminal_adjusted_export_kwh"},
    "paired_summary": {"metric", "mean_difference", "median_difference", "lower_descriptive_bootstrap", "upper_descriptive_bootstrap", "negative_blocks", "positive_blocks", "ties"},
    "uncertainty_coverage": {"block_id", "controller", "horizon_minutes", "lower_bound_coverage", "mean_margin_kw"},
    "uncontrolled_wind_baseline": {"block_id", "ramp_violations", "ramp_exceedance_kw", "wind_energy_kwh"},
}


def data_root(root=None):
    """Resolve per call so cached data cannot mask a changed artifact root."""
    return Path(root if root is not None else os.environ.get("WINDGRID_DATA_ROOT", ROOT)).resolve()


def _signature(path):
    try:
        stat = path.stat()
        return (stat.st_mtime_ns, stat.st_size)
    except OSError as error:
        raise ArtifactError(f"Missing research artifact: {path}. Restore the original local artifact; no data has been fabricated.") from error


@st.cache_data(show_spinner=False, max_entries=80, ttl=120)
def _csv_cached(path_text, signature):
    # The file's size and nanosecond modification time are part of the cache key.
    try:
        return pd.read_csv(path_text)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        raise ArtifactError(f"Could not read research CSV {path_text}: {error}") from error


def _csv(path):
    return _csv_cached(str(path), _signature(path)).copy(deep=True)


def _require_columns(frame, columns, path):
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ArtifactError(f"Invalid research artifact {path}: missing columns {', '.join(missing)}.")


def _finite(frame, columns, path):
    for name in columns:
        try:
            values = pd.to_numeric(frame[name], errors="raise").to_numpy(dtype=float)
        except (TypeError, ValueError) as error:
            raise ArtifactError(f"Invalid numeric column {name} in {path}.") from error
        if not np.isfinite(values).all():
            raise ArtifactError(f"Non-finite or missing numeric values in {path}: {name}.")


def _timestamps(frame, path):
    try:
        times = pd.to_datetime(frame["timestamp"], errors="raise")
    except (TypeError, ValueError) as error:
        raise ArtifactError(f"Invalid timestamps in {path}.") from error
    if times.isna().any() or times.duplicated().any() or not times.is_monotonic_increasing:
        raise ArtifactError(f"Missing, duplicate or unordered timestamps in {path}.")
    if times.dt.tz is not None:
        raise ArtifactError(f"Expected the original timezone-naive dataset clock in {path}.")
    frame["timestamp"] = times
    return times


def get_table(name, root=None):
    """Validated saved summary; available even without private interval inputs."""
    if name not in TABLE_SCHEMAS:
        raise ArtifactError(f"Unknown research table: {name}")
    path = data_root(root) / "docs/tables_v2" / f"{name}.csv"
    frame = _csv(path)
    _require_columns(frame, TABLE_SCHEMAS[name], path)
    if frame.empty:
        raise ArtifactError(f"Empty research summary: {path}")
    numeric = TABLE_SCHEMAS[name] - {"controller", "model", "metric"}
    _finite(frame, numeric, path)
    if name in {"aggregate_metrics", "block_metrics", "forecast_metrics", "uncertainty_coverage", "uncontrolled_wind_baseline"}:
        nonnegative = {"intervals", "transitions", "ramp_violations", "ramp_exceedance_kw", "throughput_kwh", "charge_kwh", "discharge_kwh", "conversion_losses_kwh", "curtailment_kwh", "export_kwh", "wind_energy_kwh", "mae_kw", "mse_kw", "rmse_kw", "mean_margin_kw"} & set(frame.columns)
        if any((pd.to_numeric(frame[column]) < -1e-6).any() for column in nonnegative):
            raise ArtifactError(f"Negative physical/count/error metric in {path}.")
    if "controller" in frame:
        if set(frame.controller) != {"fixed", "adaptive_one_sided"}:
            raise ArtifactError(f"Unexpected controller set in {path}; expected both frozen battery controllers.")
    if "block_id" in frame:
        if not np.equal(frame.block_id, frame.block_id.astype(int)).all() or set(frame.block_id.astype(int)) != set(ELIGIBLE_BLOCKS):
            raise ArtifactError(f"Invalid block set in {path}; expected 49 original blocks excluding development block 6.")
    keys = {
        "aggregate_metrics": ["controller"], "block_metrics": ["block_id", "controller"],
        "forecast_metrics": ["model", "horizon_minutes"], "paired_differences": ["block_id"],
        "paired_summary": ["metric"], "uncertainty_coverage": ["block_id", "controller", "horizon_minutes"],
        "uncontrolled_wind_baseline": ["block_id"],
    }[name]
    if frame.duplicated(keys).any():
        raise ArtifactError(f"Duplicate research summary keys in {path}: {', '.join(keys)}.")
    if name == "block_metrics":
        if len(frame) != 98 or not frame.intervals.eq(144).all() or not frame.transitions.eq(144).all():
            raise ArtifactError(f"Invalid paired episode counts in {path}; expected 98 controller-block rows of 144 transitions.")
    if name == "aggregate_metrics" and (not frame.intervals.eq(7056).all() or not frame.transitions.eq(7056).all()):
        raise ArtifactError(f"Invalid aggregate interval count in {path}.")
    if "horizon_minutes" in frame and set(frame.horizon_minutes.astype(int)) != set(HORIZONS):
        raise ArtifactError(f"Invalid horizon set in {path}; expected 10–60 minutes.")
    if name == "forecast_metrics":
        if set(frame.model) != {"xgboost", "persistence"} or len(frame) != 12:
            raise ArtifactError(f"Incomplete forecast comparison in {path}.")
    if name == "uncertainty_coverage":
        if len(frame) != 588 or not frame.lower_bound_coverage.between(0, 1).all():
            raise ArtifactError(f"Invalid horizon coverage data in {path}.")
    return frame


def valid_blocks(root=None):
    return sorted(get_table("block_metrics", root).block_id.astype(int).unique().tolist())


def _check_block(block_id, root):
    if isinstance(block_id, bool) or block_id not in valid_blocks(root):
        raise ArtifactError(f"Block {block_id} is not an eligible frozen evaluation block. Development block 6 is excluded.")


def validate_inputs(frame, path="forecast input"):
    required = {"timestamp", "current_power_kw"} | {f"{name}_h{h}_kw" for name in ["xgboost", "actual", "persistence"] for h in range(1, 7)}
    frame = frame.copy(deep=True)
    _require_columns(frame, required, path)
    _finite(frame, required - {"timestamp"}, path)
    times = _timestamps(frame, path)
    if len(frame) != 144 or not times.diff().iloc[1:].eq(pd.Timedelta(minutes=10)).all():
        raise ArtifactError(f"Expected exactly 144 continuous ten-minute forecast origins in {path}.")
    if not np.allclose(frame.actual_h1_kw.to_numpy()[:-1], np.maximum(0, frame.current_power_kw.to_numpy()[1:]), atol=.001, rtol=0):
        raise ArtifactError(f"Actual target/current-power alignment failed in {path}.")
    for h in range(1, 7):
        if not np.allclose(frame[f"persistence_h{h}_kw"], np.maximum(0, frame.current_power_kw), atol=.001, rtol=0):
            raise ArtifactError(f"Persistence forecast mismatch in {path}, horizon {h*10} minutes.")
        if not np.allclose(frame[f"actual_h{h}_kw"].to_numpy()[:-h], np.maximum(0, frame.current_power_kw.to_numpy()[h:]), atol=.001, rtol=0):
            raise ArtifactError(f"Within-block actual target alignment failed in {path}, horizon {h*10} minutes.")
    return frame


def validate_trace(inputs, trace, kind, path="controller trace"):
    """Reject physical/timestamp corruption rather than displaying plausible charts."""
    if kind not in {"fixed", "adaptive_one_sided"}:
        raise ArtifactError("Only recorded battery-controller traces can be validated here.")
    required = {"timestamp", "wind_generation_kw", "forecast_generation_kw", "downside_forecast_kw", "charge_kw", "discharge_kw", "curtailment_kw", "grid_export_kw", "soc_percent", "committed_charge_kw", "committed_discharge_kw", "committed_curtailment_kw"}
    if kind == "adaptive_one_sided":
        required |= {f"adaptive_margin_h{h}_kw" for h in range(1, 7)} | {"newest_residual_target"}
    frame = trace.copy(deep=True)
    _require_columns(frame, required, path)
    _finite(frame, required - {"timestamp", "newest_residual_target"}, path)
    times = _timestamps(frame, path)
    if len(frame) != 144 or not np.array_equal(times.to_numpy(), (inputs.timestamp + pd.Timedelta(minutes=10)).to_numpy()):
        raise ArtifactError(f"Controller/input target timestamp alignment failed in {path}.")
    c, d, u, g, w = [frame[n].to_numpy(float) for n in ["charge_kw", "discharge_kw", "curtailment_kw", "grid_export_kw", "wind_generation_kw"]]
    energy = frame.soc_percent.to_numpy(float) * 20
    before = np.r_[1000., energy[:-1]]
    if not np.allclose(w, np.maximum(0, inputs.actual_h1_kw), atol=1e-6, rtol=0):
        raise ArtifactError(f"Recorded wind differs from actual input targets in {path}.")
    if not np.allclose(frame.forecast_generation_kw, np.maximum(0, inputs.xgboost_h1_kw), atol=.001, rtol=0):
        raise ArtifactError(f"Recorded first-horizon forecast differs from source input in {path}.")
    if (frame.downside_forecast_kw < -1e-6).any() or (frame.downside_forecast_kw-frame.forecast_generation_kw > 1e-6).any():
        raise ArtifactError(f"Invalid downside forecast bounds in {path}.")
    if not np.allclose(w-c-u+d, g, atol=1e-6, rtol=0):
        raise ArtifactError(f"Power balance failed in {path}.")
    if not np.allclose(energy, before+(.95*c-d/.95)/6, atol=1e-5, rtol=0):
        raise ArtifactError(f"Battery stored-energy conservation failed in {path}.")
    if energy.min() < 800-1e-5 or energy.max() > 1800+1e-5:
        raise ArtifactError(f"Battery SOC outside 40–90% in {path}.")
    if min(c.min(), d.min(), u.min(), g.min()) < -1e-6 or max(c.max(), d.max()) > 1000+1e-5:
        raise ArtifactError(f"Invalid battery power, curtailment or nonnegative export in {path}.")
    if np.minimum(c, d).max() > 1e-5 or (c+u-w).max() > 1e-5:
        raise ArtifactError(f"Simultaneous charge/discharge or wind-availability violation in {path}.")
    charge_cap = np.minimum.reduce([frame.committed_charge_kw.to_numpy(float), w, np.full(len(frame), 1000.), np.maximum(0, 1800-before)/(.95*DT_HOURS)])
    discharge_cap = np.minimum.reduce([frame.committed_discharge_kw.to_numpy(float), np.full(len(frame), 1000.), np.maximum(0, before+.95*c*DT_HOURS-800)*.95/DT_HOURS])
    curtail_cap = np.minimum(frame.committed_curtailment_kw.to_numpy(float), np.maximum(0, w-c))
    if not (np.allclose(c, charge_cap, atol=1e-5, rtol=0) and np.allclose(d, discharge_cap, atol=1e-5, rtol=0) and np.allclose(u, curtail_cap, atol=1e-5, rtol=0)):
        raise ArtifactError(f"Actual actions do not match the frozen physical fallback in {path}.")
    if kind == "adaptive_one_sided":
        if (frame[[f"adaptive_margin_h{h}_kw" for h in range(1, 7)]] < 0).any().any() or not np.allclose(frame.downside_forecast_kw, np.maximum(0, frame.forecast_generation_kw-frame.adaptive_margin_h1_kw), atol=1e-6, rtol=0):
            raise ArtifactError(f"Invalid adaptive margins or first downside path in {path}.")
        try:
            newest = pd.to_datetime(frame.newest_residual_target, errors="raise")
        except (ValueError, TypeError) as error:
            raise ArtifactError(f"Invalid causal diagnostic targets in {path}.") from error
        if newest.isna().any() or not (newest.to_numpy() < inputs.timestamp.to_numpy()).all():
            raise ArtifactError(f"Residual target at or after decision time in {path}.")
    return frame


def get_replay(block_id, root=None):
    base = data_root(root)
    _check_block(block_id, base)
    source = base / f"data/processed/evaluation_block_{int(block_id)}.csv"
    inputs = validate_inputs(_csv(source), source)
    schedule_path = base/"results/evaluation_schedule.csv"
    if schedule_path.is_file():
        schedule = _csv(schedule_path)
        _require_columns(schedule, {"block_id", "evaluation_role", "start_timestamp", "end_timestamp", "forecast_origins"}, schedule_path)
        selected = schedule.loc[schedule.block_id.eq(int(block_id))]
        if len(selected) != 1 or selected.evaluation_role.iloc[0] != "evaluation":
            raise ArtifactError(f"Block {block_id} is not uniquely evaluation-designated in {schedule_path}.")
        try:
            start = pd.Timestamp(selected.start_timestamp.iloc[0])
            end = pd.Timestamp(selected.end_timestamp.iloc[0])
        except (TypeError, ValueError) as error:
            raise ArtifactError(f"Invalid schedule timestamps in {schedule_path}.") from error
        if inputs.timestamp.iloc[0] != start or inputs.timestamp.iloc[-1] != end or selected.forecast_origins.iloc[0] != 144:
            raise ArtifactError(f"Block {block_id} input timestamps/count do not match the original schedule.")
    traces = {}
    for kind in ["adaptive_one_sided", "fixed"]:
        path = base / "results/frozen_heldout" / RUN_NAME / kind / f"adaptive_charging_mpc_block_{int(block_id)}_weight_0p500.csv"
        traces[kind] = validate_trace(inputs, _csv(path), kind, path)
    wind = np.maximum(0, inputs.actual_h1_kw.to_numpy(float))
    traces["uncontrolled"] = pd.DataFrame({"timestamp": inputs.timestamp + pd.Timedelta(minutes=10), "wind_generation_kw": wind, "grid_export_kw": wind, "charge_kw": 0., "discharge_kw": 0., "curtailment_kw": 0., "soc_percent": np.nan})
    return ReplayBundle(inputs=inputs, traces=traces, block_id=int(block_id))


def interval_frame(block_id, kind, root=None):
    if kind not in CASES:
        raise ArtifactError(f"Unknown comparison case: {kind}")
    bundle = get_replay(block_id, root)
    frame = bundle.traces[kind].copy(deep=True)
    frame["decision_time"] = bundle.inputs.timestamp.to_numpy()
    frame["interval"] = np.arange(144)
    first = max(0, float(bundle.inputs.current_power_kw.iloc[0]))
    grid = frame.grid_export_kw.to_numpy(float)
    wind = frame.wind_generation_kw.to_numpy(float)
    frame["signed_grid_ramp_kw"] = np.diff(np.r_[first, grid])
    frame["absolute_grid_ramp_kw"] = np.abs(frame.signed_grid_ramp_kw)
    frame["wind_ramp_kw"] = np.diff(np.r_[first, wind])
    frame["uncontrolled_ramp_kw"] = np.abs(frame.wind_ramp_kw)
    frame["ramp_exceedance_kw"] = np.maximum(0, frame.absolute_grid_ramp_kw-RAMP_LIMIT_KW)
    frame["uncontrolled_exceedance_kw"] = np.maximum(0, frame.uncontrolled_ramp_kw-RAMP_LIMIT_KW)
    frame["exceedance_difference_kw"] = frame.ramp_exceedance_kw-frame.uncontrolled_exceedance_kw
    frame["ramp_violation"] = frame.absolute_grid_ramp_kw > VIOLATION_THRESHOLD_KW
    frame["uncontrolled_violation"] = frame.uncontrolled_ramp_kw > VIOLATION_THRESHOLD_KW
    frame["introduced_violation"] = frame.ramp_violation & ~frame.uncontrolled_violation
    frame["removed_violation"] = ~frame.ramp_violation & frame.uncontrolled_violation
    frame["battery_net_power_kw"] = frame.discharge_kw-frame.charge_kw
    frame["net_injection_kw"] = frame.battery_net_power_kw-frame.curtailment_kw
    frame["delta_net_injection_kw"] = np.diff(np.r_[0., frame.net_injection_kw])
    frame["energy_end_kwh"] = frame.soc_percent*20
    frame["energy_before_kwh"] = np.r_[1000., frame.energy_end_kwh.to_numpy()[:-1]] if kind != "uncontrolled" else np.nan
    frame["power_balance_error_kw"] = frame.wind_generation_kw-frame.charge_kw-frame.curtailment_kw+frame.discharge_kw-frame.grid_export_kw
    frame["energy_balance_error_kwh"] = frame.energy_end_kwh-frame.energy_before_kwh-(.95*frame.charge_kw-frame.discharge_kw/.95)*DT_HOURS if kind != "uncontrolled" else 0.
    frame["charge_kwh"] = frame.charge_kw*DT_HOURS
    frame["discharge_kwh"] = frame.discharge_kw*DT_HOURS
    frame["throughput_kwh"] = frame.charge_kwh+frame.discharge_kwh
    frame["conversion_loss_kwh"] = .05*frame.charge_kwh+(1/.95-1)*frame.discharge_kwh
    frame["export_kwh"] = frame.grid_export_kw*DT_HOURS
    frame["wind_kwh"] = frame.wind_generation_kw*DT_HOURS
    frame["curtailment_kwh"] = frame.curtailment_kw*DT_HOURS
    for total, values in [("throughput", "throughput_kwh"), ("loss", "conversion_loss_kwh"), ("export", "export_kwh"), ("curtailment", "curtailment_kwh")]:
        frame[f"cumulative_{total}_kwh"] = frame[values].cumsum()
    frame.attrs.update(controller=kind, block_id=int(block_id), provenance="Derived no-battery reference" if kind == "uncontrolled" else "Recorded frozen simulation trace")
    return frame


def energy_metrics(frame, upto=None):
    """Inclusive cursor totals; EFC is an AC-throughput proxy, not degradation."""
    view = frame if upto is None else frame.iloc[:int(upto)+1]
    if view.empty:
        raise ArtifactError("No intervals selected for energy accounting.")
    battery = not view.energy_end_kwh.isna().all()
    delta = float(view.energy_end_kwh.iloc[-1]-1000) if battery else 0.
    export = float(view.export_kwh.sum())
    throughput = float(view.throughput_kwh.sum())
    adjusted = export+(.95*delta if delta >= 0 else delta/.95) if battery else np.nan
    return {"intervals": len(view), "throughput_kwh": throughput, "conversion_losses_kwh": float(view.conversion_loss_kwh.sum()), "conversion_loss_kwh": float(view.conversion_loss_kwh.sum()), "charge_kwh": float(view.charge_kwh.sum()), "discharge_kwh": float(view.discharge_kwh.sum()), "export_kwh": export, "actual_export_kwh": export, "wind_kwh": float(view.wind_kwh.sum()), "curtailment_kwh": float(view.curtailment_kwh.sum()), "terminal_energy_delta_kwh": delta, "inventory_change_kwh": delta, "terminal_adjusted_export_kwh": adjusted, "efc_proxy": throughput/(2*CAPACITY_KWH), "equivalent_full_cycle_proxy": throughput/(2*CAPACITY_KWH), "energy_balance_residual_kwh": float(view.wind_kwh.sum()-export-view.curtailment_kwh.sum()-view.conversion_loss_kwh.sum()-delta), "ramp_violations": int(view.ramp_violation.sum()), "ramp_exceedance_kw": float(view.ramp_exceedance_kw.sum()), "final_soc_percent": float(view.soc_percent.iloc[-1]) if battery else np.nan}


def comparisons(root=None):
    totals = get_table("aggregate_metrics", root).set_index("controller")
    baseline = get_table("uncontrolled_wind_baseline", root)
    rows = []
    for kind in CASES:
        if kind == "uncontrolled":
            row = {"controller": kind, "label": CASES[kind], "ramp_violations": int(baseline.ramp_violations.sum()), "ramp_exceedance_kw": float(baseline.ramp_exceedance_kw.sum()), "throughput_kwh": 0., "conversion_losses_kwh": 0., "charge_kwh": 0., "discharge_kwh": 0., "export_kwh": float(baseline.wind_energy_kwh.sum()), "terminal_adjusted_export_kwh": np.nan, "curtailment_kwh": 0., "terminal_energy_delta_kwh": 0., "intervals": 7056, "transitions": 7056}
        else:
            row = totals.loc[kind].to_dict()
            row.update(controller=kind, label=CASES[kind])
        row["efc_proxy"] = row["throughput_kwh"]/(2*CAPACITY_KWH)
        rows.append(row)
    return pd.DataFrame(rows).set_index("controller")


def fixed_margins(root=None):
    path = data_root(root)/"results/multistep_uncertainty_calibration_split.csv"
    data = _csv(path)
    _require_columns(data, {"horizon_minutes", "calibration_quantile_kw"}, path)
    _finite(data, ["horizon_minutes", "calibration_quantile_kw"], path)
    if len(data) != 6 or set(data.horizon_minutes.astype(int)) != set(HORIZONS) or (data.calibration_quantile_kw < 0).any():
        raise ArtifactError(f"Invalid fixed six-horizon calibration margins in {path}.")
    return data.sort_values("horizon_minutes").calibration_quantile_kw.to_numpy(float)


def planning_frame(block_id, kind, step, root=None):
    if kind not in CASES or not 0 <= int(step) < 144:
        raise ArtifactError("Select a valid controller and decision step 0–143.")
    bundle = get_replay(block_id, root)
    step = int(step)
    row = bundle.inputs.iloc[step]
    nominal = np.maximum(0, [float(row[f"xgboost_h{h}_kw"]) for h in range(1, 7)])
    if kind == "adaptive_one_sided":
        margins = np.array([bundle.traces[kind].iloc[step][f"adaptive_margin_h{h}_kw"] for h in range(1, 7)], dtype=float)
    elif kind == "fixed":
        margins = fixed_margins(root)
    else:
        margins = np.full(6, np.nan)
    result = pd.DataFrame({"horizon_minutes": HORIZONS, "target_time": [row.timestamp+pd.Timedelta(minutes=h) for h in HORIZONS], "nominal_kw": nominal, "downside_kw": np.maximum(0, nominal-margins), "actual_kw": [float(row[f"actual_h{h}_kw"]) for h in range(1, 7)], "persistence_kw": [float(row[f"persistence_h{h}_kw"]) for h in range(1, 7)], "margin_kw": margins})
    result.attrs.update(decision_time=row.timestamp, controller=kind, provenance="Forecast scenarios reconstructed from recorded decision forecasts and recorded/calibrated margins; future actuals shown retrospectively; no planned actions or solver objectives logged")
    return result


def integrity_report(root=None):
    """Verify the exact manifest before following its recorded artifact paths."""
    base = data_root(root)
    path = base/"results/development_controller_freeze_manifest.json"
    result = {"expected_sha256": EXPECTED_FREEZE_SHA256, "actual_sha256": None, "manifest_match": False, "source_checks": [], "checked_files": 0, "status": "missing"}
    if not path.is_file():
        result["message"] = f"Missing local freeze manifest: {path}"
        return result
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    result["actual_sha256"] = actual
    if actual != EXPECTED_FREEZE_SHA256:
        result.update(status="mismatch", message="Freeze manifest SHA256 does not match; untrusted reference paths were not followed.")
        return result
    result["manifest_match"] = True
    manifest = json.loads(path.read_text(encoding="utf-8"))
    entries = list(manifest["source_files"].values()) + [entry for group in manifest["development_result_files"].values() for entry in group.values()]
    for entry in entries:
        item = base/entry["path"]
        found = hashlib.sha256(item.read_bytes()).hexdigest() if item.is_file() else None
        result["source_checks"].append({"path": entry["path"], "expected_sha256": entry["sha256"], "actual_sha256": found, "status": "pass" if found == entry["sha256"] else "missing" if found is None else "mismatch"})
    result["checked_files"] = len(entries)
    passed = all(item["status"] == "pass" for item in result["source_checks"])
    result.update(status="pass" if passed else "failed", message="Manifest and all 59 referenced frozen sources/development outputs match." if passed else "The manifest matches, but referenced artifacts are missing or mismatched.")
    return result


def validation_summary(root=None):
    base = data_root(root)
    paths = [base/"audits/research_completion_20261029/verification_evidence_final.json", base/"results/frozen_heldout/final_20261029/analysis_v2/validation.json"]
    for path in paths:
        if path.is_file():
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise ArtifactError(f"Invalid saved validation report {path}: {error}") from error
            return {"available": True, "path": str(path.relative_to(base)), "record": record, "status": record.get("status", "unknown"), "message": "Recorded prior validation evidence; loading a replay independently validates its current physical trace."}
    return {"available": False, "status": "missing", "record": {}, "message": "Local validation report is absent. Summary tables alone do not establish current source integrity."}


def environment_summary():
    packages = {}
    for name in ["streamlit", "plotly", "numpy", "pandas", "cvxpy", "highspy", "xgboost"]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "not installed"
    return {"python": sys.version.split()[0], "platform": platform.platform(), "packages": packages, "data_root": str(data_root()), "mode": "Historical replay / offline demonstration"}
