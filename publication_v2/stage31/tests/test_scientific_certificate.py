"""Synthetic Stage 3.1.1 raw-MILP and optimality-certificate regressions."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
import unittest
from unittest.mock import patch

import numpy as np
from scipy.optimize import milp

from publication_v2.stage31.battery import BatteryConfig
from publication_v2.stage31.controllers import MPCConfig, _formulate, decide
from publication_v2.stage31.forecast import ForecastBundle

D = datetime(2035, 1, 1, tzinfo=timezone.utc)


def packet(point=(1000.,) * 6):
    point = tuple(point)
    return ForecastBundle(D, point, point, point, .1, 'SYNTHETIC_CERTIFICATE_TEST', D,
        tuple(D + timedelta(minutes=10 * (i + 1)) for i in range(6)), D,
        uncertainty_kind='POINT_ONLY')


class ScientificCertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.battery = BatteryConfig()
        cls.config = MPCConfig()
        cls.forecast = packet()
        cls.solution = cls.solve_fixture(cls.forecast)
        if cls.solution.status != 0 or not cls.solution.success:
            raise AssertionError('Native synthetic fixture must solve optimally')

    @classmethod
    def solve_fixture(cls, forecast):
        point = np.asarray(forecast.point_kw)
        c, integer, bounds, constraints, _ = _formulate(point, point, point, 1300.,
            1000., cls.battery, cls.config)
        return milp(c, integrality=integer, bounds=bounds, constraints=constraints,
            options={'mip_rel_gap': cls.config.solver_mip_rel_gap})

    def mutated(self, change, *, forecast=None, solution=None, config=None):
        altered = deepcopy(self.solution if solution is None else solution)
        change(altered)
        with patch('publication_v2.stage31.controllers.milp', return_value=altered):
            return decide('deterministic', self.forecast if forecast is None else forecast,
                D, 1300., 1000., self.battery, self.config if config is None else config)

    def rejected(self, change, **kwargs):
        result = self.mutated(change, **kwargs)
        self.assertTrue(result.fallback, result)
        self.assertTrue(result.optimization_failed)
        self.assertEqual((result.charge_kw, result.discharge_kw), (0., 0.))
        self.assertTrue(result.fallback_reason.startswith('invalid_solver_plan'))
        return result

    def test_native_certificate_passes_and_records_numerical_checks(self):
        result = self.mutated(lambda s: None)
        self.assertEqual(result.status, 'optimal', result.fallback_reason)
        plan = result.plan
        self.assertLessEqual(plan['solver_maximum_bound_violation'], 1e-5)
        self.assertLessEqual(plan['solver_maximum_constraint_violation'], 1e-5)
        self.assertLessEqual(plan['solver_maximum_integrality_violation'], 1e-6)
        self.assertLessEqual(plan['solver_mip_gap'], self.config.solver_mip_rel_gap + 1e-9)
        self.assertTrue(math.isfinite(plan['solver_mip_dual_bound']))
        self.assertEqual(plan['solver_linear_objective'], plan['solver_objective'])

    def test_negative_auxiliary_slack_is_rejected_by_original_bounds(self):
        result = self.rejected(lambda s: s.x.__setitem__(24, -1000.))
        self.assertIn('variable bounds', result.fallback_reason)

    def test_ramp_slack_cannot_understate_positive_threshold_exceedance(self):
        f = packet((3000.,) * 6)
        solution = self.solve_fixture(f)
        self.assertGreater(solution.x[24], 1.)
        result = self.rejected(lambda s: s.x.__setitem__(24, 0.), forecast=f, solution=solution)
        self.assertIn('linear constraints', result.fallback_reason)

    def test_energy_row_violation_is_detected_before_physical_reconstruction(self):
        result = self.rejected(lambda s: s.x.__setitem__(12, s.x[12] + 1.))
        self.assertIn('linear constraints', result.fallback_reason)

    def test_fractional_mode_is_rejected_by_integrality(self):
        result = self.rejected(lambda s: s.x.__setitem__(18, .5))
        self.assertIn('integrality', result.fallback_reason)

    def test_positive_unused_slack_cannot_disagree_with_reported_linear_objective(self):
        result = self.rejected(lambda s: s.x.__setitem__(24, s.x[24] + 100.))
        self.assertIn('Raw MILP objective', result.fallback_reason)

    def test_reported_objective_must_equal_dot_product(self):
        result = self.rejected(lambda s: s.update(fun=s.fun + .5))
        self.assertIn('Raw MILP objective', result.fallback_reason)

    def test_nonfinite_incumbent_is_rejected(self):
        self.rejected(lambda s: s.x.__setitem__(24, float('nan')))

    def test_incomplete_incumbent_is_rejected(self):
        self.rejected(lambda s: s.update(x=s.x[:-1]))

    def test_missing_gap_is_rejected(self):
        self.rejected(lambda s: s.pop('mip_gap'))

    def test_none_gap_is_rejected(self):
        self.rejected(lambda s: s.update(mip_gap=None))

    def test_nonfinite_negative_and_excess_gaps_are_rejected(self):
        for gap in (float('nan'), float('inf'), -.1, .5, True):
            with self.subTest(gap=gap):
                self.rejected(lambda s: s.update(mip_gap=gap))

    def test_missing_dual_bound_is_rejected(self):
        self.rejected(lambda s: s.pop('mip_dual_bound'))

    def test_nonfinite_dual_bound_is_rejected(self):
        for dual in (None, float('nan'), float('inf'), float('-inf'), True):
            with self.subTest(dual=dual):
                self.rejected(lambda s: s.update(mip_dual_bound=dual))

    def test_dual_bound_above_minimization_incumbent_is_rejected(self):
        result = self.rejected(lambda s: s.update(mip_dual_bound=s.fun + 1.))
        self.assertIn('dual bound exceeds', result.fallback_reason)

    def test_gap_and_dual_bound_must_be_mutually_consistent(self):
        result = self.rejected(lambda s: s.update(mip_dual_bound=s.fun - 1., mip_gap=0.))
        self.assertIn('gap and dual bound are inconsistent', result.fallback_reason)

    def test_missing_node_count_is_rejected(self):
        self.rejected(lambda s: s.pop('mip_node_count'))

    def test_node_count_must_be_nonnegative_integer(self):
        for count in (-1, .5, 1., True, None, float('nan')):
            with self.subTest(count=count):
                self.rejected(lambda s: s.update(mip_node_count=count))

    def test_limit_and_failure_statuses_discard_even_feasible_incumbents(self):
        for status in (1, 2, 3, 4):
            with self.subTest(status=status):
                result = self.mutated(lambda s: s.update(status=status, success=False))
                self.assertTrue(result.fallback)
                self.assertTrue(result.optimization_failed)
                self.assertEqual(result.fallback_reason, 'solver_status_' + str(status))
                self.assertIsNone(result.plan)
                self.assertEqual((result.charge_kw, result.discharge_kw), (0., 0.))

    def test_false_boolean_status_is_not_integer_zero(self):
        self.rejected(lambda s: s.update(status=False))

    def test_truthy_string_success_is_not_valid_termination_metadata(self):
        self.rejected(lambda s: s.update(success='yes'))

    def test_nonzero_gap_within_explicit_tolerance_is_logged_honestly(self):
        f = packet((3000.,) * 6)
        solution = self.solve_fixture(f)
        gap = 5e-5
        result = self.mutated(lambda s: s.update(mip_gap=gap, mip_dual_bound=s.fun - gap * abs(s.fun)),
            forecast=f, solution=solution, config=replace(self.config, solver_mip_rel_gap=1e-4))
        self.assertEqual(result.status, 'optimal', result.fallback_reason)
        self.assertEqual(result.plan['solver_mip_gap'], gap)
        self.assertLessEqual(result.plan['solver_mip_dual_bound'], result.plan['solver_objective'])

    def test_all_three_native_mpc_variants_retain_valid_certificates(self):
        f = packet((400., 2300., 600., 1800., 300., 2100.))
        for controller in ('deterministic', 'fixed_margin', 'adaptive'):
            with self.subTest(controller=controller):
                result = decide(controller, f, D, 1300., 1000., self.battery, self.config)
                self.assertEqual(result.status, 'optimal', result.fallback_reason)
                self.assertLessEqual(result.plan['solver_mip_gap'], 1e-8 + 1e-9)
                self.assertGreaterEqual(result.plan['solver_mip_node_count'], 0)


if __name__ == '__main__':
    unittest.main()
