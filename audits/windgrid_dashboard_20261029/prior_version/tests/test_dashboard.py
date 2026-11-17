"""Read-only dashboard smoke tests and independent display-accounting checks."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"app"))
from research_data import available_blocks, load_table, load_replay, interval_accounting, aggregate_comparison

class DashboardDataTests(unittest.TestCase):
    def test_valid_selection_excludes_development(self):
        self.assertEqual(len(available_blocks()),49)
        self.assertNotIn(6,available_blocks())
        with self.assertRaises(ValueError):load_replay(6)

    def test_display_accounting_matches_saved_block(self):
        source,traces=load_replay(1)
        saved=load_table("block_metrics")
        for kind,trace in traces.items():
            display=interval_accounting(source,trace)
            row=saved.loc[(saved.block_id==1)&saved.controller.eq(kind)].iloc[0]
            self.assertEqual(int(display.ramp_violation.sum()),int(row.ramp_violations))
            self.assertAlmostEqual(display.ramp_exceedance_kw.sum(),row.ramp_exceedance_kw,places=7)
            self.assertAlmostEqual(display.throughput_kwh.sum(),row.throughput_kwh,places=7)
            self.assertAlmostEqual(display.conversion_loss_kwh.sum(),row.conversion_losses_kwh,places=7)

    def test_aggregate_only_without_private_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            destination=root/"docs/tables_v2"
            destination.mkdir(parents=True)
            for name in ["aggregate_metrics","block_metrics","uncontrolled_wind_baseline"]:
                shutil.copyfile(ROOT/f"docs/tables_v2/{name}.csv",destination/f"{name}.csv")
            self.assertEqual(len(available_blocks(root)),49)
            self.assertEqual(len(aggregate_comparison(root)),3)
            with self.assertRaisesRegex(FileNotFoundError,"Missing local replay artifacts"):
                load_replay(1,root)

class DashboardAppTests(unittest.TestCase):
    def test_initial_render_and_control_changes(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/"app/dashboard.py"), default_timeout=30).run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.selectbox(key="controller").value,"adaptive_one_sided")
        app.selectbox(key="controller").select("fixed").run()
        self.assertEqual(len(app.exception),0)
        app.selectbox(key="block_id").select(7).run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.selectbox(key="block_id").value,7)
        app.select_slider(key="horizon").set_value(60).run()
        self.assertEqual(len(app.exception),0)

if __name__=="__main__":unittest.main()
