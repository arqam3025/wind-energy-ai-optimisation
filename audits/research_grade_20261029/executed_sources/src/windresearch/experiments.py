"""Saved-data controller comparisons; no forecasting models are fitted here."""
from __future__ import annotations

from dataclasses import asdict, replace
from functools import lru_cache
import hashlib
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd

from .mpc import MPCConfig, TwoStageMPC, realise
from .protocol import require_static_calibration_available

ROOT = Path(__file__).resolve().parents[2]
CASES = ("uncontrolled", "persistence_nominal", "xgboost_nominal", "fixed_margin",
         "adaptive_one_sided", "perfect_forecast_oracle")
FLOORS = np.array([358.379810, 504.728717, 571.614234, 630.176420, 690.977755, 731.661882])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=2)
def history_frames(period: str) -> pd.DataFrame:
    frames = [pd.read_csv(ROOT / "results/multistep_calibration_split.csv", parse_dates=["timestamp"])]
    frames += [pd.read_csv(ROOT / f"data/processed/controller_development_blocks/development_block_{b}.csv",
                          parse_dates=["timestamp"]) for b in range(1, 19)]
    if period == "evaluation":
        schedule = pd.read_csv(ROOT / "results/evaluation_schedule.csv")
        frames += [pd.read_csv(ROOT / f"data/processed/evaluation_block_{b}.csv", parse_dates=["timestamp"])
                   for b in schedule.block_id]
    elif period != "development":
        raise ValueError(f"Unknown period: {period}")
    return pd.concat(frames, ignore_index=True)


def block_path(period: str, block: int) -> Path:
    return ROOT / (f"data/processed/evaluation_block_{block}.csv" if period == "evaluation" else
                   f"data/processed/controller_development_blocks/development_block_{block}.csv")


def validate_input(frame: pd.DataFrame, period: str, block: int) -> None:
    if frame.empty or frame.timestamp.duplicated().any() or not frame.timestamp.is_monotonic_increasing:
        raise ValueError("Empty, duplicated or unsorted forecast origins")
    if not frame.timestamp.diff().iloc[1:].eq(pd.Timedelta(minutes=10)).all():
        raise ValueError("Forecast origins are not ten-minute aligned")
    required = ["current_power_kw"] + [f"{kind}_h{h}_kw" for h in range(1, 7)
        for kind in ("actual", "xgboost", "persistence")]
    if not np.isfinite(frame[required].to_numpy(float)).all():
        raise ValueError("Non-finite saved forecasts or observations")
    if not np.allclose(frame.actual_h1_kw.iloc[:-1], frame.current_power_kw.iloc[1:], atol=.001, rtol=0):
        raise ValueError("Actual h1 targets do not align with next origin observations")
    calibration = pd.read_csv(ROOT / "results/multistep_calibration_split.csv", parse_dates=["timestamp"])
    require_static_calibration_available(calibration, frame.timestamp.iloc[0])
    if period == "evaluation":
        schedule = pd.read_csv(ROOT / "results/evaluation_schedule.csv")
        eligible = schedule.loc[schedule.evaluation_role.eq("evaluation"), "block_id"].tolist()
        if block not in eligible or block == 6:
            raise ValueError("Block is not eligible for the retrospective evaluation comparison")


@lru_cache(maxsize=48)
def _engine(config: MPCConfig) -> TwoStageMPC:
    return TwoStageMPC(config)


def margins_for(frame: pd.DataFrame, case: str, period: str, alpha: float) -> tuple[np.ndarray, pd.DataFrame]:
    if case == "fixed_margin":
        table = pd.read_csv(ROOT / "results/multistep_uncertainty_calibration_split.csv").sort_values("horizon_minutes")
        return np.tile(table.calibration_quantile_kw.to_numpy(float), (len(frame), 1)), pd.DataFrame()
    if case == "adaptive_one_sided":
        from .forecast_audit import reconstruct_adaptive_margins
        return reconstruct_adaptive_margins(history_frames(period), frame.timestamp, alpha=alpha)
    if case == "adaptive_floors_only":
        return np.tile(FLOORS, (len(frame), 1)), pd.DataFrame()
    return np.zeros((len(frame), 6)), pd.DataFrame()


