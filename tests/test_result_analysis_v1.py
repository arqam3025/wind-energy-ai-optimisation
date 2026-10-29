"""Synthetic integrity fixtures, never reported as research outcomes."""
import sys
import unittest
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from windresearch.protocol import ProtocolError
from windresearch.result_analysis import transition_diagnostics


class TransitionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.wind = pd.DataFrame({'block_id': [1, 1, 2], 'timestamp': ['a', 'b', 'c'],
                                  'grid_ramp_kw': [300., 100., 250.], 'ramp_violation': [1, 0, 1]})

    def test_introduced_removed_identity_includes_episode_boundary(self):
        controller = self.wind.copy()
        controller['grid_ramp_kw'] = [100., 300., 250.]
        controller['ramp_violation'] = [0, 1, 1]
        result = transition_diagnostics(controller, self.wind)
        self.assertEqual(result['introduced_violations'], 1)
        self.assertEqual(result['removed_violations'], 1)
        self.assertEqual(result['net_additional_violations'], 0)
        self.assertEqual(result['transitions'], 3)

    def test_unmatched_transition_never_silently_deleted(self):
        with self.assertRaises(ProtocolError):
            transition_diagnostics(self.wind.iloc[:2], self.wind)
        with self.assertRaises(ProtocolError):
            transition_diagnostics(pd.concat([self.wind, self.wind.iloc[:1]]), self.wind)


if __name__ == '__main__':
    unittest.main()
