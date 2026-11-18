"""Analytical synthetic MPC regressions; no measured data or efficacy claims."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from itertools import product
import unittest
from unittest.mock import patch

import numpy as np

from publication_v2.stage31 import controllers as ctrl
from publication_v2.stage31.battery import BatteryConfig, transition
from publication_v2.stage31.forecast import ForecastBundle
from publication_v2.stage31.evaluation import paired_comparisons, simulate
from publication_v2.stage31.scenarios import SyntheticScenario, make_scenarios


D = datetime(2035, 1, 1, tzinfo=timezone.utc)


def packet(point, lower=None, upper=None):
    point = tuple(float(x) for x in point)
    return ForecastBundle(
        issue_time=D, point_kw=point,
        lower_kw=point if lower is None else tuple(lower),
        upper_kw=point if upper is None else tuple(upper),
        alpha=.1, provenance='SYNTHETIC_ANALYTICAL_OBJECTIVE_REGRESSION',
        available_at=D,
        target_times=tuple(D + timedelta(minutes=10 * (i + 1)) for i in range(6)),
        model_available_at=D - timedelta(days=1))


class ScientificObjectiveTests(unittest.TestCase):
    def decision(self, controller, forecast, *, battery=None, config=None,
                 previous=1000., energy=None):
        battery = BatteryConfig() if battery is None else battery
        return ctrl.decide(controller, forecast, D,
                           battery.initial_energy_kwh if energy is None else energy,
                           previous, battery, ctrl.MPCConfig() if config is None else config)

    def assert_physical(self, action, battery):
        self.assertEqual(action.status, 'optimal', action.fallback_reason)
        plan = action.plan
        self.assertEqual(len(plan['energy_kwh']), 7)
        for i, (charge, discharge) in enumerate(zip(plan['charge_kw'], plan['discharge_kw'])):
            self.assertAlmostEqual(
                transition(battery, plan['energy_kwh'][i], charge, discharge),
                plan['energy_kwh'][i + 1], places=5)
            self.assertLessEqual(charge, battery.max_charge_kw + 1e-6)
            self.assertLessEqual(discharge, battery.max_discharge_kw + 1e-6)
            self.assertFalse(charge > 1e-6 and discharge > 1e-6)
        self.assertGreaterEqual(min(plan['energy_kwh']), battery.min_energy_kwh - 1e-6)
        self.assertLessEqual(max(plan['energy_kwh']), battery.max_energy_kwh + 1e-6)

    def test_zero_power_battery_gives_analytical_slacks_and_realised_first_anchor(self):
        battery = BatteryConfig(max_charge_kw=0., max_discharge_kw=0.)
        action = self.decision('deterministic', packet((1000., 1200., 500., 800., 100., 1000.)),
                               battery=battery, previous=300.)
        self.assert_physical(action, battery)
        # Ramps from the realised 300 kW anchor are 700,200,700,300,700,900 kW.
        expected = [500., 0., 500., 100., 500., 700.]
        np.testing.assert_allclose(action.plan['nominal_ramp_exceedance_kw'], expected, atol=1e-6)
        np.testing.assert_allclose(action.plan['worst_box_ramp_exceedance_kw'], expected, atol=1e-6)
        # Point forecasts duplicate the ramp term with weights 1 and .5.
        self.assertAlmostEqual(action.plan['objective'], 1.5 * 2300. / 1200., places=7)
        self.assertEqual(action.plan['energy_kwh'], [1300.] * 7)

    def test_fixed_interval_uncertainty_has_nonzero_analytical_floor_without_dispatch(self):
        battery = BatteryConfig(max_charge_kw=0., max_discharge_kw=0.)
        action = self.decision('fixed_margin', packet((1000.,) * 6),
                               battery=battery, previous=700.)
        self.assert_physical(action, battery)
        np.testing.assert_allclose(action.plan['nominal_ramp_exceedance_kw'], [100., 0., 0., 0., 0., 0.], atol=1e-6)
        # First interval compares [800,1200] with realised 700; later boxes
        # independently span 400 kW despite a constant nominal forecast.
        np.testing.assert_allclose(action.plan['worst_box_ramp_exceedance_kw'], [300., 200., 200., 200., 200., 200.], atol=1e-6)
        self.assertAlmostEqual(action.plan['objective'], (100. + .5 * 1300.) / 1200., places=7)

    def test_original_linear_rows_and_epigraph_slacks_bound_independent_corner_ramps(self):
        battery, config = BatteryConfig(), ctrl.MPCConfig()
        point = np.asarray((500., 1500., 400., 1700., 600., 1200.))
        lower = np.asarray((100., 1000., 100., 1000., 100., 600.))
        upper = np.asarray((900., 2000., 700., 2200., 1100., 1600.))
        objective, integers, bounds, constraints, groups = ctrl._formulate(
            point, lower, upper, 1300., 1000., battery, config)
        result = ctrl.milp(objective, integrality=integers, bounds=bounds, constraints=constraints,
                           options={'mip_rel_gap': config.solver_mip_rel_gap})
        self.assertEqual(result.status, 0, result.message)
        values = constraints.A @ result.x
        self.assertTrue(np.all(values >= np.asarray(constraints.lb) - 1e-5))
        self.assertTrue(np.all(values <= np.asarray(constraints.ub) + 1e-5))
        net = result.x[groups['discharge']] - result.x[groups['charge']]
        grid = point + net
        nominal = np.maximum(0., np.abs(np.diff(np.r_[1000., grid])) - 200.)
        corner_ramps = []
        for corner in product((0, 1), repeat=6):
            selected = np.where(corner, upper, lower) + net
            corner_ramps.append(np.maximum(0., np.abs(np.diff(np.r_[1000., selected])) - 200.))
        worst = np.max(corner_ramps, axis=0)
        self.assertTrue(np.all(result.x[groups['nominal_excess']] >= nominal - 1e-5))
        self.assertTrue(np.all(result.x[groups['worst_excess']] >= worst - 1e-5))
        np.testing.assert_allclose(result.x[groups['nominal_excess']], nominal, atol=1e-5)
        np.testing.assert_allclose(result.x[groups['worst_excess']], worst, atol=1e-5)

    def test_zero_weight_slacks_may_be_loose_if_rows_and_solver_certificate_remain_valid(self):
        config = ctrl.MPCConfig(ramp_weight=0., uncertainty_weight=0.,
                               soc_margin_weight=0., terminal_weight=0., throughput_weight=1.)
        forecast = packet((1000., 1600., 500., 1700., 600., 1200.))
        battery = BatteryConfig()
        _, _, _, _, groups = ctrl._formulate(np.asarray(forecast.point_kw),
            np.asarray(forecast.lower_kw), np.asarray(forecast.upper_kw), 1300., 1000., battery, config)
        native_solver = ctrl.milp
        modified_vectors = []

        def loose_feasible_slacks(*args, **kwargs):
            result = native_solver(*args, **kwargs)
            self.assertEqual(result.status, 0)
            result.x = result.x.copy()
            result.x[groups['nominal_excess']] += 5000.
            result.x[groups['worst_excess']] += 5000.
            modified_vectors.append(result.x.copy())
            # These columns have zero coefficients, so fun, dual bound and gap
            # remain valid; rejecting loose epigraphs would reject a feasible optimum.
            return result

        with patch.object(ctrl, 'milp', side_effect=loose_feasible_slacks):
            action = self.decision('adaptive', forecast, config=config)
        self.assertEqual(len(modified_vectors), 1)
        self.assertGreater(min(modified_vectors[0][groups['nominal_excess']]), 4000.)
        self.assert_physical(action, battery)
        self.assertAlmostEqual(action.plan['objective'], 0., places=7)
        self.assertEqual(sum(action.plan['charge_kw']) + sum(action.plan['discharge_kw']), 0.)

    def test_uniform_physical_scaling_preserves_dimensionless_adaptive_optimum(self):
        battery = BatteryConfig()
        forecast = packet((500., 1500., 400., 1700., 600., 1200.),
                          (100., 1000., 100., 1000., 100., 600.),
                          (900., 2000., 700., 2200., 1100., 1600.))
        config = ctrl.MPCConfig(grid_min_kw=0., grid_max_kw=2500.)
        a = self.decision('adaptive', forecast, config=config)
        doubled_battery = replace(battery, capacity_kwh=4000., max_charge_kw=2000., max_discharge_kw=2000.)
        doubled_forecast = packet(tuple(2*x for x in forecast.point_kw),
                                  tuple(2*x for x in forecast.lower_kw),
                                  tuple(2*x for x in forecast.upper_kw))
        b = self.decision('adaptive', doubled_forecast, battery=doubled_battery,
                          config=replace(config, ramp_limit_kw=400., fixed_margin_kw=400.,
                                         grid_min_kw=0., grid_max_kw=5000.), previous=2000.)
        self.assert_physical(a, battery)
        self.assert_physical(b, doubled_battery)
        self.assertAlmostEqual(a.plan['objective'], b.plan['objective'], places=6)
        # Multiple optimal dispatches are allowed: compare objective and hard
        # constraints, rather than asserting an unjustified unique optimizer.
        for action, cap in ((a, 2500.), (b, 5000.)):
            self.assertGreaterEqual(min(action.plan['lower_grid_kw']), -1e-5)
            self.assertLessEqual(max(action.plan['upper_grid_kw']), cap + 1e-5)

    def test_deterministic_controller_ignores_valid_but_different_uncertainty_bounds(self):
        point = (1000., 1600., 500., 1700., 600., 1200.)
        tight = packet(point)
        broad = packet(point, (0.,) * 6, tuple(x + 3000. for x in point))
        a, b = self.decision('deterministic', tight), self.decision('deterministic', broad)
        self.assert_physical(a, BatteryConfig())
        self.assert_physical(b, BatteryConfig())
        np.testing.assert_allclose(a.plan['charge_kw'], b.plan['charge_kw'], atol=1e-6)
        np.testing.assert_allclose(a.plan['discharge_kw'], b.plan['discharge_kw'], atol=1e-6)
        self.assertEqual(b.plan['lower_wind_kw'], list(point))
        self.assertEqual(b.plan['upper_wind_kw'], list(point))
        self.assertAlmostEqual(a.plan['objective'], b.plan['objective'], places=7)

    def test_adaptive_asymmetric_intervals_and_positive_risk_weight_change_policy(self):
        forecast = packet((1000.,) * 6, (900.,) * 6, (1600.,) * 6)
        base = ctrl.MPCConfig(uncertainty_weight=0., terminal_weight=0., soc_margin_weight=0.)
        no_risk = self.decision('adaptive', forecast, config=base)
        risk = self.decision('adaptive', forecast, config=replace(base, uncertainty_weight=1.))
        self.assert_physical(no_risk, BatteryConfig())
        self.assert_physical(risk, BatteryConfig())
        self.assertAlmostEqual(no_risk.charge_kw + no_risk.discharge_kw, 0., places=6)
        self.assertGreater(risk.charge_kw, 1.)
        self.assertEqual(risk.discharge_kw, 0.)
        self.assertLess(sum(risk.plan['worst_box_ramp_exceedance_kw']),
                        sum(no_risk.plan['worst_box_ramp_exceedance_kw']))
        # There is deliberately no realised/future observation in this fixture.
        self.assertEqual(risk.plan['point_wind_kw'], list(forecast.point_kw))

    def comparison_runs(self):
        scenario = make_scenarios(seed=491, steps=8)[0]
        return [simulate(scenario, name) for name in ctrl.CONTROLLERS]

    def test_pair_guard_rejects_changed_decision_time_even_when_forecast_hash_matches(self):
        runs = self.comparison_runs()
        runs[1]['rows'][0]['decision_time'] = '2031-01-01T00:00:01+00:00'
        with self.assertRaises(ValueError):
            paired_comparisons(runs)

    def test_pair_guard_rejects_different_initial_realised_grid_anchor(self):
        runs = self.comparison_runs()
        runs[1]['rows'][0]['previous_grid_kw'] += 1.
        with self.assertRaises(ValueError):
            paired_comparisons(runs)

    def test_battery_safe_fallback_still_counts_realised_ramp_exceedance(self):
        scenario = SyntheticScenario(name='synthetic_fallback_ramp_fixture',
            wind_kw=(2000.,), initial_history_kw=(1000.,) * 6, seed=491,
            faults=((0, 'missing'),))
        run = simulate(scenario, 'adaptive')
        row, metrics = run['rows'][0], run['metrics']
        self.assertTrue(row['fallback'])
        self.assertEqual(row['fallback_reason'], 'missing_forecast')
        self.assertEqual((row['charge_kw'], row['discharge_kw']), (0., 0.))
        self.assertEqual(row['energy_after_kwh'], 1300.)
        self.assertEqual(metrics['safe_fallback_events'], 1)
        self.assertEqual(metrics['optimisation_failures'], 0)
        self.assertEqual(metrics['ramp_violations'], 1)
        self.assertEqual(metrics['total_ramp_exceedance_kw'], 800.)
        self.assertEqual(metrics['maximum_ramp_kw'], 1000.)
        self.assertEqual(metrics['intervals'], 1)

    def test_sixth_state_constraint_prevents_late_only_overcharge(self):
        # The exact grid constraint forces zero dispatch for five steps. At the
        # sixth, exporting 1000 from wind1100 requires charging100 kW; this is
        # impossible from full SOC if the terminal state is properly bounded.
        battery = BatteryConfig(initial_soc=.9)
        forecast = packet((1000., 1000., 1000., 1000., 1000., 1100.))
        action = self.decision('deterministic', forecast, battery=battery,
                               config=ctrl.MPCConfig(grid_min_kw=1000., grid_max_kw=1000.))
        self.assertTrue(action.fallback)
        self.assertTrue(action.optimization_failed)
        self.assertEqual(action.solver_status, 2)
        self.assertEqual((action.charge_kw, action.discharge_kw), (0., 0.))
        self.assertEqual(transition(battery, 1800., action.charge_kw, action.discharge_kw), 1800.)

    def test_uniform_objective_weight_scaling_changes_cost_but_not_optimal_value_order(self):
        forecast = packet((900., 1400., 700., 1700., 600., 1100.),
                          (800., 1000., 500., 1100., 400., 700.),
                          (1300., 2000., 1100., 2200., 1000., 1800.))
        config = ctrl.MPCConfig()
        scaled = replace(config, ramp_weight=7*config.ramp_weight,
            throughput_weight=7*config.throughput_weight,
            soc_margin_weight=7*config.soc_margin_weight,
            uncertainty_weight=7*config.uncertainty_weight,
            terminal_weight=7*config.terminal_weight)
        a = self.decision('adaptive', forecast, config=config)
        b = self.decision('adaptive', forecast, config=scaled)
        self.assert_physical(a, BatteryConfig())
        self.assert_physical(b, BatteryConfig())
        self.assertGreater(a.plan['objective'], 0.)
        self.assertAlmostEqual(7*a.plan['objective'], b.plan['objective'], places=6)


if __name__ == '__main__':
    unittest.main()
