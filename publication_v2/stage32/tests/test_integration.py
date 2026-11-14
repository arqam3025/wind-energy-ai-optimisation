"""Stage 3.2 synthetic forecast -> MPC integration: causality, identity and fail-closed checks."""
from copy import deepcopy
from datetime import timedelta
import unittest

from publication_v2.protocol import HORIZONS
from publication_v2.stage31.controllers import CONTROLLERS
from publication_v2.stage31.evaluation import paired_comparisons, reproducibility_payload
from publication_v2.stage32.adapter import AdapterPolicy, SyntheticRegistry, adapt_forecast, adapt_stage2_points
from publication_v2.stage32.episode import run_comparison, run_episode
from publication_v2.stage32.synthetic import START, STEP, ScenarioSpec, SyntheticStream, forcing

STEPS = 8


def spec(**kwargs):
    base = dict(episode_name='t', profile='rapid', forecast_mode='noisy', forecast_noise_kw=40., steps=STEPS)
    base.update(kwargs)
    return ScenarioSpec(**base)


def first_packet(**kwargs):
    stream = SyntheticStream(spec(**kwargs))
    return stream, stream.packet(0)


class AdapterTests(unittest.TestCase):
    def test_clean_packet_maps_exactly_to_bundle(self):
        stream, packet = first_packet()
        result = adapt_forecast(packet, START, stream.registry)
        self.assertTrue(result.accepted, result.detail)
        bundle = result.bundle
        self.assertEqual(bundle.point_kw, tuple(r['point_kw'] for r in packet['horizons']))
        self.assertEqual(bundle.lower_kw, tuple(r['lower_kw'] for r in packet['horizons']))
        self.assertEqual(bundle.target_times, tuple(START + timedelta(minutes=h) for h in HORIZONS))
        self.assertEqual(bundle.uncertainty_kind, 'CONFORMAL_MARGINAL')
        self.assertTrue(all(t < START for t in bundle.calibration_newest_target_times))
        self.assertIn('not joint trajectory coverage', result.audit['coverage_interpretation'])

    def test_decision_time_mismatch_rejected(self):
        stream, packet = first_packet()
        result = adapt_forecast(packet, START + STEP, stream.registry)
        self.assertEqual(result.rejection_code, 'FORECAST_CLOCK_ALIGNMENT')

    def test_tampered_point_breaks_calibration_replay(self):
        stream, packet = first_packet()
        packet['horizons'][2]['point_kw'] += 25.
        result = adapt_forecast(packet, START, stream.registry)
        self.assertFalse(result.accepted)
        self.assertEqual(result.rejection_code, 'INTERVAL_CALIBRATION_MISMATCH')

    def test_widened_bounds_rejected(self):
        stream, packet = first_packet()
        packet['horizons'][0]['upper_kw'] += 1.
        self.assertEqual(adapt_forecast(packet, START, stream.registry).rejection_code,
                         'INTERVAL_CALIBRATION_MISMATCH')

    def test_registry_from_other_scenario_rejects(self):
        _, packet = first_packet(seed=1)
        other = SyntheticStream(spec(seed=2))
        other.packet(0)
        self.assertFalse(adapt_forecast(packet, START, other.registry).accepted)

    def test_empty_registry_and_wrong_types_fail_closed(self):
        _, packet = first_packet()
        self.assertEqual(adapt_forecast(packet, START, SyntheticRegistry({}, {}, {}, {})).rejection_code,
                         'UNREGISTERED_IDENTITY')
        self.assertEqual(adapt_forecast(packet, START, None).rejection_code, 'REGISTRY_INVALID')
        self.assertFalse(adapt_forecast(None, START, SyntheticRegistry({}, {}, {}, {})).accepted)

    def test_real_data_role_rejected(self):
        stream, packet = first_packet()
        packet['study_role'] = 'CONFIRMATORY'
        self.assertEqual(adapt_forecast(packet, START, stream.registry).rejection_code,
                         'SOURCE_OR_SEMANTICS_REJECTED')

    def test_future_feature_input_rejected(self):
        stream, packet = first_packet()
        packet['feature_inputs'][0]['available_at'] = (START + timedelta(seconds=1)).isoformat()
        self.assertEqual(adapt_forecast(packet, START, stream.registry).rejection_code, 'FEATURE_UNAVAILABLE')

    def test_strict_calibration_age_policy(self):
        stream, packet = first_packet()
        strict = AdapterPolicy(max_calibration_age_minutes=5.)
        self.assertEqual(adapt_forecast(packet, START, stream.registry, policy=strict).rejection_code,
                         'CALIBRATION_STALE')

    def test_perfect_benchmark_can_be_disabled(self):
        stream, packet = first_packet(forecast_mode='announced_perfect', forecast_noise_kw=0.)
        self.assertTrue(adapt_forecast(packet, START, stream.registry).accepted)
        off = AdapterPolicy(allow_preannounced_forcing=False)
        self.assertEqual(adapt_forecast(packet, START, stream.registry, policy=off).rejection_code,
                         'INPUT_ACCESS_REJECTED')

    def test_stage2_point_row_bridge(self):
        import numpy as np
        stream, packet = first_packet()
        points = np.array([r['point_kw'] for r in packet['horizons']])
        metadata = deepcopy(packet)
        for row in metadata['horizons']:
            del row['point_kw']
        result = adapt_stage2_points(points, metadata=metadata, decision_time=START, registry=stream.registry)
        self.assertTrue(result.accepted, result.detail)
        self.assertEqual(adapt_stage2_points(points[:5], metadata=metadata, decision_time=START,
                                             registry=stream.registry).rejection_code, 'POINT_SHAPE')
        bad = deepcopy(packet)  # point_kw present in metadata is an unsupported key
        self.assertEqual(adapt_stage2_points(points, metadata=bad, decision_time=START,
                                             registry=stream.registry).rejection_code, 'METADATA_SCHEMA')


