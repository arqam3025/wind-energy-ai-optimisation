"""Clearly labelled synthetic fixtures: fitted outputs are not research results."""
from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from publication_v2.stage2.forecasting import (FEATURE_NAMES, HORIZONS, DependencyUnavailable,
    ForecastingError, _configuration, _native_lightgbm_sampling, file_sha256,
    fit_forecaster, load_forecaster, save_forecaster)


def synthetic_fixture():
    rng = np.random.default_rng(20301101)
    x = rng.uniform(0, 10, size=(48, len(FEATURE_NAMES)))
    y = np.column_stack([np.maximum(0, x[:,0] + .1*h*x[:,1] - .2*x[:,2]) for h in range(1,7)])
    return x, y


class ForecastingContractTests(unittest.TestCase):
    def test_persistence_uses_only_current_feature_and_common_horizons(self):
        x,y = synthetic_fixture()
        model = fit_forecaster('persistence', x, y)
        current = x[:3].copy(); current[0,0] = -1
        predicted = model.predict(current)
        self.assertEqual(predicted.shape, (3,6))
        np.testing.assert_array_equal(predicted[:,0], np.maximum(0,current[:,0]))
        np.testing.assert_array_equal(predicted, np.repeat(predicted[:,:1],6,axis=1))
        self.assertNotIn('targets', inspect.signature(model.predict).parameters)

    def test_prediction_does_not_access_future_labels(self):
        x,y = synthetic_fixture(); model = fit_forecaster('persistence',x,y)
        before=model.predict(x);y[:]=1e9
        np.testing.assert_array_equal(before,model.predict(x))

    def test_missing_feature_targets_and_nonfinite_inputs_fail(self):
        x,y=synthetic_fixture()
        invalid = [(x[:,:-1],y),(x,y[:,:-1]),(x,y[:-1]),(np.empty((0,14)),np.empty((0,6)))]
        bad=x.copy();bad[0,0]=np.nan; invalid.append((bad,y))
        bad=y.copy();bad[0,0]=-1;invalid.append((x,bad))
        for a,b in invalid:
            with self.subTest(shape=(a.shape,b.shape)),self.assertRaises(ForecastingError): fit_forecaster('persistence',a,b)

    def test_input_column_order_is_not_silently_repaired(self):
        x,y=synthetic_fixture()
        class NamedMatrix:
            columns=tuple(reversed(FEATURE_NAMES))
            def __array__(self,dtype=None,copy=None): return np.asarray(x,dtype=dtype)
        with self.assertRaisesRegex(ForecastingError,'Column order'):fit_forecaster('persistence',NamedMatrix(),y)

    def test_seed_threads_objective_and_score_access_are_not_overridden(self):
        x,y=synthetic_fixture()
        for name in ('xgboost','lightgbm'):
            for override in ({'n_jobs':8},{'random_state':0},{'eval_set':[]},{'early_stopping_rounds':2},{'objective':'reg:absoluteerror'}):
                with self.subTest(name=name,override=override),self.assertRaises(ForecastingError): fit_forecaster(name,x,y,hyperparameters=override)
        with self.assertRaises(ForecastingError):fit_forecaster('unknown',x,y)
        with self.assertRaises(ForecastingError):fit_forecaster('xgboost',x,y,seed=True)

    def test_lightgbm_frequency_resolves_to_an_effective_explicit_configuration(self):
        default=_configuration('lightgbm',17,None)
        self.assertEqual((default['subsample'],default['subsample_freq']),(1,0))
        automatic=_configuration('lightgbm',17,{'subsample':.5})
        self.assertEqual((automatic['subsample'],automatic['subsample_freq']),(.5,1))
        explicit=_configuration('lightgbm',17,{'subsample':.5,'subsample_freq':3})
        self.assertEqual(explicit['subsample_freq'],3)
        self.assertEqual(explicit['random_state'],17)
        self.assertEqual(explicit['n_jobs'],1)
        self.assertEqual(explicit['objective'],'regression')

    def test_lightgbm_rejects_ineffective_or_unsupported_sampling_requests(self):
        requests=[{'subsample':.5,'subsample_freq':0},
                  {'subsample':1,'subsample_freq':1},
                  {'bagging_freq':1},{'bagging_fraction':.5}]
        requests.extend({'subsample':.5,'subsample_freq':value} for value in (-1,True,1.5,'1',np.inf,2**31))
        for request in requests:
            with self.subTest(request=request),self.assertRaises(ForecastingError):
                _configuration('lightgbm',17,request)
        with self.assertRaisesRegex(ForecastingError,'Unsupported'):
            _configuration('xgboost',17,{'subsample_freq':1})

    def test_lightgbm_backend_sampling_must_be_inspectable_and_match_effective_input(self):
        class NativeFixture:
            def __init__(self,text):self.text=text
            def model_to_string(self):return self.text
        parameters=_configuration('lightgbm',17,{'subsample':.5})
        invalid=['', '[bagging_fraction: 0.5]\n[bagging_freq: 0]',
                 '[bagging_fraction: 1]\n[bagging_freq: 1]',
                 '[bagging_fraction: nan]\n[bagging_freq: 1]',
                 '[bagging_fraction: 0.5]\n[bagging_freq: 1]\n[bagging_freq: 1]']
        for native in invalid:
            with self.subTest(native=native),self.assertRaisesRegex(ForecastingError,'native sampling'):
                _native_lightgbm_sampling(NativeFixture(native),parameters)
        verified=_native_lightgbm_sampling(NativeFixture('[bagging_fraction: 0.5]\n[bagging_freq: 1]'),parameters)
        self.assertEqual(verified['bagging_fraction'],.5)
        self.assertEqual(verified['bagging_freq'],1)
        self.assertTrue(verified['row_bagging_active'])

    def test_missing_dependency_is_explicit_never_silent_model_drop(self):
        x,y=synthetic_fixture()
        with patch('publication_v2.stage2.forecasting.package_metadata.version', side_effect=__import__('importlib.metadata',fromlist=['PackageNotFoundError']).PackageNotFoundError):
            with self.assertRaises(DependencyUnavailable):fit_forecaster('lightgbm',x,y)

    def test_persistence_exclusive_artifact_and_manifest_identity(self):
        x,y=synthetic_fixture();model=fit_forecaster('persistence',x,y)
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'synthetic_fixture'
            manifest=save_forecaster(model,directory,training_provenance={'purpose':'synthetic_fixture_only'})
            sha=file_sha256(directory/'manifest.json')
            loaded=load_forecaster(directory,expected_manifest_sha256=sha)
            np.testing.assert_array_equal(model.predict(x),loaded.predict(x))
            self.assertEqual(manifest['model_files_sha256'],{})
            with self.assertRaises(FileExistsError):save_forecaster(model,directory,training_provenance={'purpose':'synthetic_fixture_only'})
            data=json.loads((directory/'manifest.json').read_text());data['seed']=0
            (directory/'manifest.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ForecastingError,'manifest hash'):load_forecaster(directory,expected_manifest_sha256=sha)

    def test_partial_artifact_and_missing_provenance_are_rejected(self):
        x,y=synthetic_fixture();model=fit_forecaster('persistence',x,y)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ForecastingError):save_forecaster(model,Path(tmp)/'missing',training_provenance={})
            with self.assertRaises(ForecastingError):load_forecaster(Path(tmp))


