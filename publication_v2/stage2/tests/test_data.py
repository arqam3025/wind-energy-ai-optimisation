import json
from pathlib import Path
import tempfile
import unittest
from publication_v2.stage2.data import DatasetError,load_bundle
from publication_v2.stage2.tests.fixtures import dataset


class DatasetGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.path=dataset(self.root)

    def change(self,fn):
        doc=json.loads(self.path.read_text());fn(doc);self.path.write_text(json.dumps(doc));return doc

    def load(self): return load_bundle(self.path,self.root,allow_synthetic=True)

    def test_valid_full_ledger_and_no_synthetic_production_admission(self):
        bundle=self.load();self.assertEqual(bundle.features_for('train').shape,(80,14));self.assertEqual(bundle.targets_for_fit().shape,(80,6))
        with self.assertRaisesRegex(DatasetError,'Synthetic'):load_bundle(self.path,self.root)

    def test_software_test_mode_cannot_mislabel_real_training(self):
        self.change(lambda d:d.update(dataset_kind='REAL_DEVELOPMENT'))
        with self.assertRaisesRegex(DatasetError,'Software-test'):self.load()

    def test_missing_file_and_unknown_provenance_rejected(self):
        with self.assertRaises(DatasetError):load_bundle(self.root/'missing.json',self.root)
        self.change(lambda d:d['provenance']['timezone'].update(value=None,status='UNKNOWN'))
        with self.assertRaisesRegex(DatasetError,'timezone'):self.load()

    def test_post_origin_feature_and_missing_measurement_support_rejected(self):
        self.change(lambda d:d['partitions']['development'][0]['features'][0].update(available_at='2030-01-01T23:10:01+00:00'))
        with self.assertRaises(DatasetError):self.load()

    def test_modified_feature_or_target_cannot_become_a_measurement(self):
        self.change(lambda d:d['partitions']['train'][0]['features'][0].update(value=999999))
        with self.assertRaisesRegex(DatasetError,'lineage'):self.load()
        # Restore a fresh explicitly synthetic ledger, then corrupt a target.
        self.tmp2=tempfile.TemporaryDirectory();self.addCleanup(self.tmp2.cleanup)
        root=Path(self.tmp2.name);path=dataset(root);doc=json.loads(path.read_text())
        doc['partitions']['development'][0]['targets'][0]['value_kw']=999999;path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(DatasetError,'source measurements'):load_bundle(path,root,allow_synthetic=True)

    def test_duplicate_origins_horizon_omission_and_unavailable_training_labels(self):
        original=self.path.read_text()
        for mutate in (lambda d:d['partitions']['train'].append(d['partitions']['train'][0]),
                       lambda d:d['partitions']['development'][0]['targets'].pop(),
                       lambda d:d.update(fit_time=d['partitions']['train'][0]['origin_time'])):
            with self.subTest(mutate=mutate):
                self.path.write_text(original);self.change(mutate)
                with self.assertRaises(DatasetError):self.load()

    def test_cross_split_embargo_rejected(self):
        self.change(lambda d:d['partitions']['calibration'].insert(0,d['partitions']['train'][-1]))
        with self.assertRaisesRegex(DatasetError,'overlap|embargo|unauthorized'):self.load()

    def test_confirmation_role_and_unresolved_source_timezone_rejected(self):
        original=self.path.read_text()
        self.change(lambda d:d.update(contains_confirmation_data=True))
        with self.assertRaisesRegex(DatasetError,'Confirmation'):self.load()
        self.path.write_text(original);self.change(lambda d:d['provenance']['timezone'].update(value='unknown/source_clock'))
        with self.assertRaisesRegex(DatasetError,'timezone'):self.load()

    def test_changed_receipt_or_source_hash_rejected(self):
        original=self.path.read_text()
        self.change(lambda d:d['partitions']['development'][0]['features'][0]['source_available_ats'].__setitem__(0,'2030-01-01T23:10:01+00:00'))
        with self.assertRaises(DatasetError):self.load()
        self.path.write_text(original);self.change(lambda d:d['source_artifact'].update(sha256='a'*64))
        with self.assertRaisesRegex(DatasetError,'identity|hash'):self.load()


if __name__=='__main__':unittest.main()
