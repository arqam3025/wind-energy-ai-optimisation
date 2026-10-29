"""Synthetic algorithm fixtures only; not experimental wind findings."""
from pathlib import Path
import sys,unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from windresearch.dependent_statistics import moving_block_indices,paired_uncertainty,recentered_basic_interval,METRICS
from windresearch.protocol import ProtocolError

class DependentStatisticsTests(unittest.TestCase):
    def test_segment_boundaries_seed_and_short_segment(self):
        labels=np.array([1]*5+[2]*9)
        a=moving_block_indices(labels,100,7,42)
        np.testing.assert_array_equal(a,moving_block_indices(labels,100,7,42))
        np.testing.assert_array_equal(a[:,:5],np.tile(np.arange(5),(100,1)))
        self.assertTrue((labels[a[:,:5]]==1).all())
        self.assertTrue((labels[a[:,5:]]==2).all())
        with self.assertRaises(ProtocolError):moving_block_indices([1,2,1],10,2,1)

    def test_identical_cases_have_exact_zero_differences(self):
        schedule=pd.DataFrame({'block_id':range(1,9),'segment_id':[1]*4+[2]*4,
            'evaluation_role':'evaluation','start_timestamp':pd.date_range('2020-01-01',periods=8)})
        rows=[]
        for controller in ['fixed','adaptive_one_sided']:
            for block in range(1,9):rows.append({'controller':controller,'block_id':block,**{k:float(block) for k in METRICS}})
        intervals,_,_=paired_uncertainty(pd.DataFrame(rows),schedule,lengths=[2,3],replicates=100)
        self.assertTrue((intervals[['estimate','lower_approx95','upper_approx95']]==0).all().all())
        with self.assertRaises(ProtocolError):paired_uncertainty(pd.DataFrame(rows[:-1]),schedule,replicates=100)

    def test_recentered_interval_not_forced_to_cross_zero(self):
        lower,upper=recentered_basic_interval(5.,np.arange(10.))
        self.assertGreater(lower,0)
        self.assertGreater(upper,lower)

if __name__=='__main__':unittest.main()