class NativeSyntheticModelTests(unittest.TestCase):
    def check_model(self,name):
        x,y=synthetic_fixture()
        hyper={'n_estimators':8,'max_depth':2}
        if name=='lightgbm':hyper.update(num_leaves=3,min_child_samples=2)
        a=fit_forecaster(name,x,y,seed=17,hyperparameters=hyper)
        b=fit_forecaster(name,x,y.copy(),seed=17,hyperparameters=hyper)
        self.assertEqual(len(a.estimators),6)
        self.assertEqual(a.hyperparameters['n_jobs'],1)
        np.testing.assert_array_equal(a.predict(x),b.predict(x))
        self.assertTrue(np.isfinite(a.predict(x)).all())
        self.assertGreaterEqual(a.predict(x).min(),0)
        persisted=fit_forecaster('persistence',x,y,seed=17)
        self.assertEqual(a.training_features_sha256,persisted.training_features_sha256)
        self.assertEqual(a.training_targets_sha256,persisted.training_targets_sha256)
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/name
            manifest=save_forecaster(a,directory,training_provenance={'purpose':'synthetic_fixture_only','scored_observations_used_for_fit':False})
            self.assertEqual(len(manifest['model_files_sha256']),6)
            self.assertEqual(manifest['requested_hyperparameters'],hyper)
            self.assertEqual(manifest['hyperparameters'],a.hyperparameters)
            repeated=save_forecaster(b,Path(tmp)/f'{name}_repeat',training_provenance={'purpose':'synthetic_fixture_only'})
            self.assertEqual(manifest['model_files_sha256'],repeated['model_files_sha256'])
            restored=load_forecaster(directory,expected_manifest_sha256=file_sha256(directory/'manifest.json'))
            np.testing.assert_array_equal(a.predict(x),restored.predict(x))
            if name=='xgboost':
                for estimator in restored.estimators:
                    generic=json.loads(estimator.get_booster().save_config())['learner']['generic_param']
                    self.assertEqual(estimator.get_params()['n_jobs'],1)
                    self.assertEqual(estimator.get_params()['random_state'],17)
                    self.assertEqual(generic['nthread'],'1')
                    self.assertEqual(generic['n_jobs'],'1')
                    self.assertEqual(generic['seed'],'17')
                    self.assertEqual(generic['random_state'],'17')
                # Reapplying a runtime profile never rewrites persisted native trees.
                self.assertEqual(manifest['model_files_sha256'],{filename:file_sha256(directory/filename)
                    for filename in manifest['model_files_sha256']})
            else:
                self.assertEqual(len(manifest['native_row_sampling']),6)
                for sampling,config in zip(manifest['native_row_sampling'],manifest['native_training_configs']):
                    self.assertEqual((sampling['bagging_fraction'],sampling['bagging_freq']),(1,0))
                    self.assertFalse(sampling['row_bagging_active'])
                    self.assertEqual(config['subsample_freq'],0)
                    self.assertEqual(config['num_threads'],1)
                    self.assertEqual(config['random_state'],17)
                    self.assertEqual(config['objective'],'regression')
            first=directory/next(iter(manifest['model_files_sha256']))
            with first.open('ab') as stream:stream.write(b'\ncorruption')
            with self.assertRaisesRegex(ForecastingError,'hash mismatch'):load_forecaster(directory)

    @unittest.skipUnless(importlib.util.find_spec('xgboost') is not None,'Optional XGBoost dependency absent')
    def test_xgboost_actual_fit_native_reload_and_reproducibility_synthetic(self):self.check_model('xgboost')

    @unittest.skipUnless(importlib.util.find_spec('lightgbm') is not None,'Optional LightGBM dependency absent')
    def test_lightgbm_actual_fit_native_reload_and_reproducibility_synthetic(self):self.check_model('lightgbm')

    @unittest.skipUnless(importlib.util.find_spec('lightgbm') is not None,'Optional LightGBM dependency absent')
    def test_lightgbm_actual_native_row_bagging_and_sampling_metadata(self):
        x,y=synthetic_fixture()
        requested={'n_estimators':4,'max_depth':2,'num_leaves':3,'min_child_samples':2,'subsample':.5}
        model=fit_forecaster('lightgbm',x,y,seed=17,hyperparameters=requested)
        self.assertNotIn('subsample_freq',requested)
        self.assertEqual(model.requested_hyperparameters,requested)
        self.assertEqual(model.hyperparameters['subsample_freq'],1)
        for estimator in model.estimators:
            native=estimator.model_to_string()
            self.assertIn('[bagging_fraction: 0.5]',native)
            self.assertIn('[bagging_freq: 1]',native)
            self.assertIn('[num_threads: 1]',native)
            self.assertIn('[bagging_seed: 17]',native)
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'synthetic_bagging'
            manifest=save_forecaster(model,directory,training_provenance={'purpose':'synthetic_fixture_only'})
            self.assertEqual(manifest['requested_hyperparameters'],requested)
            self.assertEqual(manifest['hyperparameters']['subsample_freq'],1)
            for sampling in manifest['native_row_sampling']:
                self.assertEqual((sampling['bagging_fraction'],sampling['bagging_freq']),(.5,1))
                self.assertTrue(sampling['row_bagging_active'])
            loaded=load_forecaster(directory)
            np.testing.assert_array_equal(model.predict(x),loaded.predict(x))
            manifest['native_row_sampling'][0]['bagging_freq']=0
            (directory/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ForecastingError,'sampling metadata'):
                load_forecaster(directory)
            manifest['native_row_sampling'][0]['bagging_freq']=1
            manifest['requested_hyperparameters']['subsample']=1
            (directory/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ForecastingError,'hyperparameters are inconsistent'):
                load_forecaster(directory)


if __name__=='__main__':unittest.main()
