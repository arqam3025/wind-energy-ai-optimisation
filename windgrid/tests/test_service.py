"""Service core: equivalence with the research closed loop, causality and fail-closed input handling."""

import unittest

import numpy as np

from publication_v2.stage4.closed_loop import Series, run_episode
from publication_v2.stage5.experiment import REGISTRY
from publication_v2.stage31.battery import BatteryConfig
from windgrid import service, simulate

METRICS = ('total_ramp_exceedance_kw', 'total_throughput_kwh', 'ramp_violations', 'minimum_soc', 'maximum_soc')


def window(series, end, rows=250):
    lo = max(0, end + 1 - rows)
    return Series(
        series.times[lo : end + 1],
        series.realised[lo : end + 1].copy(),
        series.predictions[lo : end + 1].copy(),
        series.name,
    )


class Equivalence(unittest.TestCase):
    """A replay through the service must equal the research ``run_episode`` exactly."""

    def test_replay_reproduces_research_closed_loop(self):
        series = simulate.load_sample()['lightgbm_spatial']
        k0 = simulate.sample_episode_starts('lightgbm_spatial')[3]
        for controller in ('graded_mpc', 'stochastic_skill', 'adaptive', 'lowpass_fast', 'uncontrolled'):
            with self.subTest(controller=controller):
                ours = simulate.replay(series, k0, controller)['metrics']
                extra = (
                    {'decider': REGISTRY[controller][0], 'decider_config': REGISTRY[controller][1]}
                    if controller in REGISTRY
                    else {}
                )
                research = run_episode(series, k0, controller, **extra)['metrics']
                for metric in METRICS:
                    self.assertAlmostEqual(ours[metric], research[metric], places=9, msg=metric)

    def test_sample_has_eligible_episodes_for_both_forecasts(self):
        for forecast in simulate.SAMPLE_FORECASTS:
            self.assertGreaterEqual(len(simulate.sample_episode_starts(forecast)), 30)


class Behaviour(unittest.TestCase):
    def setUp(self):
        self.series = simulate.load_sample()['lightgbm_spatial']
        self.end = simulate.sample_episode_starts('lightgbm_spatial')[5] + 7

    def test_decision_is_causal(self):
        """The interval that just ended must not change the decision (only earlier targets calibrate)."""
        base = window(self.series, self.end)
        changed = window(self.series, self.end)
        changed.realised[-1] += 750.0
        a = service.dispatch(base, 1300.0, 1000.0, 'graded_mpc')
        b = service.dispatch(changed, 1300.0, 1000.0, 'graded_mpc')
        self.assertEqual(
            (a['charge_kw'], a['discharge_kw'], a['skill_score']), (b['charge_kw'], b['discharge_kw'], b['skill_score'])
        )

    def test_longer_history_gives_identical_decision(self):
        short, long = window(self.series, self.end, 250), window(self.series, self.end, 900)
        self.assertEqual(
            service.dispatch(short, 1300.0, 1000.0)['charge_kw'], service.dispatch(long, 1300.0, 1000.0)['charge_kw']
        )

    def test_missing_forecast_fails_closed(self):
        series = window(self.series, self.end)
        series.predictions[-1] = np.nan
        result = service.dispatch(series, 1300.0, 1000.0, 'graded_mpc')
        self.assertFalse(result['forecast_available'])
        self.assertEqual((result['charge_kw'], result['discharge_kw']), (0.0, 0.0))

    def test_plan_respects_battery_limits(self):
        battery = BatteryConfig()
        for controller in ('graded_mpc', 'adaptive', 'lowpass_fast'):
            plan = service.dispatch(window(self.series, self.end), 1300.0, 1000.0, controller)['plan']
            for energy in plan['energy_kwh']:
                self.assertGreaterEqual(energy, battery.capacity_kwh * battery.min_soc - 1e-6)
                self.assertLessEqual(energy, battery.capacity_kwh * battery.max_soc + 1e-6)

    def test_graded_weight_is_reported_and_bounded(self):
        result = service.dispatch(window(self.series, self.end), 1300.0, 1000.0, 'graded_mpc')
        self.assertTrue(0.0 <= result['skill_weight'] <= 1.0)
        self.assertIsNone(service.dispatch(window(self.series, self.end), 1300.0, 1000.0, 'adaptive')['skill_weight'])


class InputValidation(unittest.TestCase):
    def setUp(self):
        series = simulate.load_sample()['lightgbm_spatial']
        self.times = [t.isoformat() for t in series.times[:100]]
        self.realised = list(series.realised[:100])
        self.forecasts = [list(row) for row in series.predictions[:100]]

    def test_valid_history_is_accepted(self):
        self.assertEqual(len(service.make_series(self.times, self.realised, self.forecasts).times), 100)

    def test_gap_is_rejected(self):
        with self.assertRaises(service.HistoryError):
            service.make_series(self.times[:50] + self.times[51:], self.realised[:99], self.forecasts[:99])

    def test_naive_timestamps_are_rejected(self):
        with self.assertRaises(service.HistoryError):
            service.make_series([t[:19] for t in self.times], self.realised, self.forecasts)

    def test_too_short_history_is_rejected(self):
        with self.assertRaises(service.HistoryError):
            service.make_series(self.times[:10], self.realised[:10], self.forecasts[:10])

    def test_wrong_horizon_count_is_rejected(self):
        forecasts = [row[:5] for row in self.forecasts]
        with self.assertRaises(service.HistoryError):
            service.make_series(self.times, self.realised, forecasts)

    def test_energy_outside_soc_window_and_unknown_controller(self):
        series = service.make_series(self.times, self.realised, self.forecasts)
        with self.assertRaises(ValueError):
            service.dispatch(series, 100.0, 0.0)
        with self.assertRaises(KeyError):
            service.dispatch(series, 1300.0, 0.0, 'not_a_controller')


if __name__ == '__main__':
    unittest.main()