class StreamTests(unittest.TestCase):
    def test_sequential_clock_enforced(self):
        stream = SyntheticStream(spec())
        with self.assertRaises(ValueError):
            stream.packet(1)
        stream.packet(0)
        with self.assertRaises(ValueError):
            stream.observe(1, 1000.)

    def test_calibration_never_uses_unreleased_targets(self):
        stream = SyntheticStream(spec())
        for index in range(STEPS):
            packet = stream.packet(index)
            issue = START + STEP * index
            for row in packet['horizons']:
                for residual in row['calibration']['residuals']:
                    self.assertLess(residual['target_time'], issue.isoformat())
            stream.observe(index, forcing(stream.spec, index))

    def test_invalid_spec_rejected(self):
        with self.assertRaises(ValueError):
            ScenarioSpec('x', forecast_mode='announced_perfect', forecast_noise_kw=5.)
        with self.assertRaises(ValueError):
            ScenarioSpec('x', faults=((1, 'stale_calibration'),))


class EpisodeTests(unittest.TestCase):
    FAULTS = ((1, 'missing'), (2, 'stale'), (3, 'future_generation'), (4, 'future_availability'),
              (5, 'unsupported_model'), (6, 'invalid_bounds'), (7, 'stale_calibration'),
              (8, 'invalid_calibration'), (9, 'invalid_horizon'))
    EXPECTED = {1: 'MISSING_PACKET', 2: 'FORECAST_CLOCK_ALIGNMENT', 3: 'FORECAST_CLOCK_ALIGNMENT',
                4: 'FORECAST_CLOCK_ALIGNMENT', 5: 'UNREGISTERED_IDENTITY', 6: 'INTERVAL_INVALID',
                7: 'CALIBRATION_STALE', 8: 'CALIBRATION_IDENTITY', 9: 'HORIZON_MAPPING'}

    def test_every_fault_rejected_and_falls_back_to_zero_dispatch(self):
        run = run_episode(spec(steps=11, faults=self.FAULTS), 'adaptive')
        for index, code in self.EXPECTED.items():
            row = run['rows'][index]
            self.assertEqual(row['forecast_fault'], code)
            self.assertTrue(row['fallback'])
            self.assertEqual((row['charge_kw'], row['discharge_kw']), (0., 0.))
        self.assertIsNone(run['rows'][0]['forecast_fault'])
        self.assertIsNone(run['rows'][10]['forecast_fault'])
        self.assertEqual(run['metrics']['adapter_rejections'], len(self.EXPECTED))

    def test_counterfactual_future_does_not_change_past_decisions(self):
        """Leakage test: altering outcomes from interval k on cannot alter decisions before k."""
        base_spec = spec()
        k = 4
        altered = lambda i: forcing(base_spec, i) + (900. if i >= k else 0.)
        for controller in ('deterministic', 'adaptive', 'heuristic'):
            a = run_episode(base_spec, controller)
            b = run_episode(base_spec, controller, wind=altered)
            for i in range(k + 1):  # decision k is sealed before outcome k is released
                self.assertEqual(a['rows'][i]['forecast_sha256'], b['rows'][i]['forecast_sha256'])
                self.assertEqual((a['rows'][i]['charge_kw'], a['rows'][i]['discharge_kw']),
                                 (b['rows'][i]['charge_kw'], b['rows'][i]['discharge_kw']), controller)
            self.assertNotEqual(a['rows'][k + 1]['forecast_sha256'], b['rows'][k + 1]['forecast_sha256'])

    def test_comparison_is_paired_physical_and_reproducible(self):
        s = spec(calibration_method='weighted')
        runs = run_comparison(s)
        self.assertEqual([r['controller'] for r in runs], list(CONTROLLERS))
        self.assertTrue(paired_comparisons(runs))
        for run in runs:
            m = run['metrics']
            self.assertEqual(m['intervals'], STEPS)
            self.assertEqual(m['soc_constraint_violations'] + m['power_constraint_violations']
                             + m['simultaneous_charge_discharge_events'], 0)
            self.assertEqual(m['optimisation_failures'], 0)
        self.assertEqual(runs[0]['metrics']['total_throughput_kwh'], 0.)
        again = run_episode(s, 'adaptive')
        self.assertEqual(reproducibility_payload(again), reproducibility_payload(runs[3]))

    def test_forecast_diagnostics(self):
        perfect = run_episode(spec(forecast_mode='announced_perfect', forecast_noise_kw=0.), 'uncontrolled')
        d = perfect['forecast_diagnostics']
        self.assertAlmostEqual(d['nominal_marginal_coverage'], .9)
        for h in HORIZONS:
            entry = d['per_horizon'][str(h)]
            self.assertEqual(entry['n'], STEPS)
            self.assertAlmostEqual(entry['mae_kw'], 0.)
            self.assertEqual(entry['empirical_coverage'], 1.)
        self.assertEqual(d['joint_six_horizon_coverage'], 1.)
        noisy = run_episode(spec(), 'uncontrolled')['forecast_diagnostics']
        self.assertGreater(noisy['per_horizon']['60']['mae_kw'], 0.)

    def test_static_calibration_frozen_before_first_decision(self):
        run = run_episode(spec(calibration_method='static'), 'adaptive')
        self.assertEqual(run['metrics']['adapter_rejections'], 0)


if __name__ == '__main__':
    unittest.main()
