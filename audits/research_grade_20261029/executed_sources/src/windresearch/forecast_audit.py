"""Read-only forecasting and causal uncertainty audit of preserved predictions.

No fitting, controller selection or mutation of historical artifacts occurs here.
The 49-block sample is retrospective. Coverage is descriptive under temporal
dependence; one-sided prediction sets have an infinite upper endpoint.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ALPHA = 0.10
WINDOW = 144
POST_GAP_MINIMUM = 72
GAP_START = pd.Timestamp("2018-10-31 16:50:00")
STATIC_FLOORS_KW = np.array([
    358.379810, 504.728717, 571.614234,
    630.176420, 690.977755, 731.661882,
])
FEATURES = [
    "power_kw", "wind_speed", "wind_direction", "power_lag_10min",
    "power_lag_20min", "power_lag_30min", "power_lag_60min",
    "wind_lag_10min", "wind_lag_20min", "wind_lag_30min",
    "wind_lag_60min", "power_change_10min", "wind_change_10min",
    "power_mean_40min",
]
BASELINES = ("xgboost", "persistence", "local_linear")
METHODS = ("fixed_absolute_lower", "adaptive_signed_lower", "fixed_absolute_two_sided")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def conformal_quantile(values, alpha=ALPHA):
    """Finite-sample rank with no interpolation, matching frozen code."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("Expected finite, nonempty one-dimensional residuals")
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie strictly between zero and one")
    rank = int(math.ceil((len(values) + 1) * (1 - alpha)))
    if rank > len(values):
        raise ValueError("Insufficient samples for the requested conformal rank")
    return float(np.partition(values, rank - 1)[rank - 1])


def reconstruct_adaptive_margins(history, decisions, alpha=ALPHA, window=WINDOW,
                                 floors=None, post_gap_minimum=POST_GAP_MINIMUM,
                                 score="signed"):
    """Query six margins once per decision using STRICT target < decision.

    Defaults reproduce the frozen algorithm. Explicit alpha/window/floor
    arguments support separately labelled development-only sensitivity studies.
    "score='absolute'" is an explicit ablation, never the frozen adaptive method.
    Returns an N x 6 array and a long diagnostics DataFrame.
    """
    if not isinstance(window, (int, np.integer)) or window < 1:
        raise ValueError("window must be a positive integer")
    if post_gap_minimum < 0 or score not in {"signed", "absolute"}:
        raise ValueError("Invalid gap minimum or residual score")
    conformal_quantile(np.zeros(window), alpha)
    floors = STATIC_FLOORS_KW.copy() if floors is None else np.asarray(floors, dtype=float)
    if floors.shape != (6,) or not np.isfinite(floors).all() or (floors < 0).any():
        raise ValueError("floors must contain six finite nonnegative values")
    required = ["timestamp"] + [f"{kind}_h{h}_kw" for h in range(1, 7)
                                 for kind in ("xgboost", "actual")]
    missing = set(required) - set(history.columns)
    if missing:
        raise ValueError(f"Missing history columns: {sorted(missing)}")
    history = history[required].copy()
    history["timestamp"] = pd.to_datetime(history["timestamp"], errors="raise")
    history = history.sort_values("timestamp").reset_index(drop=True)
    if history.timestamp.isna().any() or history.timestamp.duplicated().any():
        raise ValueError("History requires unique, present forecast origins")
    if not np.isfinite(history.drop(columns="timestamp").to_numpy(dtype=float)).all():
        raise ValueError("Non-finite history forecasts or outcomes")
    decisions = pd.DatetimeIndex(pd.to_datetime(decisions, errors="raise"))
    if decisions.hasnans or decisions.tz is not None or history.timestamp.dt.tz is not None:
        raise ValueError("Use present, timezone-naive dataset-clock timestamps")
    origins = history.timestamp.to_numpy(dtype="datetime64[ns]")
    margins = np.empty((len(decisions), 6))
    records = []
    for h in range(1, 7):
        targets = origins + np.timedelta64(h * 10, "m")
        residuals = history[f"xgboost_h{h}_kw"].to_numpy() - history[f"actual_h{h}_kw"].to_numpy()
        if score == "absolute":
            residuals = np.abs(residuals)
        ends = np.searchsorted(targets, decisions.to_numpy(dtype="datetime64[ns]"), side="left")
        for i, end in enumerate(ends):
            if end < window:
                raise ValueError(f"Insufficient causal history at horizon {h}, decision {decisions[i]}")
            selected = slice(end - window, end)
            rolling = conformal_quantile(residuals[selected], alpha)
            post_gap = int(np.count_nonzero(origins[selected] >= np.datetime64(GAP_START, "ns")))
            fallback = bool(decisions[i] >= GAP_START and post_gap < post_gap_minimum)
            margin = floors[h - 1] if fallback else max(rolling, floors[h - 1])
            newest = pd.Timestamp(targets[end - 1])
            if newest >= decisions[i]:
                raise RuntimeError("Future/equal-time target admitted to residual history")
            margins[i, h - 1] = margin
            records.append({
                "decision_timestamp": decisions[i], "horizon_minutes": h * 10,
                "rolling_margin_kw": rolling, "static_floor_kw": floors[h - 1],
                "adaptive_margin_kw": margin, "post_gap_count": post_gap,
                "fallback_active": fallback, "newest_target": newest,
                "selected_count": window,
                "floor_binding": bool(rolling <= floors[h - 1] or fallback),
            })
    diagnostics = pd.DataFrame(records).sort_values(
        ["decision_timestamp", "horizon_minutes"]).reset_index(drop=True)
    return margins, diagnostics


