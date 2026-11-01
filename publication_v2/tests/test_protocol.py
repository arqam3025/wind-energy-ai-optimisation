"""Synthetic time-ledger fixtures only; no synthetic efficacy results."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
import unittest

from publication_v2.protocol import (FEATURE_SUPPORT, ChronologyError, Feature, Forecast, Residual,
    embargo_projection, validate_calibration, validate_features, validate_forecast,
    validate_grid, validate_residual, validate_splits)

BASE = datetime(2030,1,1,tzinfo=timezone.utc)


def features(origin=BASE):
    result = []
    for name, offsets in FEATURE_SUPPORT.items():
        support = tuple(origin-timedelta(minutes=m) for m in offsets)
        result.append(Feature(name, 1., support, origin, support))
    return tuple(result)


def forecast():
    return Forecast(BASE, BASE, BASE, BASE+timedelta(minutes=10), 10, 1., features(),
        'a'*64, BASE-timedelta(days=1), BASE-timedelta(hours=1), BASE)


def residual(h=10):
    origin = BASE-timedelta(hours=2)
    target = origin+timedelta(minutes=h)
    return Residual(origin, origin, target, h, 1., 2., target, target, 'a'*64,
                    BASE-timedelta(days=2), BASE-timedelta(days=1), BASE)


class ForecastInformationTests(unittest.TestCase):
    def test_complete_causal_forecast_and_computation_delay(self):
        validate_forecast(forecast())
        validate_forecast(replace(forecast(), issued_at=BASE+timedelta(seconds=1), decision_time=BASE+timedelta(seconds=2)))

    def test_each_feature_missing_or_future_support_rejected(self):
        good = features()
        for i, feature in enumerate(good):
            with self.subTest(feature=feature.name):
                altered = list(good)
                altered[i] = replace(feature, source_times=(BASE+timedelta(minutes=10),))
                with self.assertRaises(ChronologyError): validate_features(altered, BASE, BASE)
                with self.assertRaises(ChronologyError): validate_features(good[:i]+good[i+1:], BASE, BASE)

    def test_duplicate_feature_and_source_support_rejected(self):
        with self.assertRaises(ChronologyError): validate_features(features()[:-1]+(features()[0],), BASE, BASE)
        altered = list(features())
        altered[0] = replace(altered[0], source_times=(BASE, BASE))
        with self.assertRaises(ChronologyError): validate_features(altered, BASE, BASE)

    def test_late_feature_rejected_even_before_delayed_issuance(self):
        altered = list(features())
        altered[0] = replace(altered[0], available_at=BASE+timedelta(seconds=1))
        with self.assertRaises(ChronologyError):
            validate_forecast(replace(forecast(), features=tuple(altered), issued_at=BASE+timedelta(seconds=2),
                                      decision_time=BASE+timedelta(seconds=3)))

    def test_source_receipt_after_feature_or_before_event_rejected(self):
        for offset in (-1, 1):
            altered = list(features())
            altered[0] = replace(altered[0], source_available_ats=(BASE+timedelta(seconds=offset),))
            with self.assertRaises(ChronologyError): validate_features(altered, BASE, BASE)
        altered[0] = replace(altered[0], source_available_ats=())
        with self.assertRaises(ChronologyError): validate_features(altered, BASE, BASE)

    def test_wrong_horizon_target_and_nonprospective_decision(self):
        for changes in ({'horizon_minutes':10.0}, {'horizon_minutes':True}, {'horizon_minutes':70},
                        {'target_time':BASE+timedelta(minutes=20)}, {'decision_time':BASE+timedelta(minutes=10)},
                        {'issued_at':BASE-timedelta(seconds=1)}):
            with self.subTest(changes=changes), self.assertRaises(ChronologyError): validate_forecast(replace(forecast(), **changes))

    def test_unattested_model_or_future_fitting_information_rejected(self):
        for changes in ({'model_sha256':''}, {'model_latest_training_target':BASE},
                        {'model_available_at':BASE+timedelta(seconds=1)},
                        {'model_available_at':BASE-timedelta(days=2)}):
            with self.subTest(changes=changes), self.assertRaises(ChronologyError): validate_forecast(replace(forecast(), **changes))

    def test_missing_nonfinite_and_naive_timestamps(self):
        for changes in ({'prediction_kw':None}, {'prediction_kw':math.inf}, {'origin_time':BASE.replace(tzinfo=None)}):
            with self.subTest(changes=changes), self.assertRaises(ChronologyError): validate_forecast(replace(forecast(), **changes))

    def test_explicit_grid_anchor_supports_nonhour_timezone_offset(self):
        anchor = BASE.astimezone(timezone(timedelta(hours=5,minutes=45))).replace(hour=0,minute=0)
        validate_grid([anchor,anchor+timedelta(minutes=10)], anchor=anchor)
        with self.assertRaises(ChronologyError): validate_grid([anchor,anchor+timedelta(minutes=10)])
        with self.assertRaises(ChronologyError): validate_forecast(replace(forecast(), origin_time=BASE+timedelta(minutes=1),
                    target_time=BASE+timedelta(minutes=11), issued_at=BASE+timedelta(minutes=1), decision_time=BASE+timedelta(minutes=1)))


class CalibrationBoundaryTests(unittest.TestCase):
    def test_past_target_with_available_inputs_passes_for_every_horizon(self):
        for h in (10,20,30,40,50,60):
            with self.subTest(h=h): validate_residual(residual(h), BASE)

    def test_equal_and_future_target_rejected_at_all_horizons(self):
        for h in (10,20,30,40,50,60):
            for delta in (0,-1):
                record = residual(h)
                with self.subTest(h=h,delta=delta), self.assertRaises(ChronologyError):
                    validate_residual(record, record.target_time+timedelta(minutes=delta))

    def test_late_observation_or_computation_rejected(self):
        for change in ({'observation_available_at':BASE+timedelta(seconds=1)},
                       {'residual_available_at':BASE+timedelta(seconds=1)},
                       {'residual_available_at':residual().target_time-timedelta(seconds=1)},
                       {'issued_at':residual().target_time}):
            with self.subTest(change=change), self.assertRaises(ChronologyError): validate_residual(replace(residual(), **change), BASE)

    def test_empty_duplicate_and_inconsistent_anchor_calibration_rejected(self):
        for records in ([], [residual(),residual()], [residual(),replace(residual(20),grid_anchor=BASE+timedelta(minutes=1))]):
            with self.assertRaises(ChronologyError): validate_calibration(records, BASE)
        validate_calibration([residual(),residual(20)], BASE)

    def test_embargo_is_horizon_specific_and_equality_is_excluded(self):
        origins = [BASE-timedelta(minutes=m) for m in (70,60,50,40,30,20,10)]
        result = embargo_projection(origins, BASE, (10,60))
        self.assertEqual(len(result[10]['retained_origins']),6)
        self.assertEqual(len(result[60]['retained_origins']),1)
        self.assertIn(BASE-timedelta(minutes=10),result[10]['embargoed_origins'])
        self.assertIn(BASE-timedelta(minutes=60),result[60]['embargoed_origins'])
        self.assertEqual(len(origins),7)

    def test_missing_grid_row_duplicate_and_unsorted_rejected(self):
        for times in ([BASE,BASE+timedelta(minutes=20)],[BASE,BASE], [BASE+timedelta(minutes=10),BASE], []):
            with self.assertRaises(ChronologyError): validate_grid(times)
        validate_grid([BASE,BASE+timedelta(minutes=20)],allow_gaps=True)
        with self.assertRaises(ChronologyError): validate_grid([BASE,BASE+timedelta(minutes=15)],allow_gaps=True)

    def test_cross_horizon_target_overlap_rejected(self):
        # Different origins/horizons produce the SAME target timestamp.
        with self.assertRaisesRegex(ChronologyError,'overlap'):
            validate_splits({'train':[BASE], 'test':[BASE+timedelta(minutes=50)]}, order=('train','test'),
                            horizons_by_role={'train':(60,), 'test':(10,)})

    def test_equal_boundary_target_rejected_without_shared_scored_target(self):
        with self.assertRaisesRegex(ChronologyError,'embargo'):
            validate_splits({'train':[BASE], 'test':[BASE+timedelta(minutes=60)]},order=('train','test'))
        validate_splits({'train':[BASE], 'test':[BASE+timedelta(minutes=70)]},order=('train','test'))

    def test_all_declared_splits_required_and_overlap_not_repaired(self):
        with self.assertRaises(ChronologyError): validate_splits({'train':[BASE]})
        with self.assertRaises(ChronologyError):
            validate_splits({'train':[BASE],'test':[BASE]},order=('train','test'))


if __name__ == '__main__': unittest.main()
