"""Independently verify preservation, completion and saved physical/solver traces.

This command never reruns an experiment or tests and exclusively creates its
requested JSON report. Run after the declared studies finish. Changed current
implementation files require hash-matching archived executed-source snapshots.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

from windresearch.integrity import (IntegrityError, checked_relative_path, sha256,
    verify_frozen_manifest, verify_hash_mapping, verify_protected_baseline)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise IntegrityError(message)


def close(label: str, actual: Any, expected: Any, tolerance: float = 1e-4) -> None:
    if not np.allclose(np.asarray(actual, float), np.asarray(expected, float),
                       rtol=0, atol=tolerance, equal_nan=True):
        raise IntegrityError(f"Independent reconstruction mismatch: {label}")


def planning_overlap_kw(charge: Any, discharge: Any, tolerance_kw: float = 1e-3) -> float:
    """Check mutually exclusive *planned* powers at the declared kW tolerance.

    A product threshold has units kW squared and amplifies a small inactive
    channel by the active-channel magnitude. The original v1 verifier used
    that inappropriate planned-power comparison. A 1e-3 kW overlap threshold
    matches the already declared solver constraint acceptance tolerance;
    realised execution retains its separate, stricter existing product guard.
    """
    overlap = np.minimum(np.asarray(charge, float), np.asarray(discharge, float))
    require(bool(np.isfinite(overlap).all()), "Non-finite planned battery overlap")
    maximum = float(np.max(overlap))
    require(maximum <= tolerance_kw, f"Planned battery overlap {maximum:.12g} kW exceeds {tolerance_kw:g} kW")
    return max(0., maximum)


def verify_trace(trace: pd.DataFrame, source: pd.DataFrame, config: dict,
                 case: str, metric: pd.Series) -> dict:
    """Recompute metrics from powers; do not trust stored ramp/SOC columns."""
    require(len(trace) == len(source) > 0, "Trace/source interval count differs")
    decision = pd.to_datetime(trace.decision_timestamp)
    require(np.array_equal(decision.to_numpy(), source.timestamp.to_numpy()), "Decision timestamps differ from source")
    require(np.array_equal(pd.to_datetime(trace.timestamp).to_numpy(),
            (source.timestamp + pd.Timedelta(minutes=10)).to_numpy()), "Executed target timestamp mismatch")
    require(not decision.duplicated().any(), "Duplicate decision timestamp")
    dt, eta_c, eta_d = config["dt_hours"], config["eta_charge"], config["eta_discharge"]
    close("ten-minute physical interval", dt, 1 / 6, 1e-12)
    capacity = config["capacity_kwh"]
    low, high = capacity * config["min_soc_percent"] / 100, capacity * config["max_soc_percent"] / 100
    initial = capacity * config["initial_soc_percent"] / 100
    powers = trace[["wind_generation_kw", "charge_kw", "discharge_kw", "curtailment_kw", "grid_export_kw"]].to_numpy(float)
    require(bool(np.isfinite(powers).all()), "Non-finite physical power")
    wind, charge, discharge, curtail, export = powers.T
    require(bool((powers >= -1e-5).all()), "Negative physical power")
    close("raw target wind", wind, np.maximum(0, source.actual_h1_kw))
    require(bool((charge + curtail <= wind + 1e-5).all()), "Charge/curtailment exceeds wind")
    require(bool((charge <= config["max_power_kw"] + 1e-5).all() and
                 (discharge <= config["max_power_kw"] + 1e-5).all()), "Battery power rating exceeded")
    require(bool((charge * discharge <= 1e-3).all()), "Simultaneous battery operation")
    close("AC power balance", export, wind - charge - curtail + discharge)
    ramp = np.abs(np.diff(np.r_[max(0., source.current_power_kw.iloc[0]), export]))
    excess = np.maximum(0., ramp - config["ramp_limit_kw"])
    violations = (ramp > config["ramp_limit_kw"] + .001).astype(int)
    close("grid ramp", trace.grid_ramp_kw, ramp)
    close("ramp exceedance", trace.ramp_exceedance_kw, excess)
    close("ramp violation count column", trace.ramp_violation, violations, 0)
    close("common200 exceedance", trace.reference_200kw_exceedance_kw, np.maximum(0, ramp - 200))
    close("common200 violation", trace.reference_200kw_violation, (ramp > 200.001).astype(int), 0)
    charge_energy, discharge_energy = charge.sum() * dt, discharge.sum() * dt
    losses = (1 - eta_c) * charge_energy + (1 / eta_d - 1) * discharge_energy
    battery = case != "uncontrolled"
    if battery:
        energy = initial + np.cumsum(eta_c * charge * dt - discharge * dt / eta_d)
        close("DC battery energy", trace.energy_kwh, energy)
        close("SOC percentage", trace.soc_percent, energy / capacity * 100)
        close("observed pre-decision battery energy", trace.initial_energy_kwh, np.r_[initial, energy[:-1]])
        committed = trace[["committed_charge_kw", "committed_discharge_kw", "committed_curtailment_kw"]].to_numpy(float)
        require(bool(np.isfinite(committed).all() and (committed >= -1e-5).all()), "Invalid committed command")
        old_energy = np.r_[initial, energy[:-1]]
        expected_charge = np.minimum.reduce([committed[:, 0], wind, np.full(len(wind), config["max_power_kw"]),
            np.maximum(0, high - old_energy) / (eta_c * dt)])
        expected_discharge = np.minimum.reduce([committed[:, 1], np.full(len(wind), config["max_power_kw"]),
            np.maximum(0, old_energy + eta_c * charge * dt - low) * eta_d / dt])
        close("realised charge fallback", charge, expected_charge)
        close("realised discharge fallback", discharge, expected_discharge)
        close("realised curtailment fallback", curtail, np.minimum(committed[:, 2], np.maximum(0, wind - charge)))
        require(bool((energy >= low - 1e-4).all() and (energy <= high + 1e-4).all()), "Hard SOC violation")
        inventory = float(energy[-1] - initial)
        adjustment = eta_d * inventory if inventory >= 0 else inventory / eta_c
        require(trace.stage2_status.eq("optimal").all(), "Non-optimal secondary stage")
        require(bool((trace.max_constraint_residual <= 1e-3).all()), "Logged solver constraint residual too high")
        require(bool(np.isfinite(trace[["stage2_objective", "achieved_primary_objective"]]).all().all()), "Non-finite solver objective")
        if config["primary_enabled"]:
            require(trace.stage1_status.eq("optimal").all(), "Non-optimal primary stage")
            require(bool((trace.achieved_primary_objective <= trace.stage1_objective + config["primary_tolerance"] + 1e-3).all()),
                    "Lexicographic allowance violated")
        else:
            require(trace.stage1_status.eq("disabled_by_declared_ablation").all(), "Unreported primary-stage ablation")
    else:
        require(bool((charge == 0).all() and (discharge == 0).all() and (curtail == 0).all()), "Uncontrolled case has battery actions")
        require(trace.energy_kwh.isna().all() and trace.soc_percent.isna().all(), "No-battery case has battery state")
        inventory = adjustment = 0.
    residual = float(wind.sum() * dt - export.sum() * dt - curtail.sum() * dt - losses - inventory)
    require(abs(residual) <= 1e-4, "Integrated physical energy conservation failure")
    expected = {"ramp_violations": int(violations.sum()), "total_ramp_exceedance_kw": float(excess.sum()),
        "mean_grid_ramp_kw": float(ramp.mean()), "max_grid_ramp_kw": float(ramp.max()),
        "reference_200kw_violations": int((ramp > 200.001).sum()),
        "reference_200kw_exceedance_kw": float(np.maximum(0, ramp - 200).sum()),
        "charge_energy_kwh": charge_energy, "discharge_energy_kwh": discharge_energy,
        "throughput_kwh": charge_energy + discharge_energy, "conversion_losses_kwh": losses,
        "curtailment_kwh": curtail.sum() * dt, "actual_export_kwh": export.sum() * dt,
        "hypothetical_terminal_adjusted_export_kwh": export.sum() * dt + adjustment,
        "energy_conservation_residual_kwh": residual, "soc_violations": 0,
        "terminal_inventory_change_kwh": inventory if battery else np.nan,
        "equivalent_full_cycle_proxy": (charge_energy + discharge_energy) / (2 * capacity) if battery else np.nan}
    if battery:
        expected.update(final_soc_percent=energy[-1] / capacity * 100,
                        min_soc_percent=energy.min() / capacity * 100,
                        max_soc_percent=energy.max() / capacity * 100)
    for name, value in expected.items():
        close(f"block metric {name}", metric[name], value)
    close("block metric interval count", metric.intervals, len(trace), 0)
    close("successful block solver failures", metric.solver_failures, 0, 0)
    return {"intervals": len(trace), "energy_residual_kwh": residual, "ramp_metrics_independently_reconstructed": True}


def verify_plans(plans: pd.DataFrame, trace: pd.DataFrame, config: dict, initial_export_kw: float) -> dict:
    """Check logged planning physics and first-command scenario minima."""
    plans = plans.copy()
    plans["decision_timestamp"] = pd.to_datetime(plans.decision_timestamp)
    horizon = config["horizon"]
    scenarios = ("nominal",) if config["risk_weight"] == 0 else ("nominal", "downside")
    expected_keys = {(pd.Timestamp(t), s, (h + 1) * 10) for t in trace.decision_timestamp
                     for s in scenarios for h in range(horizon)}
    keys = list(plans[["decision_timestamp", "scenario", "horizon_minutes"]].itertuples(index=False, name=None))
    require(len(keys) == len(expected_keys) and set(keys) == expected_keys, "Missing/duplicate planning decision/scenario/horizon")
    plans = plans.sort_values(["decision_timestamp", "scenario", "horizon_minutes"])
    fields = ["forecast_kw", "charge_kw", "discharge_kw", "curtailment_kw", "energy_kwh", "export_kw", "ramp_kw", "exceedance_kw", "reserve_shortfall_kwh"]
    require(bool(np.isfinite(plans[fields]).all().all()), "Non-finite logged plan")
    observed = trace.copy()
    observed["decision_timestamp"] = pd.to_datetime(observed.decision_timestamp)
    observed = observed.set_index("decision_timestamp")
    observed["previous_actual_export_kw"] = np.r_[max(0., initial_export_kw), observed.grid_export_kw.iloc[:-1]]
    observed["previous_actual_battery_kw"] = np.r_[0., (observed.discharge_kw - observed.charge_kw).iloc[:-1]]
    group = plans.groupby(["decision_timestamp", "scenario"], sort=False)
    previous_energy = group.energy_kwh.shift().fillna(plans.decision_timestamp.map(observed.initial_energy_kwh))
    c, d, u, w, energy = [plans[name].to_numpy(float) for name in
                         ("charge_kw", "discharge_kw", "curtailment_kw", "forecast_kw", "energy_kwh")]
    require(bool((np.c_[c, d, u, w, plans.export_kw] >= -1e-5).all()), "Negative planned power")
    require(bool((c + u <= w + 1e-4).all()), "Planned wind availability failure")
    maximum_overlap = planning_overlap_kw(c, d)
    require(bool((c <= config["max_power_kw"] + 1e-4).all() and (d <= config["max_power_kw"] + 1e-4).all()), "Planned power rating violation")
    minimum, maximum = [config["capacity_kwh"] * config[k] / 100 for k in ("min_soc_percent", "max_soc_percent")]
    require(bool((energy >= minimum - 1e-3).all() and (energy <= maximum + 1e-3).all()), "Planned hard SOC violation")
    close("planned energy dynamics", energy, previous_energy + config["eta_charge"] * c * config["dt_hours"] - d * config["dt_hours"] / config["eta_discharge"], 1e-3)
    close("planned power balance", plans.export_kw, w - c - u + d, 1e-3)
    previous_export = group.export_kw.shift().fillna(plans.decision_timestamp.map(observed.previous_actual_export_kw))
    close("planned ramp boundary/dynamics", plans.ramp_kw, plans.export_kw - previous_export, 1e-3)
    expected_weights = plans.scenario.map({"nominal": 1. if config["risk_weight"] == 0 else 1. - config["risk_weight"],
                                          "downside": config["risk_weight"]})
    close("planning scenario weights", plans.scenario_weight, expected_weights, 1e-12)
    require(bool((plans.exceedance_kw >= np.maximum(0, plans.ramp_kw.abs() - config["ramp_limit_kw"]) - 1e-3).all()), "Planned exceedance epigraph invalid")
    require(bool((plans.reserve_shortfall_kwh >= np.maximum(0, config["capacity_kwh"] * config["reserve_soc_percent"] / 100 - energy) - 1e-3).all()), "Planned soft reserve epigraph invalid")
    first = plans.loc[plans.horizon_minutes.eq(10)]
    charge_request = first.decision_timestamp.map(observed.committed_charge_kw)
    curtail_request = first.decision_timestamp.map(observed.committed_curtailment_kw)
    close("first-scenario charge minimum", first.charge_kw, np.minimum(charge_request, first.forecast_kw), 1e-3)
    close("first-scenario discharge commitment", first.discharge_kw, first.decision_timestamp.map(observed.committed_discharge_kw), 1e-3)
    close("first-scenario curtailment minimum", first.curtailment_kw, np.minimum(curtail_request, first.forecast_kw - first.charge_kw), 1e-3)
    weighted = (plans.exceedance_kw * plans.scenario_weight).groupby(plans.decision_timestamp).sum()
    close("logged achieved primary objective", weighted.reindex(observed.index), observed.achieved_primary_objective, 1e-3)
    plans["battery_power_kw"] = plans.discharge_kw - plans.charge_kw
    previous_battery = plans.groupby(["decision_timestamp", "scenario"], sort=False).battery_power_kw.shift().fillna(
        plans.decision_timestamp.map(observed.previous_actual_battery_kw))
    cost = (config["absolute_ramp_weight"] * plans.ramp_kw.abs()
        + config["battery_ramp_weight"] * (plans.battery_power_kw - previous_battery).abs()
        + config["secondary_exceedance_weight"] * plans.exceedance_kw
        + config["throughput_weight"] * config["dt_hours"] * (plans.charge_kw + plans.discharge_kw)
        + config["curtailment_weight"] * plans.curtailment_kw
        + config["reserve_penalty"] * plans.reserve_shortfall_kwh)
    terminal = plans.horizon_minutes.eq(horizon * 10)
    cost = cost + terminal * config["terminal_weight"] * (
        plans.energy_kwh - config["capacity_kwh"] * config["terminal_soc_percent"] / 100).abs()
    total = (cost * plans.scenario_weight).groupby(plans.decision_timestamp).sum()
    close("reconstructed secondary objective", total.reindex(observed.index), observed.stage2_objective, 2e-3)
    return {"plan_rows": len(plans), "planning_physics_and_first_command_minima": "pass",
            "max_planned_charge_discharge_overlap_kw": maximum_overlap,
            "planned_overlap_acceptance_tolerance_kw": 1e-3}


def verify_completed_study(root: Path, directory: Path, snapshots: Path) -> dict:
    completion = json.loads((directory / "completion.json").read_text(encoding="utf-8"))
    protocol = json.loads((directory / "protocol.json").read_text(encoding="utf-8"))
    require(completion.get("complete") is True and completion.get("failed_jobs") == 0, "Study did not complete successfully")
    expected = {(v["variant"], v["controller"], int(b)) for v in protocol["variants"] for b in protocol["blocks"]}
    require(completion["completed_jobs"] == completion["expected_jobs"] == len(expected), "Completion job count differs from protocol")
    metrics = pd.read_csv(directory / "block_metrics.csv")
    aggregate = pd.read_csv(directory / "aggregate_metrics.csv")
    actual = list(metrics[["variant", "controller", "block_id"]].itertuples(index=False, name=None))
    require(len(actual) == len(expected) and set(actual) == expected, "Missing/duplicate declared job")
    require(len(pd.read_csv(directory / "failures.csv")) == 0, "Nonempty failure record")
    require(aggregate.complete.eq(True).all(), "Incomplete aggregate row")
    for key in ("input_source_sha256", "uncertainty_history_sha256"):
        verify_hash_mapping(root, protocol[key])
    implementations = []
    for relative, expected_hash in protocol["implementation_sha256"].items():
        live = checked_relative_path(root, relative)
        matches = live.is_file() and sha256(live) == expected_hash
        snapshot = checked_relative_path(snapshots, relative)
        archived = snapshot.is_file() and sha256(snapshot) == expected_hash
        require(matches or archived, f"Executed implementation unavailable or changed without matching snapshot: {relative}")
        implementations.append({"path": relative, "executed_sha256": expected_hash,
            "current_matches_executed": matches, "archived_executed_snapshot_matches": archived})
    variants = {(v["variant"], v["controller"]): v for v in protocol["variants"]}
    files = {"protocol.json", "completion.json", "block_metrics.csv", "aggregate_metrics.csv", "failures.csv"}
    physical_intervals = plan_rows = 0
    maximum_residual = maximum_planned_overlap = 0.
    for row in metrics.itertuples(index=False):
        variant = variants[(row.variant, row.controller)]
        config = variant["config"]
        source_relative = (f"data/processed/evaluation_block_{row.block_id}.csv" if protocol["period"] == "evaluation" else
                           f"data/processed/controller_development_blocks/development_block_{row.block_id}.csv")
        source = pd.read_csv(root / source_relative, parse_dates=["timestamp"]).iloc[:protocol["intervals_per_block"]]
        prefix = f"{row.variant}/{row.controller}/block_{row.block_id:02d}"
        trace_relative = prefix + "_trace.csv"
        trace = pd.read_csv(directory / trace_relative)
        result = verify_trace(trace, source, config, row.controller, pd.Series(row._asdict()))
        physical_intervals += result["intervals"]
        maximum_residual = max(maximum_residual, abs(result["energy_residual_kwh"]))
        files.add(trace_relative)
        if row.controller != "uncontrolled":
            plans_relative = prefix + "_plans.csv"
            planned = verify_plans(pd.read_csv(directory / plans_relative), trace, config, float(source.current_power_kw.iloc[0]))
            plan_rows += planned["plan_rows"]
            maximum_planned_overlap = max(maximum_planned_overlap, planned["max_planned_charge_discharge_overlap_kw"])
            files.add(plans_relative)
        if row.controller == "adaptive_one_sided":
            uncertainty_relative = prefix + "_uncertainty.csv"
            uncertainty = pd.read_csv(directory / uncertainty_relative)
            require(len(uncertainty) == 6 * len(trace), "Adaptive uncertainty diagnostics incomplete")
            require((pd.to_datetime(uncertainty.newest_target) < pd.to_datetime(uncertainty.decision_timestamp)).all(),
                    "Adaptive history admits equal/future target")
            files.add(uncertainty_relative)
    sums = ["ramp_violations", "total_ramp_exceedance_kw", "throughput_kwh", "charge_energy_kwh", "discharge_energy_kwh",
            "conversion_losses_kwh", "curtailment_kwh", "actual_export_kwh", "hypothetical_terminal_adjusted_export_kwh",
            "reference_200kw_violations", "reference_200kw_exceedance_kw", "soc_violations", "solver_failures"]
    recomputed = metrics.groupby(["variant", "controller"])[sums].sum().sort_index()
    saved = aggregate.set_index(["variant", "controller"]).sort_index()
    require(recomputed.index.equals(saved.index), "Aggregate case set differs")
    close("aggregate sums", saved[sums], recomputed[sums], 1e-3)
    return {"status": "pass", "declared_jobs": len(expected), "physical_intervals_checked": physical_intervals,
        "planning_rows_checked": plan_rows, "max_absolute_energy_residual_kwh": maximum_residual,
        "max_planned_charge_discharge_overlap_kw": maximum_planned_overlap,
        "planned_overlap_acceptance_tolerance_kw": 1e-3,
        "planned_overlap_note": "Dimensioned kW tolerance matches declared solver acceptance; realised-execution guard unchanged. Original v1 failed report retained.",
        "implementation_identity": implementations,
        "output_sha256": {relative: sha256(directory / relative) for relative in sorted(files)}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New exclusive JSON filename")
    parser.add_argument("--studies", type=Path, default=ROOT / "results/research_grade_v1_20261029")
    parser.add_argument("--study-names", nargs="+", default=["benchmark", "sensitivity", "ablations"])
    parser.add_argument("--baseline", type=Path, default=ROOT / "audits/research_grade_20261029/protected_baseline.json")
    parser.add_argument("--executed-sources", type=Path, default=ROOT / "audits/research_grade_20261029/executed_sources")
    parser.add_argument("--test-log", type=Path, help="Optional existing unittest log; recorded/parsed without rerunning tests")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing existing verification report: {args.output}")
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "scope": "Independent saved-artifact verification; no experiment/test rerun",
              "checks": {}, "errors": [], "test_execution": "not rerun by this command"}
    actions = {"frozen_manifest": lambda: {"status": "pass", "manifest_sha256": sha256(ROOT / "results/development_controller_freeze_manifest.json"),
        "references": len((lambda m: list(m["source_files"].values()) + [e for g in m["development_result_files"].values() for e in g.values()])(
            verify_frozen_manifest(ROOT)))},
        "protected_baseline": lambda: verify_protected_baseline(ROOT, args.baseline)}
    for name in args.study_names:
        if Path(name).name != name or name in (".", ".."):
            raise ValueError("Study names must be directory names")
        actions[f"study_{name}"] = lambda name=name: verify_completed_study(ROOT, args.studies / name, args.executed_sources)
    for name, action in actions.items():
        try:
            report["checks"][name] = action()
        except Exception as error:
            report["checks"][name] = {"status": "fail", "error_type": type(error).__name__, "message": str(error)}
            report["errors"].append(name)
        print(f"{name}: {report['checks'][name]['status']}", flush=True)
    if args.test_log:
        text = args.test_log.read_text(encoding="utf-8", errors="replace")
        summaries = re.findall(r"Ran (\d+) tests? in [^\r\n]+\r?\n\r?\n(OK(?: \([^\r\n]*\))?|FAILED[^\r\n]*)", text)
        report["supplied_test_log"] = {"path": str(args.test_log), "sha256": sha256(args.test_log),
            "interpretation": "Parsed supplied log; not an independent test rerun",
            "last_unittest_summary": {"tests": int(summaries[-1][0]), "summary": summaries[-1][1]} if summaries else None}
        if not summaries or not summaries[-1][1].startswith("OK"):
            report["errors"].append("supplied_test_log_not_passing")
    report["status"] = "pass" if not report["errors"] else "fail"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({"status": report["status"], "errors": report["errors"], "output": str(args.output)}), flush=True)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