def read_raw(path):
    raw = pd.read_csv(path)
    raw["timestamp"] = pd.to_datetime(raw["Date/Time"], format="%d %m %Y %H:%M", errors="raise")
    raw = raw.sort_values("timestamp").set_index("timestamp", verify_integrity=True)
    if raw.index.hasnans:
        raise ValueError("Missing raw timestamp")
    return raw


def raw_lookup(raw, times, column="LV ActivePower (kW)"):
    values = raw[column].reindex(pd.DatetimeIndex(times)).to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"Missing/nonfinite raw measurements for {column}")
    return values


def causal_linear_prediction(raw, decisions, horizon):
    """Parameter-free two-point trend: max(0, P_t+h(P_t-P_t-10))."""
    decisions = pd.DatetimeIndex(decisions)
    current = raw_lookup(raw, decisions)
    previous = raw_lookup(raw, decisions - pd.Timedelta(minutes=10))
    return np.maximum(0.0, current + horizon * (current - previous))


def load_inputs(root):
    root = Path(root)
    schedule = pd.read_csv(root / "results/evaluation_schedule.csv")
    blocks, all_blocks = [], []
    paths = [root / "results/evaluation_schedule.csv", root / "data/raw/T1.csv",
             root / "data/processed/wind_multistep_features.csv",
             root / "results/multistep_calibration_split.csv",
             root / "results/multistep_controller_development_split.csv",
             root / "results/multistep_mpc_validation_audited.csv",
             root / "results/multistep_uncertainty_calibration_split.csv",
             root / "results/development_controller_freeze_manifest.json",
             root / "configs/research_audit_v1.json"]
    for item in schedule.itertuples():
        path = root / f"data/processed/evaluation_block_{item.block_id}.csv"
        paths.append(path)
        block = pd.read_csv(path, parse_dates=["timestamp"])
        expected = pd.date_range(item.start_timestamp, periods=int(item.forecast_origins), freq="10min")
        if (len(block) != 144 or not np.array_equal(block.timestamp.to_numpy(), expected.to_numpy())
                or block.timestamp.iloc[-1] != pd.Timestamp(item.end_timestamp)):
            raise ValueError(f"Invalid scheduled block {item.block_id}")
        all_blocks.append(block)
        if item.evaluation_role == "evaluation":
            block = block.assign(block_id=int(item.block_id), segment_id=int(item.segment_id))
            blocks.append(block)
    calibration = pd.read_csv(paths[3], parse_dates=["timestamp"])
    dev = []
    for b in range(1, 19):
        path = root / f"data/processed/controller_development_blocks/development_block_{b}.csv"
        paths.append(path)
        dev.append(pd.read_csv(path, parse_dates=["timestamp"]))
    data = pd.concat(blocks, ignore_index=True)
    if len(blocks) != 49 or len(data) != 7056 or 6 in data.block_id.unique():
        raise ValueError("Expected the unchanged 49-block / 7,056-origin retrospective sample")
    if data.timestamp.duplicated().any():
        raise ValueError("Duplicate scored forecast origins")
    history = pd.concat([calibration] + dev + all_blocks, ignore_index=True)
    fixed = pd.read_csv(root / "results/multistep_uncertainty_calibration_split.csv")
    fixed = fixed.set_index("horizon_minutes").loc[[10, 20, 30, 40, 50, 60], "calibration_quantile_kw"].to_numpy()
    if fixed.shape != (6,) or not np.isfinite(fixed).all() or (fixed < 0).any():
        raise ValueError("Invalid fixed calibration margins")
    for h in range(1, 7):
        paths.append(root / f"models/wind_xgboost_h{h}.json")
    for name in ["build_wind_features.py", "prepare_multistep_ml_data.py", "train_multistep_xgboost.py",
                 "prepare_forecasting_data.py", "prepare_audited_validation.py",
                 "split_validation_calibration_development.py", "causal_one_sided_uncertainty.py",
                 "frozen_fixed_heldout.py", "frozen_adaptive_one_sided_heldout.py"]:
        paths.append(root / "scripts" / name)
    paths.extend([root / "src/windresearch/forecast_audit.py",
                  root / "scripts/run_forecast_uncertainty_audit_v1.py",
                  root / "tests/test_forecast_audit_v1.py"])
    return data, history, calibration, dev, fixed, read_raw(root / "data/raw/T1.csv"), paths


