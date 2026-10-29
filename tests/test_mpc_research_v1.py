"""Physical/intervention/reference tests for the separately versioned MPC."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import cvxpy as cp
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from windresearch.mpc import MPCConfig, SolverFailure, TwoStageMPC, realise
from windresearch.experiments import run_block, study_jobs, validate_and_measure


class PhysicalExecutionTests(unittest.TestCase):
    def setUp(self):
        self.config = MPCConfig()

    def test_charge_loss_upper_soc_and_power_balance(self):
        d = {"committed_charge_kw": 2000., "committed_discharge_kw": 0., "committed_curtailment_kw": 500.}
        result = realise(d, 1200., 1790., self.config)
        self.assertAlmostEqual(result["energy_kwh"], 1800.)
        self.assertAlmostEqual(result["charge_kw"], 10 / (.95 / 6))
        self.assertAlmostEqual(result["grid_export_kw"], 1200 - result["charge_kw"] - 500)

    def test_discharge_efficiency_lower_soc_zero_wind(self):
        d = {"committed_charge_kw": 0., "committed_discharge_kw": 1000., "committed_curtailment_kw": 500.}
        result = realise(d, 0., 810., self.config)
        self.assertAlmostEqual(result["energy_kwh"], 800.)
        self.assertAlmostEqual(result["discharge_kw"], 10 * .95 * 6)
        self.assertEqual(result["curtailment_kw"], 0.)

    def test_wind_shortfall_clips_charging_before_curtailment(self):
        d = {"committed_charge_kw": 900., "committed_discharge_kw": 0., "committed_curtailment_kw": 400.}
        result = realise(d, 50., 1000., self.config)
        self.assertEqual(result["charge_kw"], 50.)
        self.assertEqual(result["curtailment_kw"], 0.)
        self.assertAlmostEqual(result["energy_kwh"], 1000 + .95 * 50 / 6)

    def test_simultaneous_commitments_are_rejected(self):
        d = {"committed_charge_kw": 100., "committed_discharge_kw": 100., "committed_curtailment_kw": 0.}
        with self.assertRaisesRegex(ValueError, "simultaneous"):
            realise(d, 500., 1000., self.config)

    def test_invalid_config_rejected(self):
        for changes in ({"initial_soc_percent": 20}, {"eta_charge": 1.1}, {"horizon": 0}, {"capacity_kwh": 0}):
            with self.assertRaises(ValueError):
                replace(self.config, **changes)


class SolverAndReferenceTests(unittest.TestCase):
    def test_horizon_one_and_exact_scenario_first_minima(self):
        c = MPCConfig(horizon=1)
        engine = TwoStageMPC(c)
        d = engine.decide(np.array([1500.]), np.array([1200.]), 1000., 2000.)
        self.assertEqual(d["stage1"]["status"], "optimal")
        self.assertLessEqual(d["max_constraint_residual"], .001)
        for plan in d["plans"]:
            self.assertAlmostEqual(plan["charge_kw"], min(d["committed_charge_kw"], plan["forecast_kw"]), places=4)
            self.assertAlmostEqual(plan["discharge_kw"], d["committed_discharge_kw"], places=4)
            self.assertAlmostEqual(plan["curtailment_kw"], min(d["committed_curtailment_kw"], plan["forecast_kw"] - plan["charge_kw"]), places=4)
            self.assertGreaterEqual(plan["energy_kwh"], 800 - .001)
            self.assertLessEqual(plan["energy_kwh"], 1800 + .001)

    def test_solver_exception_is_explicit_failure(self):
        engine = TwoStageMPC(MPCConfig(horizon=1))
        with patch.object(cp.Problem, "solve", side_effect=RuntimeError("deliberate unavailable solver")):
            with self.assertRaisesRegex(SolverFailure, "primary.*unavailable solver"):
                engine.decide(np.array([1000.]), np.zeros(1), 1000., 1000.)

    def test_nonoptimal_status_is_explicit_failure(self):
        engine = TwoStageMPC(MPCConfig(horizon=1))
        def nonoptimal(problem, *args, **kwargs):
            problem._status = cp.INFEASIBLE
            problem._value = np.inf
        with patch.object(cp.Problem, "solve", nonoptimal):
            with self.assertRaisesRegex(SolverFailure, "infeasible"):
                engine.decide(np.array([1000.]), np.zeros(1), 1000., 1000.)

    def test_native_frozen_one_step_objective_and_first_action_regression(self):
        # Execute the unmodified source body in memory, with no top-level file writes.
        source = (ROOT / "scripts/frozen_fixed_heldout.py").read_text()
        body = source[source.index("    nominal = np.maximum("):source.index("    records.append({")]
        block = pd.read_csv(ROOT / "data/processed/evaluation_block_1.csv", parse_dates=["timestamp"])
        row = block.iloc[0]
        quantiles = pd.read_csv(ROOT / "results/multistep_uncertainty_calibration_split.csv").calibration_quantile_kw.to_numpy()
        namespace = dict(cp=cp, np=np, pd=pd, row=row, step=0, block_id=1, risk_weight=.5,
            MAX_POWER=1000., MAX_ENERGY=1800., MIN_ENERGY=800., RESERVE_ENERGY=1000.,
            RESERVE_PENALTY=100., ETA_C=.95, ETA_D=.95, DT=1/6, RAMP_LIMIT=200., HORIZON=6,
            BATTERY_RAMP_WEIGHT=.1, energy_now=1000., previous_export=float(row.current_power_kw),
            previous_battery_power=0., quantiles=quantiles,
            sys=type("Arguments", (), {"argv": ["reference", "1", ".5", ".1", "1000", "100", "100"]})())
        exec("if True:\n" + body, namespace)
        engine = TwoStageMPC()
        decision = engine.decide(np.array([row[f"xgboost_h{h}_kw"] for h in range(1, 7)]), quantiles,
                                 1000., float(row.current_power_kw))
        self.assertAlmostEqual(decision["stage1"]["objective"], namespace["primary_optimum"], places=3)
        self.assertAlmostEqual(decision["stage2"]["objective"], namespace["problem"].value, places=2)
        self.assertLessEqual(decision["achieved_primary"], namespace["primary_optimum"] + 100.001)
        actual = realise(decision, row.actual_h1_kw, 1000.)
        self.assertAlmostEqual(actual["grid_export_kw"], namespace["actual_export"], places=3)

    def test_future_targets_cannot_change_nominal_command(self):
        frame = pd.read_csv(ROOT / "data/processed/controller_development_blocks/development_block_2.csv", parse_dates=["timestamp"]).iloc[:1].copy()
        first, _, _, _ = run_block("xgboost_nominal", frame, MPCConfig(), "development", 2)
        changed = frame.copy()
        for h in range(1, 7):
            changed[f"actual_h{h}_kw"] = -1e8
        second, _, _, _ = run_block("xgboost_nominal", changed, MPCConfig(), "development", 2)
        for column in ("committed_charge_kw", "committed_discharge_kw", "committed_curtailment_kw"):
            np.testing.assert_allclose(first[column], second[column], atol=1e-6, rtol=0)


class StudyProtocolTests(unittest.TestCase):
    def test_predeclared_nine_dimensions_and_ablations(self):
        sensitivity = study_jobs("sensitivity", MPCConfig())
        self.assertEqual(len(sensitivity), 19)
        self.assertEqual(len({job["variant"] for job in sensitivity}), 19)
        for job in sensitivity:
            MPCConfig(**job["config"])
        ablations = study_jobs("ablations", MPCConfig())
        self.assertEqual(len(ablations), 9)
        no_grid = next(job for job in ablations if job["variant"] == "no_grid_penalties")
        self.assertFalse(no_grid["config"]["primary_enabled"])
        self.assertEqual(no_grid["config"]["absolute_ramp_weight"], 0.)
        self.assertEqual(no_grid["config"]["secondary_exceedance_weight"], 0.)

    def test_terminal_inventory_and_corrupted_energy_trace(self):
        frame = pd.read_csv(ROOT / "data/processed/controller_development_blocks/development_block_2.csv", parse_dates=["timestamp"]).iloc[:2].copy()
        trace, _, metrics, _ = run_block("xgboost_nominal", frame, MPCConfig(), "development", 2)
        self.assertLess(abs(metrics["energy_conservation_residual_kwh"]), 1e-5)
        delta = metrics["terminal_inventory_change_kwh"]
        adjustment = .95 * delta if delta >= 0 else delta / .95
        self.assertAlmostEqual(metrics["hypothetical_terminal_adjusted_export_kwh"], metrics["actual_export_kwh"] + adjustment)
        trace.loc[trace.index[-1], "energy_kwh"] += 1
        with self.assertRaisesRegex(ValueError, "DC battery energy"):
            validate_and_measure(trace, frame, MPCConfig(), "xgboost_nominal")

    def test_corrupted_ramp_count_exceedance_and_soc_reporting_are_rejected(self):
        frame = pd.read_csv(ROOT / "data/processed/controller_development_blocks/development_block_2.csv", parse_dates=["timestamp"]).iloc[:2].copy()
        trace, _, _, _ = run_block("xgboost_nominal", frame, MPCConfig(), "development", 2)
        for column in ("grid_ramp_kw", "ramp_exceedance_kw", "ramp_violation", "reference_200kw_exceedance_kw",
                       "reference_200kw_violation", "soc_percent", "initial_energy_kwh"):
            corrupted = trace.copy()
            corrupted.loc[corrupted.index[0], column] += 1
            with self.assertRaises(ValueError, msg=column):
                validate_and_measure(corrupted, frame, MPCConfig(), "xgboost_nominal")


if __name__ == "__main__":
    unittest.main()