def run_block(case: str, frame: pd.DataFrame, config: MPCConfig, period: str, block: int,
              alpha: float = .1) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], pd.DataFrame]:
    """Execute first actions only; an oracle is explicitly isolated at forecast construction."""
    validate_input(frame, period, block)
    if case not in CASES + ("adaptive_floors_only",):
        raise ValueError(f"Unknown controller case: {case}")
    config = replace(config, risk_weight=0.0) if case in (
        "persistence_nominal", "xgboost_nominal", "perfect_forecast_oracle") else config
    margins, diagnostics = margins_for(frame, case, period, alpha)
    if not diagnostics.empty and not (pd.to_datetime(diagnostics.newest_target) < pd.to_datetime(diagnostics.decision_timestamp)).all():
        raise ValueError("Uncertainty residual target is not strictly before decision time")
    energy, previous_battery = config.initial_energy, 0.0
    previous_export = max(0., float(frame.current_power_kw.iloc[0]))
    engine = None if case == "uncontrolled" else _engine(config)
    records, plans = [], []
    start = perf_counter()
    for index, row in enumerate(frame.itertuples(index=False)):
        nominal_type = "persistence" if case == "persistence_nominal" else "xgboost"
        if case == "perfect_forecast_oracle":
            nominal_type = "actual"  # Explicit retrospective, non-deployable perfect-information benchmark.
        nominal = np.maximum(0, np.array([getattr(row, f"{nominal_type}_h{h}_kw")
                                          for h in range(1, config.horizon + 1)]))
        old_energy, old_export = energy, previous_export
        decision_start = perf_counter()
        if engine is None:
            decision = {"committed_charge_kw": 0., "committed_discharge_kw": 0., "committed_curtailment_kw": 0.}
            physical = {"wind_generation_kw": max(0., row.actual_h1_kw), "charge_kw": 0., "discharge_kw": 0.,
                        "curtailment_kw": 0., "grid_export_kw": max(0., row.actual_h1_kw),
                        "energy_kwh": np.nan, "soc_percent": np.nan}
        else:
            decision = engine.decide(nominal, margins[index, :config.horizon], energy, previous_export, previous_battery)
            # The actual first target is accessed for execution only after commands have been fixed.
            physical = realise(decision, float(row.actual_h1_kw), energy, config)
            energy = physical["energy_kwh"]
            for plan in decision["plans"]:
                plans.append({"block_id": block, "controller": case, "decision_timestamp": row.timestamp, **plan})
        previous_export = physical["grid_export_kw"]
        previous_battery = physical["discharge_kw"] - physical["charge_kw"]
        ramp = abs(previous_export - old_export)
        record = {"block_id": block, "controller": case, "decision_timestamp": row.timestamp,
            "timestamp": row.timestamp + pd.Timedelta(minutes=10), "initial_energy_kwh": old_energy if engine else np.nan,
            "forecast_generation_kw": float(nominal[0]),
            "downside_forecast_kw": float(max(0, nominal[0] - margins[index, 0])),
            **{k: decision[k] for k in ("committed_charge_kw", "committed_discharge_kw", "committed_curtailment_kw")},
            **physical, "grid_ramp_kw": ramp, "ramp_exceedance_kw": max(0., ramp - config.ramp_limit_kw),
            "ramp_violation": int(ramp > config.ramp_limit_kw + .001),
            "reference_200kw_exceedance_kw": max(0., ramp - 200.), "reference_200kw_violation": int(ramp > 200.001),
            "decision_wall_seconds": perf_counter() - decision_start}
        if engine:
            for stage in ("stage1", "stage2"):
                record.update({f"{stage}_{key}": value for key, value in decision[stage].items()})
            record["achieved_primary_objective"] = decision["achieved_primary"]
            record["max_constraint_residual"] = decision["max_constraint_residual"]
        records.append(record)
    trace = pd.DataFrame(records)
    metrics = validate_and_measure(trace, frame, config, case)
    metrics.update(block_id=block, controller=case, period=period, alpha=alpha,
                   block_wall_seconds=perf_counter() - start, initial_soc_percent=config.initial_soc_percent,
                   solver_failures=0, intervals=len(frame), horizon=config.horizon)
    return trace, pd.DataFrame(plans), metrics, diagnostics


