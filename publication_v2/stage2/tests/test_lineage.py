"""Synthetic source transformations and rejection tests; no research fitting."""
import csv
import hashlib
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from publication_v2.integrity import digest
from publication_v2.stage2.data import load_bundle,DatasetError
from publication_v2.stage2.lineage import (AdmissionError,_read_measurements,FIELDS,semantic_sha256,
    IMPLEMENTATION,verify_lineage,historical_registry,POLICY)
from publication_v2.stage2.tests.fixtures import dataset,refresh_lineage


class LineageAndCohortTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.path=dataset(self.root);self.doc=json.loads(self.path.read_text())

    def save(self):self.path.write_text(json.dumps(self.doc),encoding='utf-8')
    def load(self):self.save();return load_bundle(self.path,self.root,allow_synthetic=True)
    def policy(self):return json.loads((self.root/self.doc['cohort_policy']['path']).read_text())
    def save_policy(self,policy):
        path=self.root/self.doc['cohort_policy']['path'];path.write_text(json.dumps(policy));self.doc['cohort_policy']['sha256']=digest(path)

    def source_rows(self,name='fixture_measurements.csv'):
        with (self.root/name).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
    def write_rows(self,rows,name='fixture_measurements.csv',**options):
        with (self.root/name).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS,**options);w.writeheader();w.writerows(rows)

    def test_explicit_manifest_and_transformation_identity_required(self):
        original=json.loads(json.dumps(self.doc))
        del self.doc['lineage_manifest']
        with self.assertRaisesRegex(DatasetError,'manifest'):self.load()
        self.doc=original;path=self.root/self.doc['lineage_manifest']['path'];manifest=json.loads(path.read_text())
        manifest['transformation']['implementation_sha256']='0'*64;path.write_text(json.dumps(manifest));self.doc['lineage_manifest']['sha256']=digest(path)
        with self.assertRaisesRegex(DatasetError,'transformation'):self.load()

    def test_self_authored_attestation_cannot_authorize_real_data(self):
        self.doc['dataset_kind']='REAL_DEVELOPMENT'
        for item in self.doc['provenance'].values():item['status']='ATTESTED'
        self.save()
        with self.assertRaisesRegex(DatasetError,'independently checked|self-attestation'):
            load_bundle(self.path,self.root)

    def test_altered_csv_serialization_and_reordering_preserve_observation_identity(self):
        first=self.load();rows=self.source_rows('fixture_upstream.csv')
        old_digest=digest(self.root/'fixture_upstream.csv')
        for row in rows:
            for key in FIELDS[3:]:row[key]=format(float(row[key]),'.17e')
        self.write_rows(list(reversed(rows)),name='fixture_upstream.csv',quoting=csv.QUOTE_ALL,lineterminator='\r\n')
        self.assertNotEqual(old_digest,digest(self.root/'fixture_upstream.csv'))
        refresh_lineage(self.root,self.doc);second=self.load()
        self.assertEqual(first.admission_report['canonical_semantic_sha256'],second.admission_report['canonical_semantic_sha256'])
        self.assertEqual(first.admission_report['confirmatory_status'],'BLOCKED_CONFIRMATORY_TEST')
        self.assertEqual(first.admission_report['accepted_origins'],second.admission_report['accepted_origins'])

    def test_lineage_mismatch_cannot_be_hidden_by_updating_byte_hashes(self):
        rows=self.source_rows('fixture_upstream.csv');rows[0]['power_kw']='99999';self.write_rows(rows,name='fixture_upstream.csv')
        refresh_lineage(self.root,self.doc)
        with self.assertRaisesRegex(DatasetError,'transformation does not match'):self.load()

    def test_duplicate_observations_headers_and_malformed_csv_rows_rejected(self):
        rows=self.source_rows('fixture_upstream.csv');self.write_rows(rows+[rows[0]],name='fixture_upstream.csv');refresh_lineage(self.root,self.doc)
        with self.assertRaisesRegex(DatasetError,'Duplicate'):self.load()
        path=self.root/'ambiguous.csv';path.write_text('event_time,event_time\na,b\n')
        with self.assertRaises(AdmissionError):_read_measurements(path,{k:k for k in FIELDS})
        valid=self.source_rows();path.write_text(','.join(FIELDS)+'\n'+','.join(valid[0][k] for k in FIELDS)+',extra\n')
        with self.assertRaisesRegex(AdmissionError,'Malformed'):_read_measurements(path,{k:k for k in FIELDS})

    def test_unknown_transform_options_and_nonaware_measurement_rejected(self):
        path=self.root/self.doc['lineage_manifest']['path'];manifest=json.loads(path.read_text());manifest['transformation']['invent_latency_seconds']=0
        path.write_text(json.dumps(manifest));self.doc['lineage_manifest']['sha256']=digest(path)
        with self.assertRaisesRegex(DatasetError,'Unsupported'):self.load()
        row=self.source_rows()[0];row['event_time']='2030-01-01 00:00:00';path=self.root/'naive.csv';self.write_rows([row],name=path.name)
        with self.assertRaisesRegex(AdmissionError,'timestamp'):_read_measurements(path,{k:k for k in FIELDS})

    def test_missing_exclusion_policy_and_silent_origin_omission_rejected(self):
        original=json.loads(json.dumps(self.doc));del self.doc['cohort_policy']
        with self.assertRaisesRegex(DatasetError,'policy'):self.load()
        self.doc=original;self.doc['partitions']['development'].pop(0)
        with self.assertRaisesRegex(DatasetError,'Silent|omission'):self.load()

    def test_gaps_and_rejected_support_are_accounted_with_denominators(self):
        # Remove required support at the first declared source slot, including an edge gap.
        for name in ('fixture_measurements.csv','fixture_upstream.csv'):
            self.write_rows(self.source_rows(name)[1:],name=name)
        refresh_lineage(self.root,self.doc)
        with self.assertRaisesRegex(DatasetError,'gaps'):self.load()
        policy=self.policy();policy['gaps']='declared_missing_slots_only';policy['declared_missing_measurements']=['2030-01-01T00:00:00+00:00']
        rejected=self.doc['partitions']['train'].pop(0)
        policy['excluded_origins']=[{'role':'train','origin_time':rejected['origin_time'],'reason':'missing_feature_support'}]
        self.save_policy(policy);bundle=self.load();report=bundle.admission_report
        self.assertEqual(report['expected_measurement_slots'],165);self.assertEqual(report['observed_measurements'],164)
        self.assertEqual(report['missing_measurement_count'],1);self.assertEqual(report['roles']['train']['candidate_origins'],80)
        self.assertEqual(report['roles']['train']['accepted_origins'],79);self.assertEqual(report['excluded_origin_count'],1)
        self.assertEqual(report['rejected_origins'][0]['missing_feature_times'],['2030-01-01T00:00:00+00:00'])

    def test_unsupported_or_post_outcome_exclusions_and_unauthorized_periods_rejected(self):
        policy=self.policy();policy['excluded_origins']=[{'role':'train','origin_time':self.doc['partitions']['train'][0]['origin_time'],'reason':'bad_forecast_error'}]
        self.save_policy(policy)
        with self.assertRaisesRegex(DatasetError,'unsupported'):self.load()
        policy['excluded_origins']=[];policy['declared_at']=self.doc['partitions']['train'][0]['origin_time'];self.save_policy(policy)
        with self.assertRaisesRegex(DatasetError,'precede'):self.load()
        policy['declared_at']='2029-12-31T00:00:00+00:00';policy['authorized_periods']['train']['start']='2030-01-01T01:00:00+00:00';self.save_policy(policy)
        with self.assertRaisesRegex(DatasetError,'authorized source period'):self.load()

    def test_historical_content_exposure_survives_source_alias_and_row_order(self):
        lineage=verify_lineage(self.doc,self.root,'SYNTHETIC_FIXTURE')
        registry={tuple(float(lineage.measurements[t][k]).hex() for k in FIELDS[3:]):[datetime(2018,12,1)] for t in list(lineage.measurements)[:10]}
        with patch('publication_v2.stage2.lineage.historical_registry',return_value=registry):
            with self.assertRaisesRegex(DatasetError,'Historically evaluated'):self.load()
            rows=self.source_rows('fixture_upstream.csv');self.write_rows(list(reversed(rows)),name='fixture_upstream.csv',quoting=csv.QUOTE_ALL)
            refresh_lineage(self.root,self.doc)
            # A new claimed namespace plus changed CSV bytes still cannot erase the signal/observation match.
            path=self.root/self.doc['lineage_manifest']['path'];manifest=json.loads(path.read_text());manifest['source_identity']['dataset']='new-name'
            path.write_text(json.dumps(manifest));self.doc['lineage_manifest']['sha256']=digest(path)
            with self.assertRaisesRegex(DatasetError,'Historically evaluated'):self.load()

    def test_exposure_boundary_must_match_preserved_schedule(self):
        policy=json.loads(POLICY.read_text());policy['known_historical_source']['native_evaluation_start']='2099-01-01 00:00:00'
        with self.assertRaisesRegex(AdmissionError,'preserved evaluation schedule'):historical_registry(policy)

    def test_review_cannot_be_reused_with_changed_scientific_metadata(self):
        self.doc['dataset_kind']='REAL_DEVELOPMENT'
        for item in self.doc['provenance'].values():item['status']='ATTESTED'
        manifest_path=self.root/self.doc['lineage_manifest']['path'];manifest=json.loads(manifest_path.read_text())
        manifest['independent_review_id']='FIXTURE_NOT_REAL_REVIEW';manifest_path.write_text(json.dumps(manifest));self.doc['lineage_manifest']['sha256']=digest(manifest_path)
        review={'independently_checked':True,'lineage_manifest_sha256':self.doc['lineage_manifest']['sha256'],
                'cohort_policy_sha256':self.doc['cohort_policy']['sha256'],'source_identity':manifest['source_identity'],
                'provenance_sha256':hashlib.sha256(json.dumps(self.doc['provenance'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                'dataset_document_sha256':hashlib.sha256(json.dumps(self.doc,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
        # This mock is only an adversarial test of a future registry, not an installed approval.
        policy=json.loads(POLICY.read_text());policy['real_data_reviews']={'FIXTURE_NOT_REAL_REVIEW':review}
        original_read=Path.read_text
        def read(path,*args,**kwargs):return json.dumps(policy) if path==POLICY else original_read(path,*args,**kwargs)
        self.doc['provenance']['availability']['value']='silently replaced metadata';self.save()
        with patch.object(Path,'read_text',read):
            with self.assertRaisesRegex(DatasetError,'provenance'):load_bundle(self.path,self.root)

    def test_duplicate_observation_id_at_different_time_is_rejected(self):
        rows=self.source_rows('fixture_upstream.csv');rows[1]['source_observation_id']=rows[0]['source_observation_id']
        self.write_rows(rows,name='fixture_upstream.csv');refresh_lineage(self.root,self.doc)
        with self.assertRaisesRegex(DatasetError,'Duplicate'):self.load()

    def test_missing_target_and_rejected_origin_reasons_are_retained(self):
        # Last scoring origin requires t+60 at 26:00 (index156), absent from both sources.
        missing='2030-01-02T02:00:00+00:00'
        for name in ('fixture_measurements.csv','fixture_upstream.csv'):
            self.write_rows([r for r in self.source_rows(name) if r['event_time']!=missing],name=name)
        refresh_lineage(self.root,self.doc);policy=self.policy()
        policy.update(gaps='declared_missing_slots_only',declared_missing_measurements=[missing])
        rejected=self.doc['partitions']['development'].pop()
        policy['excluded_origins']=[{'role':'development','origin_time':rejected['origin_time'],'reason':'missing_target_support'}]
        self.save_policy(policy);bundle=self.load()
        self.assertEqual(bundle.admission_report['roles']['development']['candidate_origins'],12)
        self.assertEqual(bundle.admission_report['roles']['development']['accepted_origins'],11)
        self.assertEqual(bundle.admission_report['rejected_origins'][0]['missing_target_times'],[missing])


if __name__=='__main__':unittest.main()
