"""Data corruption and reference-accounting tests for the research platform."""
from pathlib import Path
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"app"))
import platform_data as data


class PlatformDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=data.get_replay(1)

    def test_all_cases_conserve_energy_and_match_saved_metrics(self):
        saved=data.get_table("block_metrics")
        for kind in ["fixed","adaptive_one_sided"]:
            frame=data.interval_frame(1,kind)
            totals=data.energy_metrics(frame)
            row=saved.loc[saved.block_id.eq(1)&saved.controller.eq(kind)].iloc[0]
            self.assertAlmostEqual(totals["throughput_kwh"],row.throughput_kwh,places=7)
            self.assertAlmostEqual(totals["conversion_losses_kwh"],row.conversion_losses_kwh,places=7)
            self.assertAlmostEqual(totals["terminal_adjusted_export_kwh"],row.terminal_adjusted_export_kwh,places=7)
            self.assertEqual(totals["ramp_violations"],row.ramp_violations)
            self.assertAlmostEqual(totals["ramp_exceedance_kw"],row.ramp_exceedance_kw,places=7)
            self.assertLess(abs(totals["energy_balance_residual_kwh"]),1e-5)
            self.assertLess(frame.energy_balance_error_kwh.abs().max(),1e-5)
            self.assertEqual(data.energy_metrics(frame,upto=0)["intervals"],1)

    def test_no_battery_is_a_measured_reference_with_missing_battery_state(self):
        frame=data.interval_frame(1,"uncontrolled")
        self.assertTrue(frame.soc_percent.isna().all())
        self.assertTrue(frame.energy_end_kwh.isna().all())
        self.assertTrue(frame.energy_before_kwh.isna().all())
        np.testing.assert_array_equal(frame.grid_export_kw,frame.wind_generation_kw)
        self.assertEqual(float(frame.throughput_kwh.sum()),0.)
        metrics=data.energy_metrics(frame)
        self.assertTrue(np.isnan(metrics["terminal_adjusted_export_kwh"]))
        self.assertEqual(metrics["inventory_change_kwh"],0.)
        self.assertAlmostEqual(metrics["energy_balance_residual_kwh"],0.)

    def test_rejects_corrupted_timestamps_power_and_soc(self):
        for field,amount,message in [("timestamp",pd.Timedelta(minutes=10),"timestamp"),("grid_export_kw",1.,"Power balance"),("soc_percent",1.,"stored-energy")]:
            trace=self.bundle.traces["fixed"].copy(deep=True)
            trace.loc[10,field]+=amount
            with self.assertRaisesRegex(data.ArtifactError,message):
                data.validate_trace(self.bundle.inputs,trace,"fixed")

    def test_rejects_equal_time_causal_target_and_false_horizon_actual(self):
        trace=self.bundle.traces["adaptive_one_sided"].copy(deep=True)
        trace.loc[0,"newest_residual_target"]=str(self.bundle.inputs.timestamp.iloc[0])
        with self.assertRaisesRegex(data.ArtifactError,"Residual target"):
            data.validate_trace(self.bundle.inputs,trace,"adaptive_one_sided")
        source=self.bundle.inputs.copy(deep=True)
        source.loc[10,"actual_h6_kw"]+=10
        with self.assertRaisesRegex(data.ArtifactError,"actual target alignment"):
            data.validate_inputs(source)

    def test_rejects_simultaneous_operation_even_with_balance_preserved(self):
        trace=self.bundle.traces["adaptive_one_sided"].copy(deep=True)
        trace.loc[0,"charge_kw"]+=1.
        trace.loc[0,"grid_export_kw"]-=1.
        trace["soc_percent"]+=.95/6/20
        with self.assertRaisesRegex(data.ArtifactError,"Simultaneous"):
            data.validate_trace(self.bundle.inputs,trace,"adaptive_one_sided")

    def test_aggregate_fallback_root_override_and_schema_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            temp=Path(folder)
            target=temp/"docs/tables_v2"
            target.mkdir(parents=True)
            for source in (ROOT/"docs/tables_v2").glob("*.csv"):
                shutil.copyfile(source,target/source.name)
            with patch.dict(os.environ,{"WINDGRID_DATA_ROOT":folder}):
                self.assertEqual(len(data.valid_blocks()),49)
                self.assertEqual(len(data.comparisons()),3)
                with self.assertRaisesRegex(data.ArtifactError,"Missing research artifact"):
                    data.get_replay(1)
                bad=pd.read_csv(target/"block_metrics.csv").drop(columns="ramp_violations")
                bad.to_csv(target/"block_metrics.csv",index=False)
                with self.assertRaisesRegex(data.ArtifactError,"missing columns"):
                    data.valid_blocks()
            self.assertEqual(data.data_root(),ROOT)

    def test_file_change_invalidates_cached_table(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/"docs/tables_v2"
            target.mkdir(parents=True)
            path=target/"aggregate_metrics.csv"
            shutil.copyfile(ROOT/"docs/tables_v2/aggregate_metrics.csv",path)
            old=data.get_table("aggregate_metrics",folder)
            altered=old.copy(deep=True)
            altered.loc[0,"throughput_kwh"]+=123
            altered.to_csv(path,index=False)
            stat=path.stat()
            os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns+1000000))
            loaded=data.get_table("aggregate_metrics",folder)
            self.assertAlmostEqual(loaded.throughput_kwh.iloc[0]-old.throughput_kwh.iloc[0],123)

    def test_planning_is_six_recorded_forecast_targets_not_fake_solver_controls(self):
        forecast=data.planning_frame(1,"adaptive_one_sided",0)
        self.assertEqual(forecast.horizon_minutes.tolist(),[10,20,30,40,50,60])
        self.assertEqual(forecast.target_time.iloc[-1],self.bundle.inputs.timestamp.iloc[0]+pd.Timedelta(minutes=60))
        np.testing.assert_array_equal(forecast.margin_kw,[self.bundle.traces["adaptive_one_sided"].iloc[0][f"adaptive_margin_h{h}_kw"] for h in range(1,7)])
        self.assertTrue((forecast.downside_kw<=forecast.nominal_kw).all())
        self.assertNotIn("planned_charge_kw",forecast.columns)
        for block in [6,0,51]:
            with self.assertRaises(data.ArtifactError):data.get_replay(block)

    def test_integrity_checks_match_and_do_not_follow_changed_manifest(self):
        result=data.integrity_report()
        self.assertEqual(result["status"],"pass")
        self.assertEqual(result["checked_files"],59)
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/"results"
            target.mkdir()
            (target/"development_controller_freeze_manifest.json").write_text('{"source_files":{"bad":{"path":"../../outside","sha256":"x"}}}')
            result=data.integrity_report(folder)
            self.assertEqual(result["status"],"mismatch")
            self.assertEqual(result["source_checks"],[])


if __name__=="__main__":unittest.main()
