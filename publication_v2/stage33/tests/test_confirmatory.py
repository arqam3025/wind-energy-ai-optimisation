"""Confirmatory machinery: refusal rules, Holm adjustment and hypothesis definitions."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from publication_v2.stage33 import confirmatory
from publication_v2.stage33.confirmatory_analysis import holm, primary_tests
from publication_v2.stage33.experiment import DEVELOPMENT_SEEDS


def fake_results(effect):
    """Rows with known paired structure: primary = uncontrolled + effect[forecast]."""
    rows = []
    for forecast in confirmatory.SKILFUL + confirmatory.UNSKILLED:
        for seed in range(30):
            base = 400. + 13 * seed
            values = {'uncontrolled': (base, 0.), 'adaptive': (base * .1, 900. + seed),
                      'stochastic_skill': (base + effect[forecast] + (seed % 5) - 2, 500. + seed)}
            for controller, (exceedance, throughput) in values.items():
                rows.append({'forecast': forecast, 'seed': seed, 'volatility': 1., 'controller': controller,
                             'metrics': {'total_ramp_exceedance_kw': exceedance, 'total_throughput_kwh': throughput}})
    return rows


class ConfirmatoryTests(unittest.TestCase):
    def test_designs_are_disjoint_and_complete(self):
        self.assertFalse(set(confirmatory.HELD_OUT_SEEDS) & set(DEVELOPMENT_SEEDS))
        self.assertEqual(len(confirmatory.HELD_OUT_SEEDS), 50)
        self.assertIn(confirmatory.PRIMARY, confirmatory.CONTROLLERS)
        self.assertEqual(len(set(confirmatory.FORECAST_CONDITIONS)), 9)

    def test_runner_refuses_unfrozen_protocol(self):
        with tempfile.TemporaryDirectory() as d, patch.object(confirmatory, 'PROTOCOL_SHA256', None):
            with self.assertRaises(SystemExit):
                confirmatory.run(Path(d) / 'x')

    def test_runner_refuses_modified_protocol(self):
        with tempfile.TemporaryDirectory() as d, patch.object(confirmatory, 'PROTOCOL_SHA256', '0' * 64):
            with self.assertRaises(SystemExit):
                confirmatory.run(Path(d) / 'x')

    def test_rehearsal_refuses_held_out_seeds(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                confirmatory.run(Path(d) / 'x', rehearsal_seeds=[700000])

    def test_holm(self):
        self.assertEqual(holm([.01, .04, .03]), [.03, .06, .06])
        self.assertEqual(holm([.5]), [.5])

    def test_primary_tests_detect_known_effects(self):
        effect = {'oracle25': -300., 'oracle50': -300., 'oracle100': -300.,
                  'persistence': 0., 'mean_reversion': 0., 'skill_combo': 0., 'damped_trend': 200.}
        tests = {(t['test'], t['forecast']): t for t in primary_tests(fake_results(effect))}
        self.assertEqual(len(tests), 13)
        for f in confirmatory.SKILFUL:
            self.assertTrue(tests[('H1', f)]['supported'])
            self.assertTrue(tests[('H2a', f)]['supported'])     # throughput 500 < 900
            self.assertFalse(tests[('H2b', f)]['supported'])    # adaptive exceedance far lower
        for f in ('persistence', 'mean_reversion', 'skill_combo'):
            self.assertTrue(tests[('H3', f)]['supported'])      # |noise| < 5% margin
        self.assertFalse(tests[('H3', 'damped_trend')]['supported'])  # harm 200 > margin
        self.assertAlmostEqual(tests[('H3', 'persistence')]['margin'], .05 * (400 + 13 * 14.5))
        self.assertAlmostEqual(tests[('H2b', 'oracle25')]['margin'], .10 * (400 + 13 * 14.5))


if __name__ == '__main__':
    unittest.main()
