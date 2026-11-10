"""Offline scorer fixtures are synthetic and never research comparisons."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math
import unittest

from publication_v2.stage2.metrics import MetricError,evaluate_forecasts,evaluate_intervals

BASE=datetime(2030,1,1,tzinfo=timezone.utc)
MODELS=('persistence','xgboost','lightgbm')
METHODS=('static','rolling','weighted')


def rows():
    result=[]
    for model in MODELS:
        for i,(actual,previous) in enumerate(((100.,100.),(400.,100.))):
            origin=BASE+timedelta(days=i)
            target=origin+timedelta(minutes=10)
            result.append({'model':model,'origin_time':origin,'decision_time':origin,'target_time':target,
                'horizon_minutes':10,'prediction_kw':actual+(1. if i==0 else -3.),'actual_kw':actual,
                'actual_available_at':target,'scored_at':target+timedelta(seconds=1),
                'previous_target_time':origin,'previous_actual_kw':previous,'previous_actual_available_at':origin})
    return result


def intervals():
    result=[]
    for method in METHODS:
        for row in rows():
            result.append({**row,'method':method,'lower_kw':row['prediction_kw']-2.,'upper_kw':row['prediction_kw']+2.,
                'alpha':.1,'floor_binding':False,'calibration_newest_target_time':row['decision_time']-timedelta(minutes=10)})
    return result


class ForecastMetricTests(unittest.TestCase):
    def test_correct_rmse_bias_and_outcome_defined_rapid_errors(self):
        result=evaluate_forecasts(rows(),expected_horizons=(10,))
        summary=result['per_horizon'][0]
        self.assertEqual(summary['mae_kw'],2.)
        self.assertAlmostEqual(summary['rmse_kw'],math.sqrt(5.))
        self.assertEqual(summary['bias_forecast_minus_actual_kw'],-1.)
        self.assertEqual(summary['rapid_event_n'],1)
        self.assertEqual(summary['rapid_event_mae_kw'],3.)
        self.assertEqual(summary['mae_minus_persistence_kw'],0.)
        self.assertEqual(len(result['per_period']),6)

    def test_complex_models_can_be_worse_without_failure_or_rank_assertion(self):
        data=rows()
        for row in data:
            if row['model']=='lightgbm':row['prediction_kw']+=100.
        result=evaluate_forecasts(data,expected_horizons=(10,))
        lightgbm=next(r for r in result['per_horizon'] if r['model']=='lightgbm')
        self.assertLess(lightgbm['mae_skill_vs_persistence'],0.)

    def test_zero_reference_and_absent_rapid_stratum_are_undefined_not_fake_zero(self):
        data=rows()
        for row in data:
            row['prediction_kw']=row['actual_kw'];row['previous_actual_kw']=row['actual_kw']
        result=evaluate_forecasts(data,expected_horizons=(10,))['per_horizon'][0]
        self.assertIsNone(result['mae_skill_vs_persistence'])
        self.assertIsNone(result['rapid_event_mae_kw'])

    def test_missing_model_observation_or_duplicate_panel_refused(self):
        for data in (rows()[:-1],rows()+rows()[:1],rows()[:2]):
            with self.assertRaises(MetricError):evaluate_forecasts(data,expected_horizons=(10,))
        data=rows();data[0]['actual_kw']+=1
        with self.assertRaises(MetricError):evaluate_forecasts(data,expected_horizons=(10,))

    def test_full_six_horizon_panel_required_by_default(self):
        with self.assertRaisesRegex(MetricError,'horizon'):evaluate_forecasts(rows())
        data=[]
        for h in (10,20,30,40,50,60):
            for row in rows():
                target=row['origin_time']+timedelta(minutes=h)
                data.append({**row,'horizon_minutes':h,'target_time':target,'actual_available_at':target,
                    'scored_at':target+timedelta(seconds=1),'previous_target_time':target-timedelta(minutes=10),
                    'previous_actual_available_at':target-timedelta(minutes=10)})
        self.assertEqual(len(evaluate_forecasts(data)['per_horizon']),18)

    def test_outcome_or_previous_observation_not_available_at_scoring_rejected(self):
        for key in ('actual_available_at','previous_actual_available_at'):
            data=rows();data[0][key]=data[0]['scored_at']+timedelta(seconds=1)
            with self.assertRaises(MetricError):evaluate_forecasts(data,expected_horizons=(10,))
        data=rows();data[0]['actual_available_at']=data[0]['target_time']-timedelta(seconds=1)
        with self.assertRaises(MetricError):evaluate_forecasts(data,expected_horizons=(10,))

    def test_missing_values_naive_timestamps_and_wrong_previous_target_rejected(self):
        for key,value in [('prediction_kw',float('nan')),('actual_kw',None),('target_time',BASE.replace(tzinfo=None)),
                          ('previous_target_time',BASE+timedelta(minutes=1))]:
            data=rows();data[0][key]=value
            with self.subTest(key=key),self.assertRaises(MetricError):evaluate_forecasts(data,expected_horizons=(10,))

    def test_iso_aware_rows_match_datetime_and_do_not_mutate_inputs(self):
        data=rows();before=deepcopy(data)
        expected=evaluate_forecasts(data,expected_horizons=(10,))
        iso=[{k:(v.isoformat() if isinstance(v,datetime) else v) for k,v in row.items()} for row in data]
        self.assertEqual(evaluate_forecasts(iso,expected_horizons=(10,)),expected)
        self.assertEqual(data,before)


class CoverageMetricTests(unittest.TestCase):
    def test_coverage_width_drift_calibration_error_and_floor_rate(self):
        data=intervals();data[0]['floor_binding']=True
        result=evaluate_intervals(data,expected_horizons=(10,))
        selected=next(r for r in result['per_horizon'] if r['model']=='persistence' and r['method']=='static')
        self.assertEqual(selected['marginal_coverage'],.5)
        self.assertEqual(selected['rapid_event_coverage'],0.)
        self.assertEqual(selected['mean_interval_width_kw'],4.)
        self.assertAlmostEqual(selected['coverage_minus_reference_pp'],-40.)
        self.assertEqual(selected['floor_binding_rate'],.5)
        self.assertEqual(len(result['per_period']),18)

    def test_equal_time_calibration_or_missing_floor_metadata_rejected(self):
        for key,value in [('calibration_newest_target_time',BASE),('floor_binding',0),('upper_kw',float('inf'))]:
            data=intervals();data[0][key]=value
            with self.subTest(key=key),self.assertRaises(MetricError):evaluate_intervals(data,expected_horizons=(10,))

    def test_method_comparison_rejects_changed_forecasts_observations_and_alpha(self):
        for key,value in [('prediction_kw',101.5),('actual_kw',100.5),('alpha',.2)]:
            data=intervals();data[0][key]=value
            with self.subTest(key=key),self.assertRaises(MetricError):evaluate_intervals(data,expected_horizons=(10,))
        with self.assertRaises(MetricError):evaluate_intervals(intervals()[:-1],expected_horizons=(10,))

    def test_whole_method_or_model_unequal_alpha_rejected_by_default(self):
        for selector in (lambda row:row['method']=='weighted',lambda row:row['model']=='lightgbm'):
            data=intervals()
            for row in data:
                if selector(row):row['alpha']=.2
            with self.assertRaisesRegex(MetricError,'equal nominal alpha'):
                evaluate_intervals(data,expected_horizons=(10,))

    def test_explicit_named_alpha_sensitivity_is_labelled_and_retains_levels(self):
        data=intervals()
        for row in data:
            if row['method']=='weighted':row['alpha']=.2
        result=evaluate_intervals(data,expected_horizons=(10,),sensitivity_experiment='prespecified_alpha_sweep_v1')
        self.assertEqual(result['comparison_design'],'nominal_alpha_sensitivity_experiment')
        self.assertEqual(result['sensitivity_experiment'],'prespecified_alpha_sweep_v1')
        self.assertEqual(result['nominal_alpha_levels'],[.1,.2])
        self.assertIn('not a common-alpha method comparison',result['scope'])
        for row in result['per_horizon']:
            self.assertEqual(row['alpha'],.2 if row['method']=='weighted' else .1)
        common=evaluate_intervals(intervals(),expected_horizons=(10,))
        self.assertEqual(common['comparison_design'],'common_nominal_alpha_method_comparison')
        self.assertIsNone(common['sensitivity_experiment'])
        self.assertEqual(common['nominal_alpha_levels'],[.1])

    def test_alpha_sensitivity_requires_supported_explicit_name(self):
        data=intervals()
        for row in data:
            if row['method']=='rolling':row['alpha']=.2
        for invalid in (None,'',' ','has spaces',True,1,{}, {'name':'alpha_sweep'}, ['alpha_sweep'],'x'*129):
            with self.subTest(invalid=invalid),self.assertRaises(MetricError):
                evaluate_intervals(data,expected_horizons=(10,),sensitivity_experiment=invalid)

    def test_sensitivity_never_pools_alpha_levels_within_one_method_model_horizon(self):
        data=intervals();data[0]['alpha']=.2
        with self.assertRaisesRegex(MetricError,'coverage group'):
            evaluate_intervals(data,expected_horizons=(10,),sensitivity_experiment='prespecified_alpha_sweep_v1')

    def test_empty_or_unpaired_coverage_never_succeeds(self):
        with self.assertRaises(MetricError):evaluate_intervals([],expected_horizons=(10,))
        with self.assertRaises(MetricError):evaluate_intervals(intervals()[:6],expected_horizons=(10,))


if __name__=='__main__':unittest.main()