def validate_and_measure(trace: pd.DataFrame, frame: pd.DataFrame, config: MPCConfig,
                         controller: str) -> dict[str, Any]:
    c = config
    wind, charge, discharge, curtail, export = [trace[name].to_numpy(float) for name in
        ("wind_generation_kw", "charge_kw", "discharge_kw", "curtailment_kw", "grid_export_kw")]
    if not np.isfinite(np.r_[wind, charge, discharge, curtail, export]).all():
        raise ValueError("Non-finite physical trace")
    if not np.array_equal(pd.to_datetime(trace.timestamp).to_numpy(),
                           (frame.timestamp + pd.Timedelta(minutes=10)).to_numpy()):
        raise ValueError("Executed target timestamps are misaligned")
    if not np.allclose(wind, np.maximum(0, frame.actual_h1_kw), atol=1e-6, rtol=0):
        raise ValueError("Execution wind differs from saved target observation")
    if min(charge.min(), discharge.min(), curtail.min(), export.min()) < -1e-5:
        raise ValueError("Negative physical power")
    if max(charge.max(), discharge.max()) > c.max_power_kw + 1e-5 or np.any(charge * discharge > 1e-3):
        raise ValueError("Power rating or simultaneous charging/discharging violated")
    if not np.allclose(wind - charge - curtail + discharge, export, atol=1e-5, rtol=0):
        raise ValueError("AC power balance violated")
    if np.any(charge + curtail > wind + 1e-5):
        raise ValueError("Charging/curtailment exceeds wind availability")
    charge_energy, discharge_energy = charge.sum() * c.dt_hours, discharge.sum() * c.dt_hours
    losses = (1 - c.eta_charge) * charge_energy + (1 / c.eta_discharge - 1) * discharge_energy
    battery = controller != "uncontrolled"
    if battery:
        expected = c.initial_energy + np.cumsum(c.eta_charge * charge * c.dt_hours - discharge * c.dt_hours / c.eta_discharge)
        if not np.allclose(expected, trace.energy_kwh, atol=1e-4, rtol=0):
            raise ValueError("DC battery energy balance violated")
        violations = int(np.count_nonzero((expected < c.min_energy - 1e-4) | (expected > c.max_energy + 1e-4)))
        if violations:
            raise ValueError("Hard SOC bounds violated")
        inventory = float(expected[-1] - c.initial_energy)
        adjustment = c.eta_discharge * inventory if inventory >= 0 else inventory / c.eta_charge
        final_soc, min_soc, max_soc = float(trace.soc_percent.iloc[-1]), float(trace.soc_percent.min()), float(trace.soc_percent.max())
    else:
        inventory, adjustment, violations = 0., 0., 0
        final_soc = min_soc = max_soc = np.nan
    residual = wind.sum() * c.dt_hours - export.sum() * c.dt_hours - curtail.sum() * c.dt_hours - losses - inventory
    if abs(residual) > 1e-4:
        raise ValueError("Integrated energy conservation violated")
    return {"ramp_violations": int(trace.ramp_violation.sum()), "total_ramp_exceedance_kw": float(trace.ramp_exceedance_kw.sum()),
        "mean_grid_ramp_kw": float(trace.grid_ramp_kw.mean()), "max_grid_ramp_kw": float(trace.grid_ramp_kw.max()),
        "reference_200kw_violations": int(trace.reference_200kw_violation.sum()),
        "reference_200kw_exceedance_kw": float(trace.reference_200kw_exceedance_kw.sum()),
        "charge_energy_kwh": charge_energy, "discharge_energy_kwh": discharge_energy,
        "throughput_kwh": charge_energy + discharge_energy, "conversion_losses_kwh": losses,
        "curtailment_kwh": curtail.sum() * c.dt_hours, "actual_export_kwh": export.sum() * c.dt_hours,
        "terminal_inventory_change_kwh": inventory if battery else np.nan,
        "hypothetical_terminal_adjusted_export_kwh": export.sum() * c.dt_hours + adjustment,
        "initial_energy_kwh": c.initial_energy if battery else np.nan, "final_soc_percent": final_soc,
        "min_soc_percent": min_soc, "max_soc_percent": max_soc, "soc_violations": violations,
        "energy_conservation_residual_kwh": residual,
        "equivalent_full_cycle_proxy": (charge_energy + discharge_energy) / (2 * c.capacity_kwh) if battery else np.nan,
        "decision_seconds": float(trace.decision_wall_seconds.sum()),
        "max_solver_constraint_residual": float(trace.max_constraint_residual.max()) if battery else np.nan}