def forecast_records(data, raw):
    """One row per origin/horizon, with all three unselected forecast methods."""
    records = []
    times = pd.DatetimeIndex(data.timestamp)
    current = np.maximum(0, raw_lookup(raw, times))
    if not np.allclose(data.current_power_kw, current, rtol=1e-8, atol=1e-5):
        raise ValueError("Saved current power disagrees with raw nonnegative generation")
    for h in range(1, 7):
        targets = times + pd.Timedelta(minutes=h * 10)
        actual = np.maximum(0, raw_lookup(raw, targets))
        previous = np.maximum(0, raw_lookup(raw, targets - pd.Timedelta(minutes=10)))
        if not np.allclose(data[f"actual_h{h}_kw"], actual, rtol=1e-8, atol=1e-5):
            raise ValueError(f"Saved h{h} outcomes disagree with raw target-time lookup")
        persistence = data[f"persistence_h{h}_kw"].to_numpy()
        if not np.allclose(persistence, current, rtol=1e-8, atol=1e-5):
            raise ValueError("Persistence is not current observed generation")
        item = data[["timestamp", "block_id", "segment_id"]].copy()
        item["target_timestamp"] = targets
        item["horizon_minutes"] = h * 10
        item["actual_kw"] = actual
        item["observed_target_ramp_kw"] = np.abs(actual - previous)
        item["rapid_change"] = np.abs(actual - previous) > 200.001
        item["xgboost_kw"] = data[f"xgboost_h{h}_kw"].to_numpy()
        item["persistence_kw"] = persistence
        item["local_linear_kw"] = causal_linear_prediction(raw, times, h)
        if not np.isfinite(item[[f"{b}_kw" for b in BASELINES]]).all().all():
            raise ValueError("Non-finite forecast")
        for baseline in BASELINES:
            item[f"{baseline}_error_kw"] = item[f"{baseline}_kw"] - actual
        records.append(item)
    return pd.concat(records, ignore_index=True).sort_values(["timestamp", "horizon_minutes"])


