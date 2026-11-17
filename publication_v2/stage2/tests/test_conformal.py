"""Causal calibration uses synthetic ledgers; no synthetic research findings."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
import unittest

from publication_v2.protocol import Residual
from publication_v2.stage2.conformal import (CalibrationConfig, CalibrationError, InsufficientCalibration,
    calibrate, finite_sample_quantile)

BASE=datetime(2030,1,2,tzinfo=timezone.utc)
MODEL='a'*64


def records(n=20,h=10):
    result=[]
    for i in range(n):
        origin=BASE-timedelta(hours=6)+timedelta(minutes=10*i)
        target=origin+timedelta(minutes=h)
        result.append(Residual(origin,origin,target,h,100.,100.+i+1,target,target,MODEL,
            BASE-timedelta(days=2),BASE-timedelta(days=1),BASE))
    return result


class CalibrationTests(unittest.TestCase):
    def test_finite_sample_rank_without_interpolation_and_infinite_case(self):
        self.assertEqual(finite_sample_quantile(list(range(1,21)),.1),(19.,19))
        self.assertEqual(finite_sample_quantile([1.]*9,.1),(1.,9))
        with self.assertRaises(InsufficientCalibration):finite_sample_quantile([1.]*8,.1)

    def test_static_and_rolling_have_predeclared_distinct_windows(self):
        data=records()
        static=calibrate(data,BASE,10,'static',MODEL)
        rolling=calibrate(data,BASE,10,'rolling',MODEL,CalibrationConfig(window=10))
        self.assertEqual(static.quantile_kw,19.)
        self.assertEqual(rolling.quantile_kw,20.)
        self.assertEqual(rolling.selected_count,10)
        self.assertEqual(rolling.eligible_count_before_window,20)
        self.assertEqual(data,records())

    def test_equal_future_and_late_available_fixed_records_rejected(self):
        equal=replace(records(1)[0],origin_time=BASE-timedelta(minutes=10),target_time=BASE,
                      issued_at=BASE-timedelta(minutes=10),observation_available_at=BASE,residual_available_at=BASE)
        future=replace(equal,origin_time=BASE,target_time=BASE+timedelta(minutes=10),issued_at=BASE,
                       observation_available_at=BASE+timedelta(minutes=10),residual_available_at=BASE+timedelta(minutes=10))
        late=replace(records(1)[0],observation_available_at=BASE+timedelta(seconds=1),residual_available_at=BASE+timedelta(seconds=1))
        for unavailable in (equal,future,late):
            with self.subTest(record=unavailable),self.assertRaises(CalibrationError):
                calibrate(records()+[unavailable],BASE,10,'static',MODEL)

    def test_future_observation_values_never_change_rolling_quantile(self):
        equal=replace(records(1)[0],origin_time=BASE-timedelta(minutes=10),target_time=BASE,
                      issued_at=BASE-timedelta(minutes=10),observation_available_at=BASE,residual_available_at=BASE)
        result=[]
        for unseen in (float('nan'),1e100,object()):
            answer=calibrate(records()+[replace(equal,observed_kw=unseen)],BASE,10,'rolling',MODEL)
            result.append(answer.margin_kw)
            self.assertEqual(answer.exclusions[0]['reasons'],['target_not_strictly_before_decision'])
        self.assertEqual(result,[19.,19.,19.])

    def test_past_target_late_computation_excluded_before_its_value_is_read(self):
        delayed=replace(records(1)[0],origin_time=BASE-timedelta(minutes=20),target_time=BASE-timedelta(minutes=10),
            issued_at=BASE-timedelta(minutes=20),observation_available_at=BASE-timedelta(minutes=10),
            residual_available_at=BASE+timedelta(seconds=1),observed_kw=object())
        answer=calibrate(records()+[delayed],BASE,10,'rolling',MODEL)
        self.assertIn('residual_not_available',answer.exclusions[0]['reasons'])

    def test_all_timestamp_fields_validated_even_for_future_other_model_and_other_horizon(self):
        future=replace(records(1)[0],origin_time=BASE,issued_at=BASE,target_time=BASE+timedelta(minutes=10),
            observation_available_at=BASE+timedelta(minutes=10),residual_available_at=BASE+timedelta(minutes=10),
            prediction_kw=object(),observed_kw=object())
        candidates=(future,replace(records(1,20)[0],prediction_kw=object(),observed_kw=object()),
                    replace(records(1)[0],model_sha256='b'*64,prediction_kw=object(),observed_kw=object()))
        fields=('origin_time','issued_at','target_time','observation_available_at','residual_available_at',
                'model_latest_training_target','model_available_at','grid_anchor')
        for candidate in candidates:
            for field in fields:
                for invalid in (None,'2030-01-01T00:00:00Z',BASE.replace(tzinfo=None)):
                    with self.subTest(horizon=candidate.horizon_minutes,model=candidate.model_sha256,
                                      field=field,invalid=invalid),self.assertRaises(CalibrationError):
                        calibrate(records()+[replace(candidate,**{field:invalid})],BASE,10,'rolling',MODEL)

    def test_excluded_candidates_cannot_hide_invalid_metadata_relations(self):
        future=replace(records(1)[0],origin_time=BASE,issued_at=BASE,target_time=BASE+timedelta(minutes=10),
            observation_available_at=BASE+timedelta(minutes=10),residual_available_at=BASE+timedelta(minutes=10),
            prediction_kw=object(),observed_kw=object())
        for candidate in (future,records(1,20)[0],replace(records(1)[0],model_sha256='b'*64)):
            changes=({'issued_at':candidate.origin_time-timedelta(seconds=1)},
                     {'issued_at':candidate.target_time},
                     {'target_time':candidate.target_time+timedelta(minutes=10)},
                     {'observation_available_at':candidate.target_time-timedelta(seconds=1)},
                     {'residual_available_at':candidate.observation_available_at-timedelta(seconds=1)},
                     {'model_latest_training_target':candidate.origin_time},
                     {'model_available_at':candidate.issued_at+timedelta(seconds=1)},
                     {'model_available_at':candidate.model_latest_training_target-timedelta(seconds=1)},
                     {'grid_anchor':BASE+timedelta(minutes=1)},
                     {'horizon_minutes':True},{'model_sha256':'unknown'})
            for change in changes:
                with self.subTest(change=change),self.assertRaises(CalibrationError):
                    calibrate(records()+[replace(candidate,**change)],BASE,10,'rolling',MODEL)

    def test_well_formed_exclusions_never_inspect_prediction_or_observed_values(self):
        future=replace(records(1)[0],origin_time=BASE,issued_at=BASE,target_time=BASE+timedelta(minutes=10),
            observation_available_at=BASE+timedelta(minutes=10),residual_available_at=BASE+timedelta(minutes=10),
            prediction_kw=object(),observed_kw=object())
        ignored=[future,replace(records(1,20)[0],prediction_kw=object(),observed_kw=object()),
                 replace(records(1)[0],model_sha256='b'*64,prediction_kw=object(),observed_kw=object())]
        for method in ('rolling','weighted'):
            with self.subTest(method=method):
                baseline=calibrate(records(),BASE,10,method,MODEL)
                answer=calibrate(records()+ignored,BASE,10,method,MODEL)
                self.assertEqual(answer.margin_kw,baseline.margin_kw)
                self.assertEqual(answer.other_horizon_records,1)
                self.assertEqual(answer.other_model_records,1)
                self.assertEqual(len(answer.exclusions),1)

    def test_complete_metadata_pass_precedes_any_value_validation(self):
        unavailable=replace(records(1,20)[0],issued_at=None)
        invalid_values=replace(records()[0],prediction_kw=object(),observed_kw=object())
        with self.assertRaisesRegex(CalibrationError,'Invalid calibration metadata'):
            calibrate([invalid_values,unavailable],BASE,10,'rolling',MODEL)

    def test_duplicate_ignored_identities_and_unsupported_ledger_metadata_rejected(self):
        for candidate in (records(1,20)[0],replace(records(1)[0],model_sha256='b'*64)):
            with self.subTest(candidate=candidate),self.assertRaisesRegex(CalibrationError,'Duplicate'):
                calibrate(records()+[candidate,candidate],BASE,10,'rolling',MODEL)
        with self.assertRaisesRegex(CalibrationError,'Residual ledger'):
            calibrate(records()+[{'origin_time':BASE}],BASE,10,'rolling',MODEL)

    def test_horizons_and_model_identities_never_pool_scores(self):
        data=[]
        for h in (10,20,30,40,50,60):
            data += [replace(row,observed_kw=100.+h) for row in records(12,h)]
        data += [replace(row,model_sha256='b'*64,observed_kw=1e7) for row in records()]
        for h in (10,20,30,40,50,60):
            answer=calibrate(data,BASE,h,'static',MODEL)
            self.assertEqual(answer.margin_kw,float(h))
            self.assertEqual(answer.other_horizon_records,60)
            self.assertEqual(answer.other_model_records,20)

    def test_duplicate_identity_and_unknown_timestamp_evidence_fail_closed(self):
        with self.assertRaises(CalibrationError):calibrate(records()+records()[:1],BASE,10,'rolling',MODEL)
        with self.assertRaises(ValueError):calibrate([replace(records()[0],target_time=BASE.replace(tzinfo=None))],BASE,10,'rolling',MODEL)
        with self.assertRaises(ValueError):calibrate(records(),BASE,10,'static','')
        with self.assertRaises(InsufficientCalibration):calibrate(records(),BASE,10,'static','b'*64)

    def test_malformed_chronology_and_mixed_grid_anchors_fail(self):
        data=records()
        data[0]=replace(data[0],residual_available_at=data[0].target_time-timedelta(minutes=1))
        with self.assertRaises(CalibrationError):calibrate(data,BASE,10,'static',MODEL)
        data=records();data[0]=replace(data[0],grid_anchor=BASE+timedelta(minutes=10))
        with self.assertRaises(CalibrationError):calibrate(data,BASE,10,'static',MODEL)

    def test_floor_binding_and_nonnegative_interval_width_are_explicit(self):
        flat=[replace(r,prediction_kw=0.,observed_kw=0.) for r in records()]
        disabled=calibrate(flat,BASE,10,'static',MODEL)
        self.assertFalse(disabled.floor_binding)
        active=calibrate(flat,BASE,10,'static',MODEL,CalibrationConfig(floor_kw=5.))
        self.assertTrue(active.floor_binding)
        self.assertEqual(active.interval(2.),(0.,7.))
        tie=calibrate([replace(r,prediction_kw=0.,observed_kw=5.) for r in records()],BASE,10,'static',MODEL,CalibrationConfig(floor_kw=5.))
        self.assertTrue(tie.floor_binding)
        with self.assertRaises(ValueError):active.interval(-1.)

    def test_weighted_uniform_limit_and_effective_size(self):
        answer=calibrate(records(),BASE,10,'weighted',MODEL,CalibrationConfig(half_life_minutes=1e20))
        self.assertEqual(answer.quantile_kw,19.)
        self.assertAlmostEqual(answer.effective_n,20.)
        decayed=calibrate(records(),BASE,10,'weighted',MODEL,CalibrationConfig(alpha=.2,half_life_minutes=500))
        self.assertLess(decayed.effective_n,20.)
        self.assertLess(decayed.total_calibration_weight,20.)
        self.assertEqual(decayed.as_dict()['coverage_claim'],'descriptive under temporal dependence; no guaranteed coverage asserted')

    def test_weighted_test_point_infinite_mass_case_not_capped_by_floor(self):
        with self.assertRaises(InsufficientCalibration):
            calibrate(records(9),BASE,10,'weighted',MODEL,CalibrationConfig(half_life_minutes=1.,floor_kw=1e9))

    def test_invalid_configuration_and_insufficient_horizon_history(self):
        for change in ({'alpha':0.},{'alpha':1.},{'floor_kw':-1.},{'window':True},
                       {'window':5,'min_samples':9},{'half_life_minutes':0.}):
            with self.subTest(change=change),self.assertRaises(ValueError):CalibrationConfig(**change)
        with self.assertRaises(InsufficientCalibration):calibrate([],BASE,10,'rolling',MODEL)
        with self.assertRaises(CalibrationError):calibrate(records(),BASE,10,'not_a_method',MODEL)


if __name__=='__main__':unittest.main()
