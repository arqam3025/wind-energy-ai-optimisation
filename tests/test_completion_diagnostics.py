"""Meaningful identity and timestamp checks for frozen-output diagnostics."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_completion_diagnostics import diagnose,first_export

class DiagnosticTests(unittest.TestCase):
    def test_wind_limited_requests(self):
        np.testing.assert_allclose(first_export(np.array([0.,50.,200.]),100.,0.,30.),[0.,0.,70.])

    def test_next_transition_includes_previous_battery_injection(self):
        times=pd.date_range('2018-11-05',periods=144,freq='10min')
        block=pd.DataFrame({'timestamp':times,'current_power_kw':500.,'actual_h1_kw':500.,'xgboost_h1_kw':500.})
        charge=np.r_[100.,0.,np.zeros(142)]
        energy=1000+np.cumsum(.95*charge/6)
        trace=pd.DataFrame({'timestamp':times+pd.Timedelta(minutes=10),'grid_export_kw':500-charge,
            'charge_kw':charge,'discharge_kw':0.,'curtailment_kw':0.,'soc_percent':energy/20,
            'committed_charge_kw':charge,'committed_discharge_kw':0.,'committed_curtailment_kw':0.,'downside_forecast_kw':400.})
        d,m=diagnose(block,trace,'fixed',1,1)
        np.testing.assert_allclose(d.grid_ramp_kw.iloc[:3],[-100,100,0])
        self.assertEqual(m['transitions'],144)
        trace.loc[0,'timestamp']+=pd.Timedelta(minutes=10)
        with self.assertRaises(ValueError):diagnose(block,trace,'fixed',1,1)

if __name__=='__main__':unittest.main()
