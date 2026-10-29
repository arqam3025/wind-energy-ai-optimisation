"""Data-independent protocol tests; synthetic dates are fixtures, not findings."""
from pathlib import Path
import sys
import tempfile
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from windresearch.protocol import (ProtocolError,require_static_calibration_available,
    role_target_overlap,require_cohort_interpretation,require_new_output_directory,
    target_purged_calibration)


class ResearchProtocolTests(unittest.TestCase):
    def test_equal_and_future_calibration_targets_rejected(self):
        calibration=pd.DataFrame({'timestamp':pd.to_datetime(['2020-01-01 00:00'])})
        for decision in ['2020-01-01 00:10','2020-01-01 01:00']:
            with self.assertRaises(ProtocolError):
                require_static_calibration_available(calibration,pd.Timestamp(decision))
        require_static_calibration_available(calibration,pd.Timestamp('2020-01-01 01:10'))

    def test_schedule_development_targets_included(self):
        schedule=pd.DataFrame({'block_id':[6,7],'evaluation_role':['development','evaluation']})
        blocks={6:pd.DataFrame({'timestamp':pd.to_datetime(['2020-01-01 00:00'])}),
                7:pd.DataFrame({'timestamp':pd.to_datetime(['2020-01-01 00:10'])})}
        overlap=role_target_overlap(schedule,blocks)
        self.assertEqual(len(overlap),5)
        self.assertEqual(set(overlap.block_id),{7})
        with self.assertRaises(ProtocolError):require_cohort_interpretation(overlap,retrospective=False)
        require_cohort_interpretation(overlap,retrospective=True)

    def test_partial_existing_output_not_resumed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'study'
            require_new_output_directory(path)
            (path/'partial.csv').write_text('unfinished')
            with self.assertRaises(ProtocolError):require_new_output_directory(path)
            self.assertEqual((path/'partial.csv').read_text(),'unfinished')

    def test_target_purge_is_strict_and_does_not_mutate_input(self):
        calibration=pd.DataFrame({'timestamp':pd.date_range('2020-01-01',periods=20,freq='10min'),'value':range(20)})
        before=calibration.copy(deep=True)
        retained,excluded=target_purged_calibration(calibration,pd.Timestamp('2020-01-01 03:20'))
        self.assertEqual(len(excluded),6)
        self.assertEqual(len(retained),14)
        self.assertEqual(retained.timestamp.max()+pd.Timedelta(minutes=60),pd.Timestamp('2020-01-01 03:10'))
        pd.testing.assert_frame_equal(calibration,before)

if __name__=='__main__':unittest.main()
