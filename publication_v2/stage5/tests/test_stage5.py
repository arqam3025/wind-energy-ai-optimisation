"""Stage 5 tests: filter baseline, graded/gated switches, economics."""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from publication_v2.stage31.battery import BatteryConfig
from publication_v2.stage31.evaluation import validate_plan
from publication_v2.stage31.forecast import ForecastBundle
from publication_v2.stage33.controller import StochasticMPCConfig
from publication_v2.stage4.closed_loop import Series, run_episode
from publication_v2.stage5 import economics
from publication_v2.stage5.filters import FilterConfig, decide_filter
from publication_v2.stage5.switches import (GradedConfig, decide_filter_gated, decide_graded_filter,
                                            decide_graded_mpc, weight)

T0 = datetime(2021, 3, 1, 12, tzinfo=timezone.utc)


def bundle(points, skill, width=80.):
    targets = tuple(T0 + timedelta(minutes=10 * (i + 1)) for i in range(6))
    newest = tuple(T0 - timedelta(minutes=10) for _ in range(6))
    prov = json.dumps({'released_skill': {'pooled_skill_score': skill}})
    return ForecastBundle(T0, tuple(points), tuple(max(0., p - width) for p in points), tuple(p + width for p in points),
                          .1, prov, T0, targets, T0, newest, newest, 'CONFORMAL_MARGINAL')


class Filter(unittest.TestCase):
    def test_no_action_when_estimate_equals_previous_grid_at_reference_soc(self):
        b = BatteryConfig()
        d = decide_filter('lp', bundle([1000.] * 6, .5), T0, b.capacity_kwh * .65, 1000., b, FilterConfig())
        self.assertEqual((d.charge_kw, d.discharge_kw), (0., 0.))

    def test_upward_step_is_smoothed_by_charging(self):
        b = BatteryConfig()
        d = decide_filter('lp', bundle([1600.] * 6, .5), T0, b.capacity_kwh * .65, 1000., b, FilterConfig(alpha=.5))
        self.assertAlmostEqual(d.charge_kw, 300.)
        self.assertEqual(validate_plan(d.plan, b, b.capacity_kwh * .65, 1) < 1e-9, True)

    def test_limits_respected_near_full(self):
        b = BatteryConfig()
        d = decide_filter('lp', bundle([2000.] * 6, .5), T0, b.max_energy_kwh - 1, 0., b, FilterConfig(alpha=.1))
        self.assertLessEqual(d.charge_kw * b.eta_charge * b.delta_t_hours, 1 + 1e-9)


class Switches(unittest.TestCase):
    def test_weight_is_clipped_linear(self):
        cfg = GradedConfig(base=FilterConfig())
        self.assertEqual([weight(s, cfg) for s in (None, -.2, 0., .15, .3, .9)], [0., 0., 0., .5, 1., 1.])

    def test_graded_mpc_plan_is_feasible_and_scaled(self):
        b = BatteryConfig()
        points = [900., 1300., 1700., 1700., 1700., 1700.]
        full = decide_graded_mpc('g', bundle(points, .9), T0, b.initial_energy_kwh, 900., b,
                                 GradedConfig(base=StochasticMPCConfig()))
        half = decide_graded_mpc('g', bundle(points, .15), T0, b.initial_energy_kwh, 900., b,
                                 GradedConfig(base=StochasticMPCConfig()))
        validate_plan(half.plan, b, b.initial_energy_kwh, 6)
        self.assertAlmostEqual(half.charge_kw, .5 * full.charge_kw, places=6)
        self.assertAlmostEqual(half.discharge_kw, .5 * full.discharge_kw, places=6)

    def test_zero_skill_idles(self):
        b = BatteryConfig()
        d = decide_graded_filter('g', bundle([1600.] * 6, -.1), T0, b.initial_energy_kwh, 1000., b,
                                 GradedConfig(base=FilterConfig()))
        self.assertEqual((d.charge_kw, d.discharge_kw), (0., 0.))
        g = decide_filter_gated('g', bundle([1600.] * 6, .05), T0, b.initial_energy_kwh, 1000., b, FilterConfig())
        self.assertEqual((g.charge_kw, g.discharge_kw), (0., 0.))

    def test_closed_loop_episode_with_new_controllers_is_safe(self):
        rng = np.random.default_rng(3)
        n = 400
        times = pd.date_range('2021-03-01', periods=n, freq='10min', tz='UTC')
        y = 1000 + 600 * np.sin(np.arange(n) / 15) + rng.normal(0, 40, n)
        pred = np.column_stack([np.r_[y[i + 1:], np.full(i + 1, np.nan)] for i in range(6)]) + rng.normal(0, 30, (n, 6))
        s = Series(times, y, np.clip(pred, 0, None), 'test')
        for decider, cfg in ((decide_filter, FilterConfig()), (decide_graded_filter, GradedConfig(base=FilterConfig())),
                             (decide_graded_mpc, GradedConfig(base=StochasticMPCConfig()))):
            m = run_episode(s, 100, 'x', decider=decider, decider_config=cfg)['metrics']
            self.assertEqual(m['soc_constraint_violations'] + m['power_constraint_violations'], 0)


class Economics(unittest.TestCase):
    def test_degradation_cost_and_break_even(self):
        a = economics.Assumptions(300., 6000., .8, 60.)
        self.assertAlmostEqual(a.degradation_eur_per_kwh, 300 / 9600)
        results = []
        for start in ('a', 'b'):
            results.append({'forecast': 'f', 'controller': 'uncontrolled', 'start': start,
                            'metrics': {'total_ramp_exceedance_kw': 100., 'ramp_violations': 2,
                                        'total_throughput_kwh': 0., 'conversion_loss_kwh': 0.}})
            results.append({'forecast': 'f', 'controller': 'c', 'start': start,
                            'metrics': {'total_ramp_exceedance_kw': 60., 'ramp_violations': 1,
                                        'total_throughput_kwh': 96., 'conversion_loss_kwh': 5.}})
        row = economics.table(results, {'central': a})[0]
        cost = 96 * 300 / 9600 + 5 * .06
        self.assertAlmostEqual(row['cost_eur_central'], cost)
        self.assertAlmostEqual(row['break_even_eur_per_kw_central'], cost / 40)


if __name__ == '__main__':
    unittest.main()
