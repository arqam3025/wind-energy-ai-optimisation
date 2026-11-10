"""Synthetic artifact-join failure fixtures; no predictive/control calculation."""
import csv
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest

from publication_v2.temporal_audit import TemporalInputError, _rows, reconstruct_features


class TemporalArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, rows):
        path = self.root / name
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        return path

    def fixture(self):
        base=datetime(2030,1,1)
        raw=[{'Date/Time':(base+timedelta(minutes=10*i)).strftime('%d %m %Y %H:%M'),
              'LV ActivePower (kW)':str(i),'Wind Speed (m/s)':'3','Wind Direction (degrees)':'90'} for i in range(13)]
        self.write('data/raw/T1.csv',raw)
        origin=base+timedelta(minutes=60)
        row={'timestamp':str(origin),'power_kw':'6','wind_speed':'3','wind_direction':'90',
             'target_timestamp':str(origin+timedelta(minutes=10)),'target_power_kw':'7',
             **{f'{kind}_lag_{lag}min':str(6-lag/10 if kind=='power' else 3) for kind in ('power','wind') for lag in (10,20,30,60)},
             'power_change_10min':'1','wind_change_10min':'0','power_mean_40min':'4.5'}
        self.write('data/processed/wind_features_10min.csv',[row])
        self.write('data/processed/wind_multistep_features.csv',[{**row,**{f'target_h{h}_kw':str(6+h) for h in range(1,7)}}])
        return raw,row

    def test_actual_value_lineage_reconstruction(self):
        self.fixture()
        result=reconstruct_features(self.root)
        self.assertEqual(result['feature_value_checks'],28)
        self.assertEqual(result['target_value_checks'],8)

    def test_missing_required_file_is_explicit(self):
        with self.assertRaisesRegex(TemporalInputError,'Missing required'): reconstruct_features(self.root)

    def test_duplicate_missing_and_invalid_timestamp_rejected(self):
        for rows in ([{'timestamp':'2030-01-01 00:00:00'}]*2,[{'timestamp':''}], [{'timestamp':'2030-01-01 00:01:00'}]):
            with self.subTest(rows=rows),self.assertRaises(TemporalInputError): _rows(self.write('rows.csv',rows))

    def test_missing_source_support_not_silently_shifted(self):
        raw,_=self.fixture()
        self.write('data/raw/T1.csv',raw[:3]+raw[4:])
        with self.assertRaisesRegex(TemporalInputError,'Missing feature source support'): reconstruct_features(self.root)

    def test_future_or_incorrect_feature_value_rejected(self):
        _,row=self.fixture()
        row['power_lag_10min']='7'
        self.write('data/processed/wind_features_10min.csv',[row])
        with self.assertRaisesRegex(TemporalInputError,'Feature value/support mismatch'): reconstruct_features(self.root)

    def test_misaligned_target_timestamp_and_value_rejected(self):
        _,row=self.fixture()
        row['target_timestamp']='2030-01-01 01:20:00'
        self.write('data/processed/wind_features_10min.csv',[row])
        with self.assertRaisesRegex(TemporalInputError,'Target timestamp mismatch'): reconstruct_features(self.root)
        row['target_timestamp']='2030-01-01 01:10:00'; row['target_power_kw']='8'
        self.write('data/processed/wind_features_10min.csv',[row])
        with self.assertRaisesRegex(TemporalInputError,'Target value mismatch'): reconstruct_features(self.root)

    def test_nonfinite_source_value_rejected(self):
        raw,_=self.fixture();raw[0]['LV ActivePower (kW)']='nan'
        self.write('data/raw/T1.csv',raw)
        with self.assertRaisesRegex(TemporalInputError,'nonfinite'): reconstruct_features(self.root)

    def test_signed_raw_feature_power_is_not_silently_clipped(self):
        raw,row=self.fixture()
        raw[6]['LV ActivePower (kW)']='-6'
        self.write('data/raw/T1.csv',raw)
        row.update(power_kw='-6',power_change_10min='-11',power_mean_40min='1.5')
        self.write('data/processed/wind_features_10min.csv',[row])
        self.write('data/processed/wind_multistep_features.csv',[{**row,**{f'target_h{h}_kw':str(6+h) for h in range(1,7)}}])
        self.assertEqual(reconstruct_features(self.root)['feature_value_checks'],28)


if __name__=='__main__':unittest.main()
