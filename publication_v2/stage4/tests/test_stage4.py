"""Stage 4 tests: data-access guards, causal features, causal calibration/skill, closed-loop leakage."""
from __future__ import annotations

import json
import unittest

import numpy as np
import pandas as pd

from publication_v2.stage4 import kelmarsh
from publication_v2.stage4.closed_loop import STEPS, TAIL, WINDOW, Series, bundle_at, eligible, run_episode
from publication_v2.stage4.features import FEATURES, LABELS, build


def frame(n=600, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range('2021-03-01 00:10', periods=n, freq='10min', tz='UTC')
    ws = np.clip(8 + np.cumsum(rng.normal(0, .3, n)), 0, 25)
    y = np.clip(2050 * ((ws - 3) / 9).clip(0, 1) ** 3 + rng.normal(0, 20, n), 0, 2050)
    return pd.DataFrame({'realised_kw': y, 'power_kw': y, 'wind_ms': ws, 'wind_sd_ms': np.full(n, .5),
                         'wind_dir_deg': np.full(n, 200.), 'lost_kwh': np.zeros(n)}, index=idx)


def series(n=400, seed=1, noise=60.):
    rng = np.random.default_rng(seed)
    times = pd.date_range('2021-03-01 00:00', periods=n, freq='10min', tz='UTC')
    y = 1000 + 600 * np.sin(np.arange(n) / 15) + rng.normal(0, 40, n)   # never saturates
    pred = np.column_stack([np.r_[y[i + 1:], np.full(i + 1, np.nan)] for i in range(6)])
    pred = np.clip(pred + rng.normal(0, noise, pred.shape), 0, None)
    return Series(times, y, pred, 'test')


class DataAccess(unittest.TestCase):
    def test_sealed_and_validation_years_refused_by_default(self):
        for year in (2022, 2023, 2024):
            with self.assertRaises(kelmarsh.DataAccessError):
                kelmarsh.load_turbine(year)

    def test_unknown_year_refused(self):
        with self.assertRaises(kelmarsh.DataAccessError):
            kelmarsh.load_turbine(2017)

    @unittest.skipUnless((kelmarsh.ROOT / 'development' / kelmarsh.ARCHIVES[2019][1]).exists(), 'data not present')
    def test_development_year_grid_and_timing(self):
        f = kelmarsh.load_turbine(2019)
        self.assertEqual(len(f), 52560)
        self.assertEqual(str(f.index[0]), '2019-01-01 00:10:00+00:00')  # label 00:00 -> interval end 00:10
        self.assertTrue((f['realised_kw'].dropna() >= 0).all())


class Features(unittest.TestCase):
    def test_contract_order_and_persistence_anchor(self):
        t = build(frame())
        self.assertEqual(list(t.columns[:len(FEATURES)]), FEATURES)
        self.assertEqual(FEATURES[0], 'power_kw')

    def test_features_do_not_use_future_values(self):
        f = frame()
        base = build(f)
        changed = f.copy()
        changed.iloc[301:, :] = changed.iloc[301:, :] * 3 + 7   # alter everything after index 300
        alt = build(changed)
        pd.testing.assert_frame_equal(base.iloc[:301][FEATURES], alt.iloc[:301][FEATURES])

    def test_labels_are_next_six_intervals(self):
        f = frame()
        t = build(f)
        for i, label in enumerate(LABELS):
            self.assertAlmostEqual(t[label].iloc[100], f['realised_kw'].iloc[101 + i])

    def test_gaps_are_not_imputed(self):
        f = frame()
        f.iloc[200, f.columns.get_loc('realised_kw')] = np.nan
        t = build(f)
        self.assertTrue(np.isnan(t['power_mean_40min'].iloc[200:204]).all())


class Calibration(unittest.TestCase):
    def test_bundle_ignores_realised_values_at_or_after_decision(self):
        s = series()
        k = 200
        b = bundle_at(s, k)
        y2 = s.realised.copy()
        y2[k:] = 0.0
        b2 = bundle_at(Series(s.times, y2, s.predictions, s.name), k)
        self.assertEqual((b.lower_kw, b.upper_kw, b.provenance), (b2.lower_kw, b2.upper_kw, b2.provenance))

    def test_calibration_window_and_skill(self):
        s = series(noise=1.)
        b = bundle_at(s, 300)
        skill = json.loads(b.provenance)['released_skill']
        self.assertEqual(skill['pairs'], 6 * WINDOW)
        self.assertGreater(skill['pooled_skill_score'], .9)       # near-perfect forecast beats persistence
        for newest in b.calibration_newest_target_times:
            self.assertLess(newest, s.times[300].to_pydatetime())

    def test_insufficient_history_gives_no_bundle(self):
        self.assertIsNone(bundle_at(series(), 20))


class ClosedLoop(unittest.TestCase):
    def test_actions_do_not_depend_on_future_outcomes(self):
        s = series()
        k0 = 100
        self.assertTrue(eligible(s, k0))
        base = run_episode(s, k0, 'stochastic')
        y2 = s.realised.copy()
        y2[k0 + STEPS + TAIL + 1:] += 500       # after the episode and its tail
        alt = run_episode(Series(s.times, y2, s.predictions, s.name), k0, 'stochastic')
        strip = lambda m: {k: v for k, v in m.items() if 'computation_time' not in k}
        self.assertEqual(strip(base['metrics']), strip(alt['metrics']))

    def test_conservation_and_safety_for_all_controllers(self):
        s = series()
        for c in ('uncontrolled', 'heuristic', 'deterministic', 'fixed_margin', 'adaptive',
                  'stochastic', 'stochastic_skill'):
            m = run_episode(s, 100, c)['metrics']
            self.assertEqual(m['soc_constraint_violations'] + m['power_constraint_violations'], 0)
            self.assertLess(abs(m['energy_accounting_residual_kwh']), 1e-6)

    def test_missing_realised_value_makes_episode_ineligible(self):
        s = series()
        y2 = s.realised.copy()
        y2[130] = np.nan
        self.assertFalse(eligible(Series(s.times, y2, s.predictions, s.name), 100))


if __name__ == '__main__':
    unittest.main()
