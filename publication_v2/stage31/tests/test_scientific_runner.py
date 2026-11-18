"""Adversarial synthetic evidence verification; owned temporary outputs only."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from publication_v2.stage31 import runner
from publication_v2.stage31.scenarios import make_scenarios


class ScientificRunnerTests(unittest.TestCase):
    def setUp(self):
        base=runner.ROOT/'publication_v2/stage31/runs'
        base.mkdir(parents=True,exist_ok=True)
        temporary=tempfile.TemporaryDirectory(prefix='scientific_verify_',dir=base)
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve()
        self.assertTrue(self.root.is_relative_to(base.resolve()))
        with patch.object(runner,'make_scenarios',return_value=(make_scenarios(8,8)[0],)):
            self.directory,self.manifest=runner.run_experiments(run_id='owned',seed=8,steps=8,output_root=self.root)

    def write_manifest(self,manifest):
        # Deliberately recreate self-consistent checksums: this tests schema and
        # semantic verification, not authentication of a manifest's authorship.
        path=self.directory/'manifest.json'
        path.write_text(json.dumps(manifest,sort_keys=True,allow_nan=False),encoding='utf-8')
        marker=json.loads((self.directory/'COMPLETED.json').read_text())
        marker['manifest_sha256']=runner.digest(path)
        (self.directory/'COMPLETED.json').write_text(json.dumps(marker),encoding='utf-8')

    def rewrite_json_artifact(self,relative,value,manifest=None):
        path=self.directory/relative
        path.write_text(json.dumps(value,sort_keys=True,allow_nan=False),encoding='utf-8')
        manifest=deepcopy(self.manifest if manifest is None else manifest)
        manifest['artifact_sha256'][relative]=runner.digest(path)
        self.write_manifest(manifest)
        return manifest

    def test_new_manifest_records_governance_input_and_strict_schema(self):
        self.assertEqual(self.manifest['schema_version'],runner.SCHEMA_VERSION)
        self.assertEqual(self.manifest['input_sha256'][runner.POLICY_INPUT],runner.digest(runner.ROOT/runner.POLICY_INPUT))
        self.assertEqual(runner.verify_run(self.directory),self.manifest)

    def test_empty_or_missing_inventories_fail_even_with_matching_completion_hash(self):
        for name in ('artifact_sha256','source_sha256','input_sha256'):
            for absent in (False,True):
                with self.subTest(name=name,absent=absent):
                    manifest=deepcopy(self.manifest)
                    if absent:manifest.pop(name)
                    else:manifest[name]={}
                    self.write_manifest(manifest)
                    with self.assertRaises(ValueError):runner.verify_run(self.directory)

    def test_source_inventory_cannot_omit_an_existing_source(self):
        manifest=deepcopy(self.manifest)
        manifest['source_sha256'].pop(next(iter(manifest['source_sha256'])))
        self.write_manifest(manifest)
        with self.assertRaisesRegex(ValueError,'source inventory'):runner.verify_run(self.directory)

    def test_exact_artifact_membership_rejects_omission_and_unlisted_files(self):
        manifest=deepcopy(self.manifest);manifest['artifact_sha256'].pop('summary.csv')
        self.write_manifest(manifest)
        with self.assertRaises(ValueError):runner.verify_run(self.directory)
        self.write_manifest(self.manifest)
        (self.directory/'unexpected.txt').write_text('owned synthetic extra',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'membership'):runner.verify_run(self.directory)

    def test_rehashed_unexpected_artifact_is_still_rejected(self):
        path=self.directory/'unexpected.json';path.write_text('{}',encoding='utf-8')
        manifest=deepcopy(self.manifest);manifest['artifact_sha256']['unexpected.json']=runner.digest(path)
        self.write_manifest(manifest)
        with self.assertRaisesRegex(ValueError,'membership'):runner.verify_run(self.directory)

    def test_declared_counts_scope_identity_and_schema_are_validated(self):
        cases={'scenario_count':999,'comparison_rows':0,'controller_count':4,
            'steps_per_scenario':7,'seed':True,'models_trained':False,'run_id':'other',
            'schema_version':'publication_v2.stage31.synthetic-run.v1',
            'data_admission':'APPROVED','confirmatory_status':'CONFIRMED',
            'created_at_utc':'2031-01-01T00:00:00','environment':{}}
        for name,value in cases.items():
            with self.subTest(name=name):
                manifest=deepcopy(self.manifest);manifest[name]=value;self.write_manifest(manifest)
                with self.assertRaises(ValueError):runner.verify_run(self.directory)

    def test_governance_hash_and_required_policy_identity_cannot_be_omitted(self):
        for mapping in ({runner.POLICY_INPUT:'0'*64}, {'publication_v2/stage31/requirements.txt':runner.digest(runner.ROOT/'publication_v2/stage31/requirements.txt')}):
            manifest=deepcopy(self.manifest);manifest['input_sha256']=mapping;self.write_manifest(manifest)
            with self.assertRaises(ValueError):runner.verify_run(self.directory)

    def test_escaping_or_aliased_inventory_paths_are_rejected(self):
        for relative in ('../outside.json','traces/../summary.csv','./summary.csv','C:/private/file','traces\\file.json'):
            with self.subTest(relative=relative):
                manifest=deepcopy(self.manifest);manifest['artifact_sha256'][relative]='0'*64
                self.write_manifest(manifest)
                with self.assertRaises(ValueError):runner.verify_run(self.directory)

    def test_comparison_fingerprint_is_recomputed(self):
        manifest=deepcopy(self.manifest);manifest['comparison_fingerprint']='0'*64;self.write_manifest(manifest)
        with self.assertRaisesRegex(ValueError,'fingerprint'):runner.verify_run(self.directory)

    def test_saved_trace_fingerprints_are_recomputed_not_trusted(self):
        fingerprints=json.loads((self.directory/'trace_fingerprints.json').read_text())
        fingerprints[next(iter(fingerprints))]='0'*64
        self.rewrite_json_artifact('trace_fingerprints.json',fingerprints)
        with self.assertRaisesRegex(ValueError,'fingerprint'):runner.verify_run(self.directory)

    def test_authenticated_trace_must_have_declared_controller_and_denominator(self):
        relative='traces/stable__uncontrolled.json'
        original=json.loads((self.directory/relative).read_text())
        for name,value in (('controller','adaptive'),('rows',original['rows'][:-1]),('plans',original['plans'][:-1])):
            with self.subTest(name=name):
                run=deepcopy(original);run[name]=value
                self.rewrite_json_artifact(relative,run)
                with self.assertRaises(ValueError):runner.verify_run(self.directory)

    def test_authenticated_metrics_must_reproduce_from_trace(self):
        relative='traces/stable__uncontrolled.json';run=json.loads((self.directory/relative).read_text())
        run['metrics']['ramp_violations']+=1
        self.rewrite_json_artifact(relative,run)
        with self.assertRaisesRegex(ValueError,'metrics'):runner.verify_run(self.directory)

    def test_authenticated_metric_table_must_match_traces(self):
        metrics=json.loads((self.directory/'metrics.json').read_text());metrics[0]['total_throughput_kwh']+=1
        self.rewrite_json_artifact('metrics.json',metrics)
        with self.assertRaisesRegex(ValueError,'metric table'):runner.verify_run(self.directory)

    def test_validation_evidence_and_csv_are_recomputed(self):
        validation=json.loads((self.directory/'validation.json').read_text());validation['battery_soc_violations']=999
        self.rewrite_json_artifact('validation.json',validation)
        with self.assertRaisesRegex(ValueError,'validation'):runner.verify_run(self.directory)
        self.rewrite_json_artifact('validation.json',json.loads((self.directory/'validation.json').read_text()) | {'battery_soc_violations':0})
        path=self.directory/'summary.csv';path.write_text(path.read_text().replace('SYNTHETIC_ONLY','FAKE'),encoding='utf-8')
        manifest=deepcopy(self.manifest);manifest['artifact_sha256']['summary.csv']=runner.digest(path)
        manifest['artifact_sha256']['validation.json']=runner.digest(self.directory/'validation.json');self.write_manifest(manifest)
        with self.assertRaisesRegex(ValueError,'CSV'):runner.verify_run(self.directory)

    def test_changed_governance_input_during_execution_fails_closed(self):
        output=self.root/'policy_changed'
        original=runner.digest
        calls=0
        def changed_policy_digest(path):
            nonlocal calls
            if Path(path)==runner.ROOT/runner.POLICY_INPUT:
                calls+=1
                return '0'*64 if calls>1 else original(path)
            return original(path)
        with patch.object(runner,'make_scenarios',return_value=(make_scenarios(8,8)[0],)),patch.object(runner,'digest',side_effect=changed_policy_digest):
            with self.assertRaisesRegex(ValueError,'governance input'):
                runner.run_experiments(run_id='policy_changed',seed=8,steps=8,output_root=self.root)
        self.assertTrue((output/'FAILED.json').is_file())
        self.assertFalse((output/'COMPLETED.json').exists())

    def test_failed_marker_prevents_success_even_if_completed_marker_exists(self):
        (self.directory/'FAILED.json').write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'completion'):runner.verify_run(self.directory)

    def test_nonfinite_and_duplicate_json_metadata_fail_closed(self):
        path=self.directory/'manifest.json'
        for content in ('{"schema_version": "a", "schema_version": "b"}','{"bad": NaN}'):
            path.write_text(content,encoding='utf-8')
            marker=json.loads((self.directory/'COMPLETED.json').read_text());marker['manifest_sha256']=runner.digest(path)
            (self.directory/'COMPLETED.json').write_text(json.dumps(marker),encoding='utf-8')
            with self.assertRaises(ValueError):runner.verify_run(self.directory)


if __name__=='__main__':unittest.main()
