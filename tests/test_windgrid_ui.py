"""Interaction and failure-mode tests for the historical WindGrid platform."""
from pathlib import Path
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "app/dashboard.py"
PAGES = {
    "Command Center": "screens/command_center.py",
    "Digital Twin": "screens/digital_twin.py",
    "AI Forecasting Lab": "screens/forecasting.py",
    "MPC Decision Explorer": "screens/mpc.py",
    "Battery Analytics": "screens/battery.py",
    "Grid Stability Lab": "screens/grid.py",
    "Research Results": "screens/results.py",
    "Reproducibility": "screens/reproducibility.py",
}


def rendered_text(app):
    text = []
    for name in ["title", "header", "subheader", "caption", "markdown", "info", "warning", "error"]:
        for element in getattr(app, name):
            text.append(str(element.value))
    return "\n".join(text).lower()


def summary_fixture(root):
    destination = root / "docs/tables_v2"
    destination.mkdir(parents=True)
    for source in (ROOT / "docs/tables_v2").glob("*.csv"):
        shutil.copyfile(source, destination / source.name)


class WindGridUITests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(ENTRY), default_timeout=40).run()

    def assert_clean(self, app):
        self.assertEqual(len(app.exception), 0, str(app.exception))

    def test_all_eight_pages_render_and_seven_analytical_pages_have_plotly(self):
        app = self.app()
        self.assert_clean(app)
        self.assertEqual(len(app.selectbox(key="block_id").options), 49)
        self.assertNotIn("Block 6", app.selectbox(key="block_id").options)
        for title, path in PAGES.items():
            with self.subTest(page=title):
                app.switch_page(path).run()
                self.assert_clean(app)
                text = rendered_text(app)
                self.assertIn("historical", text)
                if title != "Reproducibility":
                    self.assertGreater(len(app.get("plotly_chart")), 0, title)

    def test_controller_block_horizon_and_uncontrolled_comparison(self):
        app = self.app()
        app.selectbox(key="controller").select("uncontrolled").run()
        self.assert_clean(app)
        app.selectbox(key="block_id").select(7).run()
        self.assert_clean(app)
        app.select_slider(key="horizon").set_value(60).run()
        app.switch_page(PAGES["AI Forecasting Lab"]).run()
        self.assert_clean(app)
        self.assertEqual(app.selectbox(key="controller").value, "uncontrolled")
        self.assertEqual(app.selectbox(key="block_id").value, 7)
        self.assertEqual(app.select_slider(key="horizon").value, 60)
        app.switch_page(PAGES["Research Results"]).run()
        self.assert_clean(app)
        self.assertIn("uncontrolled", rendered_text(app))
        self.assertGreater(len(app.get("plotly_chart")), 0)

    def test_play_pause_step_reset_and_episode_end(self):
        app = self.app()
        app.switch_page(PAGES["Digital Twin"]).run()
        self.assert_clean(app)
        self.assertEqual(app.slider(key="time_step").value, 0)
        app.button(key="step_forward").click().run()
        self.assert_clean(app)
        self.assertEqual(app.slider(key="time_step").value, 1)
        app.button(key="step_back").click().run()
        self.assertEqual(app.slider(key="time_step").value, 0)
        app.button(key="play").click().run()
        self.assert_clean(app)
        self.assertTrue(app.session_state["playing"])
        app.selectbox(key="block_id").select(2).run()
        self.assert_clean(app)
        self.assertEqual(app.slider(key="time_step").value, 0)
        self.assertFalse(app.session_state["playing"])
        app.button(key="play").click().run()
        app.button(key="pause").click().run()
        self.assertFalse(app.session_state["playing"])
        app.slider(key="time_step").set_value(143).run()
        self.assert_clean(app)
        self.assertEqual(app.slider(key="time_step").value, 143)
        self.assertTrue(app.button(key="step_forward").disabled)
        self.assertTrue(app.button(key="play").disabled)
        self.assertEqual(app.slider(key="time_step").value, 143)
        self.assertFalse(app.session_state["playing"])
        app.button(key="reset_playback").click().run()
        self.assertEqual(app.slider(key="time_step").value, 0)

    def test_elapsed_playback_tick_advances_once_and_stops_at_episode_end(self):
        app=self.app()
        app.switch_page(PAGES['Digital Twin']).run()
        app.button(key='play').click().run()
        # Simulate an elapsed timer without sleeping or inventing telemetry.
        app.session_state['last_tick']=0.0
        app.run()
        self.assert_clean(app)
        self.assertEqual(app.slider(key='time_step').value,1)
        accounting=[item.value for item in app.dataframe if 'intervals' in item.value.columns]
        self.assertEqual(int(accounting[0].intervals.iloc[0]),2)
        app.session_state['pending_step']=142
        app.session_state['last_tick']=0.0
        app.run()
        self.assert_clean(app)
        self.assertEqual(app.slider(key='time_step').value,143)
        self.assertFalse(app.session_state['playing'])

    def test_summary_only_root_keeps_results_available_and_discloses_missing_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary_fixture(root)
            with patch.dict(os.environ, {"WINDGRID_DATA_ROOT": str(root)}):
                app = self.app()
                self.assert_clean(app)
                text = rendered_text(app)
                self.assertTrue("missing" in text or "unavailable" in text)
                app.switch_page(PAGES["Research Results"]).run()
                self.assert_clean(app)
                self.assertGreater(len(app.get("plotly_chart")), 0)
                app.switch_page(PAGES["Digital Twin"]).run()
                self.assert_clean(app)
                text = rendered_text(app)
                self.assertTrue("missing" in text or "unavailable" in text)

    def test_missing_summary_root_reports_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"WINDGRID_DATA_ROOT": directory}):
                app = self.app()
                self.assert_clean(app)
                self.assertGreater(len(app.error), 0)
                self.assertIn("missing", rendered_text(app))

    def test_corrupt_local_trace_is_rejected_instead_of_displayed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary_fixture(root)
            source_dir = root / "data/processed"
            source_dir.mkdir(parents=True)
            shutil.copyfile(ROOT / "data/processed/evaluation_block_1.csv", source_dir / "evaluation_block_1.csv")
            for kind in ["fixed", "adaptive_one_sided"]:
                relative = Path("results/frozen_heldout/final_20261029") / kind / "adaptive_charging_mpc_block_1_weight_0p500.csv"
                (root / relative).parent.mkdir(parents=True)
                data = pd.read_csv(ROOT / relative)
                if kind == "fixed":
                    data.loc[0, "soc_percent"] = 150.0
                data.to_csv(root / relative, index=False)
            with patch.dict(os.environ, {"WINDGRID_DATA_ROOT": str(root)}):
                app = self.app()
                self.assert_clean(app)
                text = rendered_text(app)
                self.assertTrue(any(word in text for word in ["invalid", "malformed", "soc", "conservation", "validation"]))

    def test_missing_fixed_calibration_is_disclosed_without_inventing_a_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary_fixture(root)
            source_dir = root / "data/processed"
            source_dir.mkdir(parents=True)
            shutil.copyfile(ROOT / "data/processed/evaluation_block_1.csv", source_dir / "evaluation_block_1.csv")
            for kind in ["fixed", "adaptive_one_sided"]:
                relative = Path("results/frozen_heldout/final_20261029") / kind / "adaptive_charging_mpc_block_1_weight_0p500.csv"
                (root / relative).parent.mkdir(parents=True)
                shutil.copyfile(ROOT / relative, root / relative)
            with patch.dict(os.environ, {"WINDGRID_DATA_ROOT": str(root)}):
                app = self.app()
                app.selectbox(key="controller").select("fixed").run()
                for page in ["AI Forecasting Lab", "MPC Decision Explorer"]:
                    app.switch_page(PAGES[page]).run()
                    self.assert_clean(app)
                    text = rendered_text(app)
                    self.assertIn("calibration", text)
                    self.assertTrue("missing" in text or "unavailable" in text)


if __name__ == "__main__":
    unittest.main()