def study_jobs(mode: str, base: MPCConfig) -> list[dict[str, Any]]:
    """Predeclared OFAT levels; never selected from evaluation performance."""
    if mode in ("pilot", "benchmark"):
        return [dict(variant="base", controller=case, config=asdict(replace(base, risk_weight=0.)
                     if case in ("persistence_nominal", "xgboost_nominal", "perfect_forecast_oracle") else base), alpha=.1) for case in CASES]
    jobs = [dict(variant="base", controller="adaptive_one_sided", config=asdict(base), alpha=.1)]
    if mode == "sensitivity":
        levels = {"capacity_kwh": [1000., 4000.], "max_power_kw": [500., 1500.],
            "soc_band": [(20., 90.), (40., 70.)], "ramp_limit_kw": [100., 400.], "horizon": [1, 3],
            "alpha": [.05, .2], "battery_ramp_weight": [0., 1.],
            "reserve_soc_percent": [40., 60.], "initial_soc_percent": [40., 70.]}
        for parameter, values in levels.items():
            for value in values:
                changes = {} if parameter == "alpha" else ({"min_soc_percent": value[0], "max_soc_percent": value[1]}
                    if parameter == "soc_band" else {parameter: value})
                variant = f"{parameter}_{str(value).replace(' ', '').replace('.', 'p').replace(',', '_').replace('(', '').replace(')', '')}"
                jobs.append(dict(variant=variant, controller="adaptive_one_sided", config=asdict(replace(base, **changes)),
                                 alpha=value if parameter == "alpha" else .1))
    elif mode == "ablations":
        for case in ("persistence_nominal", "xgboost_nominal", "adaptive_floors_only"):
            jobs.append(dict(variant=case, controller=case, config=asdict(replace(base, risk_weight=0.)
                             if case in ("persistence_nominal", "xgboost_nominal") else base), alpha=.1))
        for name, changes in (("no_reserve_penalty", {"reserve_penalty": 0.}),
                              ("no_secondary_exceedance_penalty", {"secondary_exceedance_weight": 0.}),
                              ("no_primary_stage", {"primary_enabled": False}),
                              ("no_grid_penalties", {"primary_enabled": False, "secondary_exceedance_weight": 0., "absolute_ramp_weight": 0.}),
                              ("zero_primary_tolerance", {"primary_tolerance": 0.})):
            jobs.append(dict(variant=name, controller="adaptive_one_sided", config=asdict(replace(base, **changes)), alpha=.1))
    else:
        raise ValueError(f"Unknown study mode: {mode}")
    return jobs


def run_job(payload: dict[str, Any]) -> dict[str, Any]:
    """One independent block; every output has an exclusive, case-specific name."""
    config = MPCConfig(**payload["config"])
    source = block_path(payload["period"], payload["block_id"])
    frame = pd.read_csv(source, parse_dates=["timestamp"])
    if payload.get("intervals"):
        frame = frame.iloc[:payload["intervals"]].copy()
    trace, plans, metrics, diagnostics = run_block(payload["controller"], frame, config,
        payload["period"], payload["block_id"], payload["alpha"])
    directory = Path(payload["output"]) / payload["variant"] / payload["controller"]
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"block_{payload['block_id']:02d}"
    for name, table in (("trace", trace), ("plans", plans), ("uncertainty", diagnostics)):
        if not table.empty:
            with (directory / f"{stem}_{name}.csv").open("x", newline="", encoding="utf-8") as stream:
                table.to_csv(stream, index=False)
    metrics.update(variant=payload["variant"], source_sha256=sha256(source))
    if payload["period"] == "evaluation" and payload["variant"] == "base" and payload["controller"] in ("fixed_margin", "adaptive_one_sided"):
        frozen_case = "fixed" if payload["controller"] == "fixed_margin" else "adaptive_one_sided"
        frozen = ROOT / f"results/frozen_heldout/final_20261029/{frozen_case}/adaptive_charging_mpc_block_{payload['block_id']}_weight_0p500.csv"
        original = pd.read_csv(frozen).iloc[:len(trace)]
        for column in ("charge_kw", "discharge_kw", "grid_export_kw", "soc_percent"):
            difference = trace[column].to_numpy() - original[column].to_numpy()
            metrics[f"frozen_max_abs_difference_{column}"] = float(np.max(np.abs(difference)))
            metrics[f"frozen_changed_intervals_{column}"] = int(np.count_nonzero(np.abs(difference) > .001))
        metrics["frozen_reference_sha256"] = sha256(frozen)
    return metrics