def summarise_forecasts(records, group_columns):
    rows = []
    for key, frame in records.groupby(group_columns, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        identity = dict(zip(group_columns, key))
        for baseline in BASELINES:
            error = frame[f"{baseline}_error_kw"].to_numpy()
            row = {**identity, "baseline": baseline, "n": len(error),
                   "mae_kw": np.abs(error).mean(), "rmse_kw": np.sqrt(np.mean(error ** 2)),
                   "bias_forecast_minus_actual_kw": error.mean(),
                   "error_std_population_kw": error.std(ddof=0)}
            for q in [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]:
                row[f"error_q{int(q * 100):02d}_kw"] = np.quantile(error, q)
            rows.append(row)
    return pd.DataFrame(rows)


def uncertainty_records(predictions, margins, diagnostics, data, fixed):
    if np.asarray(margins).shape != (len(data), 6):
        raise ValueError("Expected one six-horizon margin vector per scored origin")
    result = predictions.copy()
    result["fixed_margin_kw"] = result.horizon_minutes.map(dict(zip(range(10, 61, 10), fixed)))
    adaptive_lookup = diagnostics.rename(columns={"decision_timestamp": "timestamp"})
    result = result.merge(adaptive_lookup, on=["timestamp", "horizon_minutes"], validate="one_to_one")
    nominal = np.maximum(0.0, result.xgboost_kw)
    result["nominal_kw"] = nominal
    result["fixed_lower_kw"] = np.maximum(0, nominal - result.fixed_margin_kw)
    result["adaptive_lower_kw"] = np.maximum(0, nominal - result.adaptive_margin_kw)
    result["fixed_two_sided_upper_kw"] = nominal + result.fixed_margin_kw
    result["fixed_lower_covered"] = result.actual_kw >= result.fixed_lower_kw
    result["adaptive_lower_covered"] = result.actual_kw >= result.adaptive_lower_kw
    result["fixed_two_sided_covered"] = (result.fixed_lower_covered
                                         & (result.actual_kw <= result.fixed_two_sided_upper_kw))
    result["fixed_lower_offset_kw"] = nominal - result.fixed_lower_kw
    result["adaptive_lower_offset_kw"] = nominal - result.adaptive_lower_kw
    result["fixed_two_sided_width_kw"] = result.fixed_two_sided_upper_kw - result.fixed_lower_kw
    return result


def summarise_coverage(records, group_columns):
    rows = []
    for key, frame in records.groupby(group_columns, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        identity = dict(zip(group_columns, key))
        for method, prefix in zip(METHODS, ("fixed_lower", "adaptive_lower", "fixed_two_sided")):
            coverage = float(frame[f"{prefix}_covered"].mean())
            positive = frame.actual_kw > 0
            lower = frame.adaptive_lower_kw if method == "adaptive_signed_lower" else frame.fixed_lower_kw
            offset = frame.adaptive_lower_offset_kw if method == "adaptive_signed_lower" else frame.fixed_lower_offset_kw
            rows.append({**identity, "method": method, "n": len(frame), "coverage": coverage,
                         "reference_coverage": 0.9, "coverage_minus_reference_percentage_points": (coverage - 0.9) * 100,
                         "absolute_calibration_error_percentage_points": abs(coverage - 0.9) * 100,
                         "positive_generation_n": int(positive.sum()),
                         "positive_generation_coverage": frame.loc[positive, f"{prefix}_covered"].mean(),
                         "zero_generation_fraction": float((~positive).mean()),
                         "active_lower_bound_fraction": float((lower > 0).mean()),
                         "mean_nominal_minus_lower_kw": float(offset.mean()),
                         "mean_prediction_set_width_kw": (float(frame.fixed_two_sided_width_kw.mean())
                             if method == "fixed_absolute_two_sided" else float("inf")),
                         "upper_endpoint": "finite" if method == "fixed_absolute_two_sided" else "+infinity",
                         "floor_binding_fraction": (float(frame.floor_binding.mean())
                             if method == "adaptive_signed_lower" else np.nan),
                         "fallback_fraction": (float(frame.fallback_active.mean())
                             if method == "adaptive_signed_lower" else np.nan)})
    return pd.DataFrame(rows)


def audit_chronology_features(root, raw, calibration, development):
    root = Path(root)
    source = pd.read_csv(root / "data/processed/wind_multistep_features.csv", parse_dates=["timestamp"])
    times = pd.DatetimeIndex(source.timestamp)
    expected = {"power_kw": raw_lookup(raw, times),
                "wind_speed": raw_lookup(raw, times, "Wind Speed (m/s)"),
                "wind_direction": raw_lookup(raw, times, next(c for c in raw if c.startswith("Wind Direction")))}
    latest_offsets = {"power_kw": 0, "wind_speed": 0, "wind_direction": 0}
    for lag in [10, 20, 30, 60]:
        expected[f"power_lag_{lag}min"] = raw_lookup(raw, times - pd.Timedelta(minutes=lag))
        expected[f"wind_lag_{lag}min"] = raw_lookup(raw, times - pd.Timedelta(minutes=lag), "Wind Speed (m/s)")
        latest_offsets[f"power_lag_{lag}min"] = -lag
        latest_offsets[f"wind_lag_{lag}min"] = -lag
    expected["power_change_10min"] = expected["power_kw"] - expected["power_lag_10min"]
    expected["wind_change_10min"] = expected["wind_speed"] - expected["wind_lag_10min"]
    expected["power_mean_40min"] = np.mean([expected["power_kw"]] +
        [expected[f"power_lag_{lag}min"] for lag in [10, 20, 30]], axis=0)
    feature_rows = []
    for name in FEATURES:
        stored = source[name].to_numpy()
        matched = np.isclose(stored, expected[name], atol=1e-7, rtol=1e-9)
        feature_rows.append({"feature": name, "n": len(source), "mismatches": int((~matched).sum()),
                             "max_abs_difference": float(np.abs(stored - expected[name]).max()),
                             "latest_measurement_offset_minutes": latest_offsets.get(name, 0)})
    target_checks = []
    for h in range(1, 7):
        target = raw_lookup(raw, times + pd.Timedelta(minutes=h * 10))
        matched = np.isclose(source[f"target_h{h}_kw"], target, atol=1e-7, rtol=1e-9)
        target_checks.append({"horizon_minutes": h * 10, "mismatches": int((~matched).sum())})
    boundary = pd.Timestamp("2018-09-09 02:50")
    test = pd.Timestamp("2018-11-05 15:10")
    last = source.timestamp + pd.Timedelta(minutes=60)
    train = source[last < boundary]
    validation = source[(source.timestamp >= boundary) & (last < test)]
    first_dev = min(frame.timestamp.min() for frame in development)
    overlap = []
    for frame in development:
        for decision in frame.timestamp:
            for h in range(1, 7):
                unavailable = calibration.timestamp + pd.Timedelta(minutes=h * 10) >= decision
                if unavailable.any():
                    overlap.append({"decision_timestamp": decision, "horizon_minutes": h * 10,
                                    "calibration_labels_not_strictly_past": int(unavailable.sum())})
    train_code = (root / "scripts/train_multistep_xgboost.py").read_text(encoding="utf-8")
    report = {
        "train_origins": len(train), "validation_origins_before_prediction_audit": len(validation),
        "train_latest_h6_target": str((train.timestamp + pd.Timedelta(minutes=60)).max()),
        "validation_latest_h6_target": str((validation.timestamp + pd.Timedelta(minutes=60)).max()),
        "training_target_cutoff_strict": bool((train.timestamp + pd.Timedelta(minutes=60)).max() < boundary),
        "validation_target_cutoff_strict": bool((validation.timestamp + pd.Timedelta(minutes=60)).max() < test),
        "active_training_script_contains_shuffle_or_random_split": any(token in train_code for token in
            ["train_test_split", ".sample(", "shuffle=", "np.random.permutation"]),
        "feature_audit_rows": len(source), "feature_mismatches": sum(r["mismatches"] for r in feature_rows),
        "source_target_checks": target_checks,
        "first_development_decision": str(first_dev),
        "calibration_latest_h6_target": str(calibration.timestamp.max() + pd.Timedelta(minutes=60)),
        "calibration_development_boundary_strict": bool(calibration.timestamp.max() + pd.Timedelta(minutes=60) < first_dev),
        "affected_development_decisions": len(set(r["decision_timestamp"] for r in overlap)),
        "unavailable_calibration_label_decision_pairs": sum(r["calibration_labels_not_strictly_past"] for r in overlap),
        "raw_negative_power_count": int((raw["LV ActivePower (kW)"] < 0).sum()),
        "source_feature_negative_power_count": int((source.power_kw < 0).sum()),
        "feature_convention": "raw signed measurements; no future feature values",
        "evaluation_convention": "physical generation and saved forecasts clipped at zero",
    }
    return report, pd.DataFrame(feature_rows), pd.DataFrame(overlap), source


def verify_models(root, source, data):
    """Inference only; existing JSON models are never fitted or saved."""
    from xgboost import XGBRegressor
    features = source.set_index("timestamp").reindex(pd.DatetimeIndex(data.timestamp))[FEATURES]
    if features.isna().any().any():
        raise ValueError("Missing features for saved forecast origins")
    rows = []
    for h in range(1, 7):
        model = XGBRegressor()
        model.load_model(Path(root) / f"models/wind_xgboost_h{h}.json")
        current = np.maximum(0, model.predict(features))
        difference = np.abs(current - data[f"xgboost_h{h}_kw"].to_numpy())
        rows.append({"horizon_minutes": h * 10, "n": len(data),
                     "max_abs_serialization_difference_kw": float(difference.max()),
                     "within_0p001_kw": bool((difference <= 0.001).all())})
    return pd.DataFrame(rows)


def verify_frozen_margins(root, history, data, margins):
    spec = importlib.util.spec_from_file_location("_readonly_frozen_uncertainty",
        Path(root) / "scripts/causal_one_sided_uncertainty.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.CausalAdaptiveUncertainty(history)
    maximum = 0.0
    for i, decision in enumerate(data.timestamp):
        frozen, diagnostics = original.margins(decision)
        maximum = max(maximum, float(np.abs(frozen - margins[i]).max()))
        if not all(item["newest_target"] < decision for item in diagnostics):
            raise RuntimeError("Frozen module admitted a non-past target")
    if maximum != 0:
        raise ValueError(f"Reconstructed margins differ from frozen module: {maximum}")
    return {"decisions_checked": len(data), "horizon_margins_checked": len(data) * 6,
            "max_abs_difference_kw": maximum, "strict_newest_target_check": True}


def _save_csv(frame, path):
    with Path(path).open("x", encoding="utf-8", newline="") as stream:
        frame.to_csv(stream, index=False)


def _save_json(value, path):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, default=str, allow_nan=False)


def make_figures(predictions, forecast_summary, intervals, coverage_blocks, figure_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"xgboost": "#0072B2", "persistence": "#D55E00", "local_linear": "#009E73"}
    labels = {"xgboost": "Saved XGBoost", "persistence": "Persistence", "local_linear": "Causal local trend"}
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "savefig.facecolor": "white", "pdf.fonttype": 42})

    def save(fig, name):
        fig.tight_layout()
        for extension in ["png", "pdf"]:
            target = Path(figure_dir) / f"{name}.{extension}"
            if target.exists():
                raise FileExistsError(target)
            fig.savefig(target, dpi=300, bbox_inches="tight")
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    for baseline in BASELINES:
        frame = forecast_summary[forecast_summary.baseline.eq(baseline)]
        for ax, metric, label in zip(axes, ["mae_kw", "rmse_kw"], ["MAE (kW)", "RMSE (kW)"]):
            ax.plot(frame.horizon_minutes, frame[metric], marker="o", color=colors[baseline], label=labels[baseline])
            ax.set(xlabel="Forecast horizon (minutes)", ylabel=label, xticks=range(10, 61, 10))
            ax.grid(alpha=0.2)
    axes[0].legend(frameon=False)
    fig.suptitle("Retrospective forecast comparison: 49 original blocks, no model fitting")
    save(fig, "forecast_by_horizon")

    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    for h, ax in enumerate(axes.flat, start=1):
        frame = predictions[predictions.horizon_minutes.eq(h * 10)]
        for baseline in BASELINES:
            ax.hist(frame[f"{baseline}_error_kw"], bins=70, histtype="step", density=True,
                    color=colors[baseline], label=labels[baseline], linewidth=1.3)
        ax.set(title=f"{h * 10}-minute horizon", xlabel="Forecast minus actual (kW)", ylabel="Density")
        ax.set_yscale("log")
        ax.axvline(0, color="#444444", linewidth=0.7)
    axes.flat[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Full-range residual distributions (log density; no tail removal)")
    save(fig, "residual_distributions")

    fig, axes = plt.subplots(2, 3, figsize=(12, 7), sharey=True)
    for h, ax in enumerate(axes.flat, start=1):
        frame = coverage_blocks[coverage_blocks.horizon_minutes.eq(h * 10)]
        for method, color, label in zip(METHODS, ["#0072B2", "#009E73", "#CC79A7"],
                                       ["Fixed lower", "Adaptive lower", "Fixed two-sided"]):
            subset = frame[frame.method.eq(method)]
            for j, (_, segment) in enumerate(subset.groupby("segment_id")):
                ax.plot(segment.block_id, segment.coverage, color=color,
                        label=label if j == 0 else None, linewidth=1)
        for boundary in sorted(frame.groupby("segment_id").block_id.min().to_numpy())[1:]:
            ax.axvline(boundary - 0.5, color="#AAAAAA", linewidth=0.6, linestyle=":")
        ax.axhline(0.9, color="#444444", linestyle="--", linewidth=0.8)
        ax.set(title=f"{h * 10}-minute horizon", xlabel="Original block ID", ylabel="Empirical coverage", ylim=(0, 1.02))
    axes.flat[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Coverage stability; 90% is a reference, not an established guarantee")
    save(fig, "coverage_stability")

    fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True)
    for ax, h in zip(axes, [10, 60]):
        frame = intervals[(intervals.block_id.eq(1)) & intervals.horizon_minutes.eq(h)]
        ax.plot(frame.target_timestamp, frame.actual_kw, color="#202020", label="Observed generation", linewidth=1)
        ax.plot(frame.target_timestamp, frame.nominal_kw, color="#0072B2", label="Nominal XGBoost", linewidth=1)
        ax.plot(frame.target_timestamp, frame.fixed_lower_kw, color="#D55E00", label="Fixed lower", linewidth=1)
        ax.plot(frame.target_timestamp, frame.adaptive_lower_kw, color="#009E73", label="Adaptive lower", linewidth=1)
        ax.set(title=f"First retained block, {h}-minute horizon (predefined illustration)", ylabel="Power (kW)")
        ax.grid(alpha=0.2)
    axes[0].legend(frameon=False, ncol=2)
    axes[1].set_xlabel("Target timestamp (dataset clock; timezone unverified)")
    fig.autofmt_xdate()
    fig.suptitle("Downside scenarios; one-sided sets extend to +infinity, not to the nominal curve")
    save(fig, "lower_bound_examples")


def run_forecast_audit(root, result_dir, figure_dir):
    """Compute first, then exclusively create all new artifacts. No originals written."""
    root, result_dir, figure_dir = Path(root), Path(result_dir), Path(figure_dir)
    for path in [result_dir, figure_dir]:
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing audit directory: {path}")
    data, history, calibration, development, fixed, raw, paths = load_inputs(root)
    before = {str(p.relative_to(root)).replace("\\", "/"): sha256(p) for p in paths}
    expected_manifest = "b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a"
    if before["results/development_controller_freeze_manifest.json"] != expected_manifest:
        raise ValueError("Frozen manifest hash mismatch")
    predictions = forecast_records(data, raw)
    margins, diagnostics = reconstruct_adaptive_margins(history, data.timestamp)
    intervals = uncertainty_records(predictions, margins, diagnostics, data, fixed)
    chronology, feature_table, overlap, source = audit_chronology_features(root, raw, calibration, development)
    model_verification = verify_models(root, source, data)
    frozen_verification = verify_frozen_margins(root, history, data, margins)
    if chronology["feature_mismatches"] or any(c["mismatches"] for c in chronology["source_target_checks"]):
        raise ValueError("Raw feature/target reconstruction failed")
    if not model_verification.within_0p001_kw.all():
        raise ValueError("Existing models do not reproduce saved forecasts within 0.001 kW")
    calibration_rows = []
    for h in range(1, 7):
        residual = calibration[f"xgboost_h{h}_kw"] - calibration[f"actual_h{h}_kw"]
        recomputed = conformal_quantile(np.abs(residual))
        if not np.isclose(recomputed, fixed[h - 1], atol=1e-6, rtol=0):
            raise ValueError("Preserved fixed calibration quantile reconstruction failed")
        calibration_rows.append({"horizon_minutes": h * 10, "n": len(calibration),
                                 "fixed_absolute_margin_kw": fixed[h - 1],
                                 "recomputed_absolute_margin_kw": recomputed,
                                 "signed_q90_kw": conformal_quantile(residual),
                                 "frozen_floor_kw": STATIC_FLOORS_KW[h - 1]})
    forecast_summary = summarise_forecasts(predictions, ["horizon_minutes"])
    coverage_summary = summarise_coverage(intervals, ["horizon_minutes"])
    coverage_blocks = summarise_coverage(intervals, ["block_id", "segment_id", "horizon_minutes"])
    frames = {
        "forecast_predictions": predictions,
        "forecast_horizon_metrics": forecast_summary,
        "forecast_rapid_change_metrics": summarise_forecasts(predictions, ["rapid_change", "horizon_minutes"]),
        "forecast_block_metrics": summarise_forecasts(predictions, ["block_id", "segment_id", "horizon_minutes"]),
        "forecast_segment_metrics": summarise_forecasts(predictions, ["segment_id", "horizon_minutes"]),
        "uncertainty_intervals_and_causal_diagnostics": intervals,
        "coverage_horizon_metrics": coverage_summary,
        "coverage_rapid_change_metrics": summarise_coverage(intervals, ["rapid_change", "horizon_minutes"]),
        "coverage_block_metrics": coverage_blocks,
        "coverage_segment_metrics": summarise_coverage(intervals, ["segment_id", "horizon_minutes"]),
        "feature_timestamp_audit": feature_table,
        "calibration_development_boundary_overlap": overlap,
        "model_inference_verification": model_verification,
        "calibration_margin_reconstruction": pd.DataFrame(calibration_rows),
    }
    after = {name: sha256(root / name) for name in before}
    if before != after:
        raise RuntimeError("Protected input bytes changed during audit")
    summary = {
        "interpretation": "Retrospective descriptive audit of unchanged 49-block evaluation; not confirmatory independent testing",
        "seed": 20261029, "scored_origins": len(data), "scored_horizon_pairs": len(predictions),
        "excluded_development_block": 6, "fitting_or_hyperparameter_selection": "none",
        "chronology_and_features": chronology, "frozen_margin_verification": frozen_verification,
        "strict_target_eligibility_all_pass": bool((intervals.newest_target < intervals.timestamp).all()),
        "adaptive_floor_binding_fraction": float(intervals.floor_binding.mean()),
        "adaptive_fallback_fraction": float(intervals.fallback_active.mean()),
        "local_linear_prediction_max_kw": float(predictions.local_linear_kw.max()),
        "local_linear_definition": "max(0, raw_power(t) + h * (raw_power(t) - raw_power(t-10min))); h=1..6",
        "local_linear_limit": "No rated-power cap: rated power has not been established; extrapolation can be physically implausible",
        "rapid_change_definition": "abs(nonnegative actual target power - actual target-minus-10min power) > 200.001 kW; offline scoring only",
        "one_sided_set": "[lower,+infinity); width is infinite; finite nominal-minus-lower offset is not interval width",
        "coverage_reference": "0.90 is a descriptive calibration reference. Fixed absolute lower and floored rolling signed lower are not established 90% one-sided procedures",
        "coverage_limitations": "Serial dependence, overlapping horizon targets, distribution shift, floor/fallback and retrospective inspection preclude an asserted finite-sample coverage guarantee",
        "intervals_not_simultaneous": "Horizonwise empirical coverage; not simultaneous six-horizon coverage",
        "calibration_floor_provenance": "Frozen signed floors differ from current calibration signed 90% quantiles; historical derivation unresolved and preserved",
        "protected_inputs_unchanged": True,
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        "numpy": np.__version__, "pandas": pd.__version__},
        "input_sha256": before,
    }
    result_dir.mkdir(parents=True, exist_ok=False)
    figure_dir.mkdir(parents=True, exist_ok=False)
    for name, frame in frames.items():
        _save_csv(frame, result_dir / f"{name}.csv")
    make_figures(predictions, forecast_summary, intervals, coverage_blocks, figure_dir)
    summary["output_sha256"] = {str(p.relative_to(root)).replace("\\", "/"): sha256(p)
                                for folder in [result_dir, figure_dir] for p in sorted(folder.glob("*"))}
    _save_json(summary, result_dir / "audit_summary.json")
    return summary
