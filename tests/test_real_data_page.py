"""Real-Data Validation page: renders from verified result copies and refuses tampered files."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))

import views.real_data as real_data  # noqa: E402
from platform_data import ArtifactError  # noqa: E402


def _page():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path.cwd() / 'app'))
    from views.real_data import render
    render()


class RealDataPage(unittest.TestCase):
    def test_page_renders_without_exceptions(self):
        app = AppTest.from_function(_page, default_timeout=60)
        app.run()
        self.assertFalse(app.exception, [e.value for e in app.exception])
        self.assertEqual(app.title[0].value, 'Real-Data Validation')
        self.assertIn('4 / 4', [m.value for m in app.metric])

    def test_values_match_sealed_results(self):
        sealed = real_data.load('sealed_2023_2024_tests.json')
        tests = {t['test']: t for t in sealed['tests']}
        self.assertTrue(all(t['supported'] for t in tests.values()))
        self.assertAlmostEqual(tests['R1']['mean_difference'], -30.6, delta=.05)

    def test_second_site_matches_sealed_run_record(self):
        sealed = real_data.load('penmanshiel_sealed_2023_2024_tests.json')
        tests = {t['test']: t for t in sealed['tests']}
        self.assertEqual(sorted(tests), ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'])
        self.assertTrue(all(t['supported'] for t in tests.values()))
        self.assertAlmostEqual(tests['S1']['mean_difference'], -38.1, delta=.05)
        self.assertAlmostEqual(tests['S2']['mean_difference'], -82.2, delta=.05)
        self.assertIn('6 / 6', [m.value for m in AppTest.from_function(_page, default_timeout=60).run().metric])

    def test_tampered_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'real_data'
            shutil.copytree(real_data.ASSETS, copy)
            doc = json.loads((copy / 'sealed_2023_2024_tests.json').read_text(encoding='utf-8'))
            doc['tests'][0]['mean_difference'] = -999
            (copy / 'sealed_2023_2024_tests.json').write_text(json.dumps(doc), encoding='utf-8')
            original, real_data.ASSETS = real_data.ASSETS, copy
            try:
                with self.assertRaises(ArtifactError):
                    real_data.load('sealed_2023_2024_tests.json')
            finally:
                real_data.ASSETS = original


if __name__ == '__main__':
    unittest.main()
