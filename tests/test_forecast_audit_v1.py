"""Scientific boundary, rank and scoring tests for the new read-only audit."""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from windresearch.forecast_audit import (
    STATIC_FLOORS_KW, causal_linear_prediction, conformal_quantile,
    reconstruct_adaptive_margins, run_forecast_audit, summarise_coverage,
    summarise_forecasts,
)


def history_frame(start="2018-01-01", count=400, residual=1000):
    history = pd.DataFrame({"timestamp": pd.date_range(start, periods=count, freq="10min")})
    for h in range(1, 7):
        history[f"xgboost_h{h}_kw"] = float(residual + 1000)
        history[f"actual_h{h}_kw"] = 1000.0
    return history


class ForecastAuditTests(unittest.TestCase):
    def test_order_statistic_uses_finite_sample_rank_without_interpolation(self):
        self.assertEqual(conformal_quantile(np.arange(144)), 130.0)
        self.assertNotEqual(conformal_quantile(np.arange(144)), np.quantile(np.arange(144), 0.9))
        with self.assertRaises(ValueError):
            conformal_quantile([1], alpha=0.1)

    def test_equal_and_future_target_intervention_is_invariant(self):
        history = history_frame()
        decision = history.timestamp.iloc[250]
        original, diagnostics = reconstruct_adaptive_margins(history, [decision])
        changed = history.copy()
        for h in range(1, 7):
            unavailable = changed.timestamp + pd.Timedelta(minutes=h * 10) >= decision
            changed.loc[unavailable, f"actual_h{h}_kw"] = -1e9
        modified, _ = reconstruct_adaptive_margins(changed, [decision])
        np.testing.assert_array_equal(original, modified)
        self.assertTrue((diagnostics.newest_target < decision).all())
        self.assertTrue((diagnostics.newest_target == decision - pd.Timedelta(minutes=10)).all())
        self.assertTrue((diagnostics.selected_count == 144).all())

    def test_old_eligible_observation_can_change_quantile(self):
        history = history_frame(residual=0)
        decision = history.timestamp.iloc[250]
        baseline, _ = reconstruct_adaptive_margins(history, [decision], floors=np.zeros(6))
        history.loc[100:240, "actual_h1_kw"] = -1000.0
        changed, _ = reconstruct_adaptive_margins(history, [decision], floors=np.zeros(6))
        self.assertGreater(changed[0, 0], baseline[0, 0])

    def test_gap_fallback_uses_origin_count_and_floors(self):
        history = history_frame(start="2018-10-30")
        decision = pd.Timestamp("2018-10-31 17:00")
        margins, diagnostics = reconstruct_adaptive_margins(history, [decision])
        np.testing.assert_array_equal(margins[0], STATIC_FLOORS_KW)
        self.assertTrue(diagnostics.fallback_active.all())
        self.assertTrue((diagnostics.post_gap_count == 0).all())
        later, diag = reconstruct_adaptive_margins(history, [pd.Timestamp("2018-11-01 18:00")])
        np.testing.assert_array_equal(later[0], np.full(6, 1000.0))
        self.assertFalse(diag.fallback_active.any())

    def test_insufficient_history_and_duplicate_origins_fail(self):
        history = history_frame(count=150)
        with self.assertRaisesRegex(ValueError, "Insufficient causal history"):
            reconstruct_adaptive_margins(history, [history.timestamp.iloc[145]])
        history.loc[1, "timestamp"] = history.timestamp.iloc[0]
        with self.assertRaisesRegex(ValueError, "unique"):
            reconstruct_adaptive_margins(history, [pd.Timestamp("2018-01-03")])

    def test_sensitivity_alpha_changes_rank_without_accessing_future(self):
        history = history_frame(residual=0)
        for h in range(1, 7):
            history[f"xgboost_h{h}_kw"] += np.arange(len(history))
        low, _ = reconstruct_adaptive_margins(history, [history.timestamp.iloc[250]], alpha=0.05, floors=np.zeros(6))
        high, _ = reconstruct_adaptive_margins(history, [history.timestamp.iloc[250]], alpha=0.20, floors=np.zeros(6))
        self.assertTrue((low > high).all())

    def test_linear_baseline_is_causal_timestamp_based_and_nonnegative(self):
        times = pd.date_range("2018-01-01", periods=4, freq="10min")
        raw = pd.DataFrame({"LV ActivePower (kW)": [100, 200, 10000, 50000]}, index=times)
        self.assertEqual(causal_linear_prediction(raw, [times[1]], 6)[0], 800)
        raw.loc[times[2]:, "LV ActivePower (kW)"] = -1e10
        self.assertEqual(causal_linear_prediction(raw, [times[1]], 6)[0], 800)
        raw.loc[times[1], "LV ActivePower (kW)"] = 0
        self.assertEqual(causal_linear_prediction(raw, [times[1]], 6)[0], 0)
        with self.assertRaisesRegex(ValueError, "Missing"):
            causal_linear_prediction(raw.drop(index=times[0]), [times[1]], 1)

    def test_forecast_rmse_aggregates_squared_errors(self):
        frame = pd.DataFrame({"horizon_minutes": [10, 10]})
        for baseline in ["xgboost", "persistence", "local_linear"]:
            frame[f"{baseline}_error_kw"] = [0, 4]
        result = summarise_forecasts(frame, ["horizon_minutes"])
        np.testing.assert_allclose(result.rmse_kw, np.sqrt(8))
        np.testing.assert_allclose(result.mae_kw, 2)

    def test_one_sided_width_infinite_and_offset_distinct(self):
        frame = pd.DataFrame({
            "horizon_minutes": [10, 10], "actual_kw": [0, 100],
            "fixed_lower_kw": [0, 40], "adaptive_lower_kw": [0, 50],
            "fixed_lower_offset_kw": [20, 30], "adaptive_lower_offset_kw": [20, 20],
            "fixed_two_sided_width_kw": [70, 60],
            "fixed_lower_covered": [True, True], "adaptive_lower_covered": [True, True],
            "fixed_two_sided_covered": [True, False], "floor_binding": [True, False],
            "fallback_active": [False, False],
        })
        result = summarise_coverage(frame, ["horizon_minutes"]).set_index("method")
        self.assertTrue(np.isinf(result.loc["adaptive_signed_lower", "mean_prediction_set_width_kw"]))
        self.assertEqual(result.loc["adaptive_signed_lower", "mean_nominal_minus_lower_kw"], 20)
        self.assertEqual(result.loc["fixed_absolute_two_sided", "mean_prediction_set_width_kw"], 65)
        self.assertEqual(result.loc["fixed_absolute_two_sided", "coverage"], 0.5)

    def test_existing_output_refused_before_loading_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            existing = Path(temp) / "output"
            existing.mkdir()
            with self.assertRaisesRegex(FileExistsError, "Refusing"):
                run_forecast_audit(Path(temp), existing, Path(temp) / "figures")


if __name__ == "__main__":
    unittest.main()
