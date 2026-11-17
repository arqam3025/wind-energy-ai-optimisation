import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from publication_v2.stage2.tests.fixtures import dataset
from publication_v2.stage2.workflow import (run_development,verify_run,_directory,_require_full_panel,
                                           WorkflowError,SOURCE_ROOT,_validate_completion_scope)


class WorkflowTests(unittest.TestCase):
    def test_completion_cannot_claim_confirmation_or_missing_artifacts(self):
        manifest={'schema_version':'publication_v2.stage2.run.v1','stage':2,'scope':'DEVELOPMENT_ONLY',
                  'status':'BLOCKED_DEVELOPMENT_EXPERIMENT','confirmatory_status':'BLOCKED_CONFIRMATORY_TEST',
                  'experiment_executed':False,'research_metrics_available':False,'new_real_models_trained':0,'blockers':['missing'],
                  'artifact_sha256':{name:'a'*64 for name in ('blockers.json','data_readiness.svg','causal_contract.svg','STARTED.json',
                      'preservation_before.json','preservation_after.json','forecast_metrics.json','uncertainty_metrics.json','ablation_metrics.json')}}
        marker={k:manifest[k] for k in ('schema_version','stage','status','confirmatory_status','experiment_executed')}
        _validate_completion_scope(manifest,marker)
        for key,value in (('confirmatory_status','CONFIRMATORY_READY'),('stage',3),('schema_version','other'),('experiment_executed',True),('status','CONFIRMED')):
            with self.subTest(key=key),self.assertRaises(WorkflowError):_validate_completion_scope({**manifest,key:value},{**marker,key:value})
        with self.assertRaises(WorkflowError):_validate_completion_scope({**manifest,'artifact_sha256':{}},marker)

    def test_dangling_marker_and_namespace_redirection_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=_directory(root,'linked')
            with patch.object(Path,'is_symlink',autospec=True,side_effect=lambda p:p==run/'FAILED.json'):
                with self.assertRaises(Exception):verify_run(run,root=root)
            with patch.object(Path,'is_junction',autospec=True,side_effect=lambda p:p==root/'publication_v2'):
                with self.assertRaises(Exception):_directory(root,'junction')
    def test_missing_input_is_failed_without_fit_or_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch('publication_v2.stage2.workflow.fit_forecaster') as fit:
                with self.assertRaises(Exception):run_development(root/'missing.json','missing',root=root)
                fit.assert_not_called()
            directory=root/'publication_v2/stage2/runs/missing'
            self.assertTrue((directory/'FAILED.json').exists());self.assertFalse((directory/'COMPLETED.json').exists())

    def test_unsafe_id_and_existing_partial_directory_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for run in ('../outside','CON','COM9','LPT8','bad name'):
                with self.assertRaises(WorkflowError):_directory(root,run)
            _directory(root,'partial')
            with self.assertRaises(FileExistsError):_directory(root,'partial')

    def test_invalid_metadata_rejected_before_any_model_fit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=dataset(root);doc=json.loads(path.read_text());doc['provenance']['availability']['status']='UNKNOWN';path.write_text(json.dumps(doc))
            with patch('publication_v2.stage2.workflow.fit_forecaster') as fit:
                with self.assertRaises(Exception):run_development(path,'invalid',root=root,allow_synthetic=True)
                fit.assert_not_called()

    def test_truncated_joint_panel_refused(self):
        rows=[{'model':model,'origin_time':'one','horizon_minutes':h} for model in ('persistence','xgboost','lightgbm') for h in (10,20,30,40,50)]
        with self.assertRaises(WorkflowError):_require_full_panel(rows,1)

    def test_synthetic_end_to_end_repeated_native_fits_and_sealed_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=dataset(root)
            a,am=run_development(path,'first',root=root,allow_synthetic=True)
            b,bm=run_development(path,'repeat',root=root,allow_synthetic=True)
            self.assertEqual(am['interpretation'],'SYNTHETIC_SOFTWARE_TEST_ONLY')
            self.assertFalse(am['research_metrics_available']);self.assertEqual(am['new_real_models_trained'],0)
            self.assertEqual(verify_run(a,root=root)['status'],'SYNTHETIC_WORKFLOW_COMPLETED')
            for name in ('forecast_metrics.json','uncertainty_metrics.json','predictions.json','intervals.json'):
                self.assertEqual(json.loads((a/name).read_text()),json.loads((b/name).read_text()))
            for model in ('xgboost','lightgbm'):
                aa=json.loads((a/'models'/model/'manifest.json').read_text());bb=json.loads((b/'models'/model/'manifest.json').read_text())
                self.assertEqual(aa['model_files_sha256'],bb['model_files_sha256'])
            self.assertEqual(len(json.loads((a/'forecast_metrics.json').read_text())['per_horizon']),18)
            self.assertEqual(len(json.loads((a/'uncertainty_metrics.json').read_text())['per_horizon']),108)
            self.assertTrue((a/'forecast_errors.pdf').is_file())
            self.assertTrue(all(row['calibration_newest_target_time']<row['decision_time'] for row in json.loads((a/'intervals.json').read_text())['rows']))
            altered=json.loads((a/'predictions.json').read_text());altered['rows'][0]['actual_kw']+=1;(a/'predictions.json').write_text(json.dumps(altered))
            with self.assertRaises(WorkflowError):verify_run(a,root=root)


if __name__=='__main__':unittest.main()
