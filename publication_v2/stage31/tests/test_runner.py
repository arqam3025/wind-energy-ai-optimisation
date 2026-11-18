"""Synthetic-only runner integrity; all outputs use owned isolated runs folders."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from publication_v2.stage31 import runner
from publication_v2.stage31.scenarios import make_scenarios

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.base=runner.ROOT/'publication_v2/stage31/runs'
        self.base.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(prefix='test_',dir=self.base)
        self.root=Path(self.temporary.name).resolve()
        self.assertTrue(self.root.is_relative_to(self.base.resolve()))
        self.addCleanup(self.temporary.cleanup)
        self.fixture=(make_scenarios(8,8)[0],)

    def run_small(self,name):
        with patch.object(runner,'make_scenarios',return_value=self.fixture):
            return runner.run_experiments(run_id=name,seed=8,steps=8,output_root=self.root)

    def test_completion_manifest_and_hash_verification(self):
        directory,manifest=self.run_small('valid')
        self.assertEqual(manifest['comparison_rows'],5)
        self.assertEqual(manifest,runner.verify_run(directory))
        self.assertEqual(manifest['models_trained'],0)
        self.assertEqual(manifest['development_stage'],'STAGE31_SYNTHETIC_ONLY')
        self.assertNotIn('development_code_uncommitted',manifest)
        self.assertEqual(manifest['data_admission'],'PENDING_REVIEW')
        self.assertTrue((directory/'COMPLETED.json').is_file())
        self.assertFalse((directory/'FAILED.json').exists())

    def test_existing_run_is_never_overwritten(self):
        directory,_=self.run_small('same');before=(directory/'COMPLETED.json').read_bytes()
        with self.assertRaises(FileExistsError):self.run_small('same')
        self.assertEqual((directory/'COMPLETED.json').read_bytes(),before)

    def test_failure_has_no_false_completion(self):
        with patch.object(runner,'make_scenarios',return_value=self.fixture),patch.object(runner,'simulate',side_effect=RuntimeError('synthetic forced failure')):
            with self.assertRaises(RuntimeError):runner.run_experiments(run_id='failed',output_root=self.root)
        directory=self.root/'failed'
        self.assertTrue((directory/'FAILED.json').exists());self.assertFalse((directory/'COMPLETED.json').exists())

    def test_changed_artifact_rejected(self):
        directory,_=self.run_small('tamper')
        (directory/'summary.csv').write_text('not original synthetic metrics',encoding='utf-8')
        with self.assertRaises(ValueError):runner.verify_run(directory)

    def test_changed_scope_marker_rejected(self):
        directory,_=self.run_small('scope')
        p=directory/'COMPLETED.json';marker=json.loads(p.read_text());marker['confirmatory_status']='CONFIRMED';p.write_text(json.dumps(marker))
        with self.assertRaises(ValueError):runner.verify_run(directory)

    def test_source_change_during_execution_fails_closed(self):
        with patch.object(runner,'make_scenarios',return_value=self.fixture),patch.object(runner,'_source_hashes',side_effect=[{'synthetic.py':'old'},{'synthetic.py':'new'}]):
            with self.assertRaises(ValueError):runner.run_experiments(run_id='source_changed',output_root=self.root)
        self.assertTrue((self.root/'source_changed/FAILED.json').exists())
        self.assertFalse((self.root/'source_changed/COMPLETED.json').exists())

    def test_repeated_seed_dispatch_and_non_timing_metrics_match(self):
        a,_=self.run_small('first');b,_=self.run_small('second')
        self.assertEqual(runner.compare_runs(a,b)['status'],'REPRODUCED_EXCLUDING_TIMINGS')

    def test_escaping_outputs_and_unsafe_id_rejected(self):
        with self.assertRaises(ValueError):runner.run_experiments(run_id='../outside',output_root=self.root)
        with self.assertRaises(ValueError):runner._inside(runner.ROOT.parent/'outside')
        p=self.root/'existing.json';p.write_text('{}')
        with self.assertRaises(FileExistsError):runner._json(p,{})

if __name__=='__main__':unittest.main()
