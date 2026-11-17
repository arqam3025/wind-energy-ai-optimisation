"""Adversarial checks for the independent audit, not solver implementation tests."""
import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyse_frozen_heldout import validate_and_measure

class AccountingTests(unittest.TestCase):
    def setUp(self):
        times=pd.date_range('2018-11-05',periods=144,freq='10min')
        self.block=pd.DataFrame({'timestamp':times,'actual_h1_kw':100.,'current_power_kw':100.})
        self.output=pd.DataFrame({'timestamp':times+pd.Timedelta(minutes=10),
            'wind_generation_kw':100.,'charge_kw':0.,'discharge_kw':0.,'curtailment_kw':0.,
            'grid_export_kw':100.,'soc_percent':50.,'committed_charge_kw':0.,'committed_discharge_kw':0.,'committed_curtailment_kw':0.})

    def test_zero_battery_energy_reference(self):
        m=validate_and_measure(self.output,self.block,'fixed')
        self.assertEqual(m['ramp_violations'],0)
        self.assertEqual(m['throughput_kwh'],0)
        self.assertEqual(m['export_kwh'],2400)
        self.assertEqual(m['terminal_adjusted_export_kwh'],2400)

    def test_rejects_energy_creation(self):
        self.output.loc[50,'soc_percent']+=1
        with self.assertRaises(AssertionError):validate_and_measure(self.output,self.block,'fixed')

    def test_rejects_power_balance_error(self):
        self.output.loc[60,'grid_export_kw']+=1
        with self.assertRaises(AssertionError):validate_and_measure(self.output,self.block,'fixed')

    def test_rejects_equal_time_residual(self):
        self.output['newest_residual_target']=self.block.timestamp
        with self.assertRaises(AssertionError):validate_and_measure(self.output,self.block,'adaptive_one_sided')

    def test_terminal_restoration_accounts_for_charge_loss(self):
        # 100 kW wind-only charge for one interval; no additional export.
        self.output.loc[0,['charge_kw','committed_charge_kw']]=100.
        self.output.loc[0,'grid_export_kw']=0.
        self.output['soc_percent']=50.+(.95*100/6)/20
        m=validate_and_measure(self.output,self.block,'fixed')
        self.assertAlmostEqual(m['conversion_losses_kwh'],100/6*.05)
        self.assertAlmostEqual(m['terminal_adjusted_export_kwh'],2400-100/6+.95*.95*100/6)

if __name__=='__main__':unittest.main()
