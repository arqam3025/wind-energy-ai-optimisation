"""Boundary and intervention tests of strict causal eligibility."""
import sys
from pathlib import Path
import unittest
import ast
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from causal_one_sided_uncertainty import CausalAdaptiveUncertainty
from prepare_frozen_heldout import verify
from heldout_support import preflight

class CausalityTests(unittest.TestCase):
    def test_frozen_optimisation_and_fallback_are_identical(self):
        root = Path(__file__).resolve().parents[1]
        pairs=[('uncertainty_grid_priority_tolerance_development.py','frozen_fixed_heldout.py'),
               ('causal_one_sided_grid_priority_mpc_development.py','frozen_adaptive_one_sided_heldout.py')]
        for original, adapted in pairs:
            a=(root/'scripts'/original).read_text()
            b=(root/'scripts'/adapted).read_text()
            start='    nominal = np.maximum('
            end='    records.append({'
            self.assertEqual(ast.dump(ast.parse('if True:\n'+a[a.index(start):a.index(end)])),
                             ast.dump(ast.parse('if True:\n'+b[b.index(start):b.index(end)])))
        fixed=pd.read_csv(root/'results/multistep_uncertainty_calibration_split.csv')
        np.testing.assert_allclose(fixed.calibration_quantile_kw,[400.01362539062,536.12039257812,608.362374902344,673.96943320312,727.95680585937,786.612837734375],atol=1e-6,rtol=0)

    def test_freeze_and_inputs(self):
        verify()
        preflight()

    def test_equal_and_future_targets_cannot_change_margin(self):
        times = pd.date_range('2018-01-01', periods=300, freq='10min')
        history = pd.DataFrame({'timestamp':times})
        for h in range(1,7):
            history[f'xgboost_h{h}_kw'] = 3000.
            history[f'actual_h{h}_kw'] = 2000.
        decision = times[200]
        original, diagnostics = CausalAdaptiveUncertainty(history).margins(decision)
        for h in range(1,7):
            mask = history.timestamp + pd.Timedelta(minutes=10*h) >= decision
            history.loc[mask, f'actual_h{h}_kw'] = -1e9
        changed, _ = CausalAdaptiveUncertainty(history).margins(decision)
        np.testing.assert_array_equal(original, changed)
        for d in diagnostics:
            self.assertLess(d['newest_target'], decision)
            self.assertEqual(d['newest_target'], decision-pd.Timedelta(minutes=10))

if __name__ == '__main__':
    unittest.main()
