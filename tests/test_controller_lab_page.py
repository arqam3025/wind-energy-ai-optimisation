"""Controller Lab page: renders from the bundled sample only (no private data) and shows live results."""

import sys
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def _page():
    import sys
    from pathlib import Path

    root = Path.cwd()
    for path in (root / 'app', root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from views.controller_lab import render

    render()


class ControllerLabPage(unittest.TestCase):
    def test_page_renders_with_default_controllers(self):
        app = AppTest.from_function(_page, default_timeout=120)
        app.run()
        self.assertFalse(app.exception, [e.value for e in app.exception])
        self.assertEqual(app.title[0].value, 'Controller Lab')
        self.assertEqual(len(app.metric), 4)
        self.assertTrue(app.dataframe)

    def test_switching_to_persistence_keeps_battery_idle(self):
        app = AppTest.from_function(_page, default_timeout=120)
        app.run()
        app.selectbox(key='lab_forecast').set_value('persistence').run()
        self.assertFalse(app.exception, [e.value for e in app.exception])
        throughput = next(m.value for m in app.metric if m.label == 'Battery throughput')
        self.assertEqual(throughput, '0 kWh')  # no forecast skill -> the graded switch stays idle


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    unittest.main()
