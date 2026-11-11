"""Independent finite-box properties; synthetic software checks, not efficacy."""
from datetime import datetime, timedelta, timezone
from itertools import product
import unittest

import numpy as np

from publication_v2.stage31.battery import BatteryConfig
from publication_v2.stage31.controllers import MPCConfig, decide
from publication_v2.stage31.forecast import ForecastBundle


class BoxEnvelopePropertyTests(unittest.TestCase):
    def test_all_64_corner_paths_satisfy_logged_envelope_grid_and_energy(self):
        battery = BatteryConfig()
        decision = datetime(2031, 1, 1, tzinfo=timezone.utc)
        point = (500., 1500., 400., 1700., 600., 1200.)
        lower = (100., 1000., 100., 1000., 100., 600.)
        upper = (900., 2000., 700., 2200., 1100., 1600.)
        packet = ForecastBundle(
            decision, point, lower, upper, .1, 'SYNTHETIC_INDEPENDENT_CORNER_AUDIT',
            decision, tuple(decision + timedelta(minutes=10 * (h + 1)) for h in range(6)),
            decision - timedelta(days=1))
        action = decide('adaptive', packet, decision, 1300., 1000., battery,
                        MPCConfig(grid_min_kw=0., grid_max_kw=3000.))
        self.assertEqual(action.status, 'optimal')
        self.assertFalse(action.fallback)
        plan = action.plan
        charge = np.asarray(plan['charge_kw'])
        discharge = np.asarray(plan['discharge_kw'])
        net = discharge - charge
        envelope = np.asarray(plan['worst_box_ramp_exceedance_kw'])
        losses = float(np.sum((1 - battery.eta_charge) * charge
                             + (1 / battery.eta_discharge - 1) * discharge)
                       * battery.delta_t_hours)
        corner_excesses = []
        for corner in product((0, 1), repeat=6):
            with self.subTest(corner=corner):
                wind = np.asarray([upper[i] if selected else lower[i]
                                   for i, selected in enumerate(corner)])
                grid = wind + net
                excess = np.maximum(0., np.abs(np.diff(np.r_[1000., grid])) - 200.)
                self.assertTrue(np.all(grid >= -1e-5))
                self.assertTrue(np.all(grid <= 3000. + 1e-5))
                self.assertTrue(np.all(excess <= envelope + 1e-5))
                self.assertLessEqual(float(excess.sum()), float(envelope.sum()) + 1e-5)
                inventory_change = plan['energy_kwh'][-1] - 1300.
                self.assertAlmostEqual(float(np.sum(wind - grid) * battery.delta_t_hours),
                                       inventory_change + losses, places=7)
                corner_excesses.append(excess)
        self.assertEqual(len(corner_excesses), 64)
        np.testing.assert_allclose(np.max(corner_excesses, axis=0), envelope,
                                   rtol=0., atol=1e-6)

    def test_sum_of_per_step_envelopes_is_not_exact_trajectory_minimax(self):
        # A two-step mathematical counterexample to an overstated risk claim.
        # Both wind values are in [0,1000] kW, shared dispatch u=(0,1000),
        # prior grid is 0 kW and the ramp reference is 200 kW per interval.
        # The per-step maxima require conflicting values of the first wind.
        per_step = []
        for wind in product((0., 1000.), repeat=2):
            grid = np.asarray(wind) + np.asarray((0., 1000.))
            per_step.append(np.maximum(0., np.abs(np.diff(np.r_[0., grid])) - 200.))
        envelope_sum = float(np.max(per_step, axis=0).sum())
        exact_corner_trajectory_max = max(float(v.sum()) for v in per_step)
        self.assertEqual(envelope_sum, 2600.)
        self.assertEqual(exact_corner_trajectory_max, 1800.)
        self.assertGreater(envelope_sum, exact_corner_trajectory_max)


if __name__ == '__main__':
    unittest.main()
