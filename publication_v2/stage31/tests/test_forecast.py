"""Synthetic forecast packet chronology/interval contracts; no model fitting."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import math
import unittest

from publication_v2.stage31.forecast import ForecastBundle, ForecastError

BASE = datetime(2035, 1, 1, tzinfo=timezone.utc)


def bundle(kind='SYNTHETIC_INTERVALS'):
    point = (500.,) * 6
    lower, upper = ((500.,) * 6, (500.,) * 6) if kind == 'POINT_ONLY' else ((400.,) * 6, (600.,) * 6)
    cal = dict(calibration_newest_target_times=(BASE - timedelta(minutes=20),) * 6,
               calibration_available_ats=(BASE - timedelta(minutes=10),) * 6) if kind == 'CONFORMAL_MARGINAL' else {}
    return ForecastBundle(BASE, point, lower, upper, .1, 'synthetic_fixture_v1', BASE,
                          tuple(BASE + timedelta(minutes=10 * (i + 1)) for i in range(6)),
                          BASE - timedelta(days=1), uncertainty_kind=kind, **cal)


class ForecastTests(unittest.TestCase):
    def test_default_synthetic_bundle_is_immutable_and_valid(self):
        f = bundle()
        self.assertIsNone(f.validate(BASE))
        self.assertEqual(f.target_times[0], BASE + timedelta(minutes=10))
        self.assertEqual(f.target_times[-1], BASE + timedelta(minutes=60))
        with self.assertRaises(FrozenInstanceError):
            f.alpha = .2

    def test_point_only_and_complete_marginal_conformal_are_valid(self):
        bundle('POINT_ONLY').validate(BASE)
        bundle('CONFORMAL_MARGINAL').validate(BASE)
        with self.assertRaises(ForecastError):
            replace(bundle(), uncertainty_kind='POINT_ONLY').validate(BASE)

    def test_every_sequence_requires_immutable_tuple_and_exact_horizon(self):
        f = bundle()
        for name in ('point_kw', 'lower_kw', 'upper_kw', 'target_times',
                     'calibration_newest_target_times', 'calibration_available_ats'):
            values = getattr(f, name)
            for invalid in (list(values), values[:-1], values + values[:1], None):
                with self.subTest(field=name), self.assertRaises(ForecastError):
                    replace(f, **{name: invalid}).validate(BASE)

    def test_nonfinite_negative_and_inverted_power_bounds(self):
        f = bundle()
        for name, value in (('point_kw', math.nan), ('upper_kw', math.inf), ('lower_kw', -1),
                            ('point_kw', -1), ('lower_kw', 501), ('upper_kw', 499),
                            ('point_kw', True), ('upper_kw', 10**1000), ('point_kw', '500')):
            with self.subTest(field=name, value=repr(value)[:20]), self.assertRaises(ForecastError):
                replace(f, **{name: (value,) * 6}).validate(BASE)

    def test_alpha_and_provenance_required_and_supported(self):
        f = bundle()
        for alpha in (0, 1, -.1, True, math.nan, math.inf, '0.1', None, 10**1000):
            with self.subTest(alpha=repr(alpha)[:20]), self.assertRaises(ForecastError):
                replace(f, alpha=alpha).validate(BASE)
        for provenance in ('', ' ', ' synthetic ', None, True):
            with self.subTest(provenance=provenance), self.assertRaises(ForecastError):
                replace(f, provenance=provenance).validate(BASE)
        with self.assertRaises(ForecastError):
            replace(f, uncertainty_kind='UNKNOWN').validate(BASE)
        with self.assertRaises(TypeError):
            ForecastBundle(**{**f.__dict__, 'unsupported_metadata': 1})

    def test_issue_availability_and_model_times_are_causal(self):
        f = bundle()
        for changes in (dict(issue_time=BASE + timedelta(seconds=1)),
                        dict(available_at=BASE + timedelta(seconds=1)),
                        dict(available_at=BASE - timedelta(seconds=1)),
                        dict(model_available_at=BASE + timedelta(seconds=1))):
            with self.subTest(changes=changes), self.assertRaises(ForecastError):
                replace(f, **changes).validate(BASE)
        replace(f, issue_time=BASE - timedelta(minutes=2), available_at=BASE - timedelta(minutes=1)).validate(BASE)

    def test_naive_mixed_and_unsupported_timestamps_fail(self):
        f = bundle()
        naive = BASE.replace(tzinfo=None)
        for name in ('issue_time', 'available_at', 'model_available_at'):
            for invalid in (naive, None, '2035-01-01', True):
                with self.subTest(field=name), self.assertRaises(ForecastError):
                    replace(f, **{name: invalid}).validate(BASE)
        for invalid in (naive, None, '2035-01-01', True):
            with self.assertRaises(ForecastError):
                f.validate(invalid)
        with self.assertRaises(ForecastError):
            replace(f, target_times=(naive,) + f.target_times[1:]).validate(BASE)

    def test_explicit_different_offsets_are_compared_as_utc_instants(self):
        f = bundle('CONFORMAL_MARGINAL')
        offset = timezone(timedelta(hours=5, minutes=45))
        replace(f, issue_time=f.issue_time.astimezone(offset),
                target_times=tuple(t.astimezone(offset) for t in f.target_times),
                calibration_newest_target_times=tuple(t.astimezone(offset) for t in f.calibration_newest_target_times)).validate(BASE)

    def test_target_alignment_duplicates_and_future_horizon(self):
        f = bundle()
        for times in ((BASE,) * 6, f.target_times[::-1],
                      (BASE + timedelta(minutes=11),) + f.target_times[1:],
                      (f.target_times[1],) + f.target_times[1:]):
            with self.subTest(times=times), self.assertRaises(ForecastError):
                replace(f, target_times=times).validate(BASE)

    def test_invalid_horizon_step_and_time_overflow(self):
        f = bundle()
        for changes in (dict(horizon=0), dict(horizon=True), dict(horizon=6.0),
                        dict(step_minutes=0), dict(step_minutes=True),
                        dict(step_minutes=1.5), dict(step_minutes=10**1000)):
            with self.subTest(changes=changes), self.assertRaises(ForecastError):
                f.validate(BASE, **changes)
        far = datetime.max.replace(tzinfo=timezone.utc)
        with self.assertRaises(ForecastError):
            replace(f, issue_time=far, available_at=far, model_available_at=far).validate(far)

    def test_complete_calibration_metadata_required_for_conformal_claim(self):
        f = bundle()
        with self.assertRaises(ForecastError):
            replace(f, uncertainty_kind='CONFORMAL_MARGINAL').validate(BASE)
        f = bundle('CONFORMAL_MARGINAL')
        with self.assertRaises(ForecastError):
            replace(f, calibration_newest_target_times=(None,) * 6).validate(BASE)
        with self.assertRaises(ForecastError):
            replace(f, calibration_available_ats=(None,) * 6).validate(BASE)

    def test_equal_or_future_calibration_target_is_rejected(self):
        f = bundle('CONFORMAL_MARGINAL')
        for target in (BASE, BASE + timedelta(minutes=10)):
            with self.subTest(target=target), self.assertRaises(ForecastError):
                replace(f, calibration_newest_target_times=(target,) * 6,
                        calibration_available_ats=(target,) * 6).validate(BASE)

    def test_late_or_pre_input_calibration_availability_is_rejected(self):
        f = bundle('CONFORMAL_MARGINAL')
        for ready in (BASE + timedelta(seconds=1), BASE - timedelta(minutes=30)):
            with self.subTest(ready=ready), self.assertRaises(ForecastError):
                replace(f, calibration_available_ats=(ready,) * 6).validate(BASE)

    def test_calibration_target_between_issue_and_decision_rejected(self):
        f = bundle('CONFORMAL_MARGINAL')
        with self.assertRaises(ForecastError):
            replace(f, issue_time=BASE - timedelta(minutes=20),
                    available_at=BASE - timedelta(minutes=10),
                    calibration_newest_target_times=(BASE - timedelta(minutes=15),) * 6,
                    calibration_available_ats=(BASE - timedelta(minutes=14),) * 6).validate(BASE)

    def test_calibration_availability_between_issue_and_decision_rejected(self):
        f = bundle('CONFORMAL_MARGINAL')
        with self.assertRaises(ForecastError):
            replace(f, issue_time=BASE - timedelta(minutes=20),
                    available_at=BASE - timedelta(minutes=10),
                    calibration_newest_target_times=(BASE - timedelta(minutes=30),) * 6,
                    calibration_available_ats=(BASE - timedelta(minutes=15),) * 6).validate(BASE)

    def test_calibration_target_equal_to_old_issue_rejected(self):
        f = bundle('CONFORMAL_MARGINAL')
        issue = BASE - timedelta(minutes=20)
        with self.assertRaises(ForecastError):
            replace(f, issue_time=issue, calibration_newest_target_times=(issue,) * 6,
                    calibration_available_ats=(issue,) * 6).validate(BASE)

    def test_optional_metadata_is_validated_for_every_kind(self):
        for kind in ('SYNTHETIC_INTERVALS', 'POINT_ONLY'):
            f = bundle(kind)
            for changes in (dict(calibration_newest_target_times=(BASE,) * 6,
                                 calibration_available_ats=(BASE,) * 6),
                            dict(calibration_newest_target_times=('unsupported',) * 6,
                                 calibration_available_ats=(BASE - timedelta(minutes=1),) * 6),
                            dict(calibration_newest_target_times=(BASE - timedelta(minutes=10),) * 6)):
                with self.subTest(kind=kind, changes=changes), self.assertRaises(ForecastError):
                    replace(f, **changes).validate(BASE)


if __name__ == '__main__':
    unittest.main()
