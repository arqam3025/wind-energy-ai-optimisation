"""Synthetic optimization/contract regressions; never historical SCADA data."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from publication_v2.stage31.battery import BatteryConfig, PhysicalError, transition
from publication_v2.stage31.forecast import ForecastBundle
from publication_v2.stage31.controllers import CONTROLLERS, MPCConfig, decide

D = datetime(2035, 1, 1, tzinfo=timezone.utc)


def forecast(point=(1000.,) * 6, lower=None, upper=None):
    point = tuple(point)
    return ForecastBundle(issue_time=D, point_kw=point,
        lower_kw=point if lower is None else tuple(lower), upper_kw=point if upper is None else tuple(upper),
        alpha=.1, provenance='SYNTHETIC_TEST_ONLY_NO_MEASUREMENTS', available_at=D,
        target_times=tuple(D + timedelta(minutes=10 * (i + 1)) for i in range(6)),
        model_available_at=D - timedelta(days=1), uncertainty_kind='SYNTHETIC_INTERVALS')


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.battery = BatteryConfig()
        self.config = MPCConfig()

    def decision(self, name, bundle=None, energy=None, previous=1000., config=None, battery=None):
        b = battery or self.battery
        return decide(name, forecast() if bundle is None else bundle, D,
                      b.initial_energy_kwh if energy is None else energy, previous,
                      b, config or self.config)

    def test_uncontrolled_is_exact_zero_dispatch_even_without_forecasts(self):
        result = decide('uncontrolled', None, D, 1300., 900., self.battery, self.config)
        self.assertEqual((result.charge_kw, result.discharge_kw), (0., 0.))
        self.assertFalse(result.fallback)
        self.assertFalse(result.optimization_failed)
        self.assertEqual(result.status, 'baseline')
        self.assertIsNone(result.plan)

    def test_stable_point_forecast_has_zero_optimal_dispatch(self):
        result = self.decision('deterministic')
        self.assertEqual(result.status, 'optimal', result.fallback_reason)
        self.assertAlmostEqual(result.charge_kw + result.discharge_kw, 0., places=6)
        self.assertAlmostEqual(result.plan['objective'], 0., places=6)
        self.assertEqual(len(result.plan['energy_kwh']), 7)

    def test_complete_plan_enforces_energy_power_soc_and_exclusive_modes(self):
        f = forecast((2500., 200., 2700., 100., 2500., 300.))
        for controller in ('deterministic', 'fixed_margin', 'adaptive'):
            with self.subTest(controller=controller):
                result = self.decision(controller, f, previous=300.)
                self.assertEqual(result.status, 'optimal', result.fallback_reason)
                plan = result.plan
                self.assertEqual(len(plan['charge_kw']), 6)
                energy = self.battery.initial_energy_kwh
                self.assertAlmostEqual(plan['energy_kwh'][0], energy)
                for i, (charge, discharge) in enumerate(zip(plan['charge_kw'], plan['discharge_kw'])):
                    self.assertLessEqual(charge, 1000. + 1e-6)
                    self.assertLessEqual(discharge, 1000. + 1e-6)
                    self.assertFalse(charge > 1e-6 and discharge > 1e-6)
                    energy = transition(self.battery, energy, charge, discharge)
                    self.assertAlmostEqual(energy, plan['energy_kwh'][i + 1], places=5)
                    self.assertGreaterEqual(energy, 800. - 1e-6)
                    self.assertLessEqual(energy, 1800. + 1e-6)
                self.assertAlmostEqual(result.charge_kw, plan['charge_kw'][0])
                self.assertAlmostEqual(result.discharge_kw, plan['discharge_kw'][0])

    def test_zero_width_fixed_and_adaptive_reduce_to_same_deterministic_problem(self):
        f = forecast((400., 2300., 600., 1800., 300., 2100.))
        cfg = replace(self.config, fixed_margin_kw=0.)
        results = [self.decision(n, f, previous=300., config=cfg) for n in ('deterministic', 'fixed_margin', 'adaptive')]
        self.assertTrue(all(r.status == 'optimal' for r in results))
        for result in results[1:]:
            self.assertAlmostEqual(result.plan['objective'], results[0].plan['objective'], places=6)
            np.testing.assert_allclose(result.plan['charge_kw'], results[0].plan['charge_kw'], atol=1e-5)
            np.testing.assert_allclose(result.plan['discharge_kw'], results[0].plan['discharge_kw'], atol=1e-5)

    def test_controller_variants_use_declared_forecast_envelopes(self):
        point = (1000.,) * 6
        f = forecast(point, (700., 500., 800., 400., 600., 300.), (1400., 1800., 1600., 1900., 1500., 2200.))
        expected = {'deterministic': (list(point), list(point)),
                    'fixed_margin': ([800.] * 6, [1200.] * 6),
                    'adaptive': (list(f.lower_kw), list(f.upper_kw))}
        for name, (lower, upper) in expected.items():
            result = self.decision(name, f)
            self.assertEqual(result.status, 'optimal', result.fallback_reason)
            self.assertEqual(result.plan['lower_wind_kw'], lower)
            self.assertEqual(result.plan['upper_wind_kw'], upper)
            self.assertTrue(all(w + 1e-7 >= n for w, n in zip(
                result.plan['worst_box_ramp_exceedance_kw'], result.plan['nominal_ramp_exceedance_kw'])))

    def test_optional_terminal_target_is_soft_and_physical_terminal_limit_is_hard(self):
        f = forecast((3000.,) * 6)
        cfg = replace(self.config, terminal_soc=.9, terminal_weight=0.)
        result = self.decision('deterministic', f, energy=800., previous=0., config=cfg)
        self.assertEqual(result.status, 'optimal', result.fallback_reason)
        self.assertGreaterEqual(result.plan['energy_kwh'][-1], 800. - 1e-6)
        self.assertLessEqual(result.plan['energy_kwh'][-1], 1800. + 1e-6)
        self.assertEqual(result.plan['weighted_objective_components']['terminal_deviation'], 0.)

    def test_default_soft_ramp_problem_is_feasible_at_soc_bounds_with_extreme_boxes(self):
        f = forecast((5000., 0., 5000., 0., 5000., 0.), (0.,) * 6, (10000.,) * 6)
        for energy in (800., 1800.):
            for name in ('deterministic', 'fixed_margin', 'adaptive'):
                with self.subTest(energy=energy, controller=name):
                    result = self.decision(name, f, energy=energy, previous=10000.)
                    self.assertEqual(result.status, 'optimal', result.fallback_reason)
                    self.assertFalse(result.optimization_failed)

    def test_missing_forecast_fallback_is_battery_safe_and_not_a_solver_failure(self):
        result = decide('adaptive', None, D, 800., 1000., self.battery, self.config)
        self.assertTrue(result.fallback)
        self.assertFalse(result.optimization_failed)
        self.assertEqual(result.fallback_reason, 'missing_forecast')
        self.assertEqual(transition(self.battery, 800., result.charge_kw, result.discharge_kw), 800.)

    def test_future_availability_and_invalid_intervals_are_rejected_before_solving(self):
        cases = [replace(forecast(), available_at=D + timedelta(seconds=1)),
                 replace(forecast(), lower_kw=(1500.,) * 6)]
        with patch('publication_v2.stage31.controllers.milp') as solver:
            for f in cases:
                result = self.decision('adaptive', f)
                self.assertTrue(result.fallback)
                self.assertFalse(result.optimization_failed)
                self.assertTrue(result.fallback_reason.startswith('invalid_forecast'))
            solver.assert_not_called()

    def test_conflicting_export_envelope_returns_infeasible_zero_dispatch_fallback(self):
        f = forecast((1000.,) * 6, (0.,) * 6, (2500.,) * 6)
        cfg = replace(self.config, grid_min_kw=0., grid_max_kw=1000.)
        result = self.decision('adaptive', f, config=cfg)
        self.assertTrue(result.fallback)
        self.assertTrue(result.optimization_failed)
        self.assertEqual(result.solver_status, 2)
        self.assertEqual((result.charge_kw, result.discharge_kw), (0., 0.))
        self.assertIsNone(result.plan)

    def test_optional_grid_bounds_are_enforced_for_entire_supplied_box(self):
        f = forecast((1000.,) * 6, (900.,) * 6, (1100.,) * 6)
        cfg = replace(self.config, grid_min_kw=500., grid_max_kw=1500.)
        result = self.decision('adaptive', f, config=cfg)
        self.assertEqual(result.status, 'optimal', result.fallback_reason)
        self.assertTrue(all(x >= 500. - 1e-6 for x in result.plan['lower_grid_kw']))
        self.assertTrue(all(x <= 1500. + 1e-6 for x in result.plan['upper_grid_kw']))

    def test_solver_exception_and_limit_status_are_counted_as_optimization_failures(self):
        with patch('publication_v2.stage31.controllers.milp', side_effect=RuntimeError('synthetic failure')):
            result = self.decision('deterministic')
            self.assertTrue(result.optimization_failed)
            self.assertTrue(result.fallback_reason.startswith('solver_exception'))
        with patch('publication_v2.stage31.controllers.milp', return_value=SimpleNamespace(status=1, success=False, message='time limit')):
            result = self.decision('deterministic')
            self.assertTrue(result.optimization_failed)
            self.assertEqual(result.solver_status, 1)
            self.assertEqual(result.fallback_reason, 'solver_status_1')

    def test_postvalidation_rejects_an_invalid_terminal_state_even_when_first_action_is_valid(self):
        vector = np.zeros(49)
        vector[12:18] = 1300.
        vector[17] = 0.
        fake = SimpleNamespace(status=0, success=True, message='synthetic invalid plan', x=vector, fun=0.)
        with patch('publication_v2.stage31.controllers.milp', return_value=fake):
            result = self.decision('deterministic')
        self.assertTrue(result.optimization_failed)
        self.assertTrue(result.fallback_reason.startswith('invalid_solver_plan'))
        self.assertEqual((result.charge_kw, result.discharge_kw), (0., 0.))

    def test_receding_horizon_plan_uses_supplied_new_state_and_grid_anchor(self):
        f = forecast((2200., 1800., 1500., 1200., 900., 600.))
        low = self.decision('deterministic', f, energy=800., previous=2000.)
        high = self.decision('deterministic', f, energy=1800., previous=0.)
        self.assertEqual(low.status, 'optimal', low.fallback_reason)
        self.assertEqual(high.status, 'optimal', high.fallback_reason)
        self.assertEqual(low.plan['energy_kwh'][0], 800.)
        self.assertEqual(high.plan['energy_kwh'][0], 1800.)
        self.assertNotEqual((low.charge_kw, low.discharge_kw), (high.charge_kw, high.discharge_kw))

    def test_heuristic_uses_first_point_only_and_respects_battery_boundaries(self):
        f = forecast((2200., 200., 3000., 0., 100., 4000.))
        f2 = forecast((2200., 9999., 9999., 9999., 9999., 9999.))
        for energy in (800., 1300., 1800.):
            a = self.decision('heuristic', f, energy=energy, previous=1000.)
            b = self.decision('heuristic', f2, energy=energy, previous=1000.)
            self.assertEqual((a.charge_kw, a.discharge_kw), (b.charge_kw, b.discharge_kw))
            transition(self.battery, energy, a.charge_kw, a.discharge_kw)
            self.assertFalse(a.charge_kw > 0 and a.discharge_kw > 0)

    def test_objective_is_dimensionless_under_consistent_power_energy_scaling(self):
        f = forecast((100., 2000., 300., 2400., 500., 1800.))
        cfg = replace(self.config, fixed_margin_kw=0.)
        a = self.decision('deterministic', f, previous=100., config=cfg)
        doubled = replace(self.battery, capacity_kwh=4000., max_charge_kw=2000., max_discharge_kw=2000.)
        b = self.decision('deterministic', forecast(tuple(2*x for x in f.point_kw)), previous=200.,
                          config=replace(cfg, ramp_limit_kw=400.), battery=doubled)
        self.assertEqual(a.status, 'optimal', a.fallback_reason)
        self.assertEqual(b.status, 'optimal', b.fallback_reason)
        self.assertAlmostEqual(a.plan['objective'], b.plan['objective'], places=5)

    def test_integer_horizon_and_explicit_configuration_types_are_required(self):
        for bad in (6.0, True, '6'):
            with self.assertRaises(ValueError):
                MPCConfig(horizon_steps=bad)
        for bad_battery, bad_config in ((False, self.config), (self.battery, {})):
            with self.assertRaises(ValueError):
                decide('adaptive', forecast(), D, 1300., 1000., bad_battery, bad_config)

    def test_postvalidation_rejects_out_of_range_binary_mode(self):
        vector = np.zeros(49)
        vector[12:18] = 1300.
        vector[18:24] = 2.
        fake = SimpleNamespace(status=0, success=True, message='synthetic invalid mode', x=vector, fun=0.)
        with patch('publication_v2.stage31.controllers.milp', return_value=fake):
            result = self.decision('deterministic')
        self.assertTrue(result.optimization_failed)
        self.assertTrue(result.fallback_reason.startswith('invalid_solver_plan'))

    def test_invalid_initial_state_and_configuration_are_not_disguised_as_safe_fallback(self):
        with self.assertRaises((PhysicalError, ValueError)):
            self.decision('adaptive', energy=700.)
        with self.assertRaises(ValueError):
            self.decision('unknown')
        with self.assertRaises(ValueError):
            MPCConfig(ramp_weight=0., throughput_weight=0., soc_margin_weight=0., uncertainty_weight=0., terminal_weight=0.)
        with self.assertRaises(ValueError):
            self.decision('adaptive', config=replace(self.config, soc_buffer_fraction=.3))
        with self.assertRaises(ValueError):
            MPCConfig(grid_min_kw=1000., grid_max_kw=0.)


if __name__ == '__main__':
    unittest.main()
