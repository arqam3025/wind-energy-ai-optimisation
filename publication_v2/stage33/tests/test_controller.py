"""Stage 3.3 stochastic MPC: formulation, certification, gate and closed-loop invariants."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import unittest

import numpy as np

from publication_v2.stage31.battery import BatteryConfig, transition
from publication_v2.stage31.forecast import ForecastBundle
from publication_v2.stage32.adapter import adapt_forecast, released_skill
from publication_v2.stage32.episode import run_episode
from publication_v2.stage32.synthetic import ScenarioSpec, SyntheticStream, forcing
from publication_v2.stage33.controller import (SCENARIO_SETS, StochasticMPCConfig, decide_stochastic,
                                               plan_cost, ramp_scenarios, scenario_wind)

T0 = datetime(2032, 1, 1, tzinfo=timezone.utc)
BATTERY = BatteryConfig()
ENERGY = BATTERY.initial_energy_kwh


def bundle(point, half=50., alpha=.1):
    point = tuple(float(p) for p in point)
    return ForecastBundle(T0, point, tuple(max(0., p - half) for p in point), tuple(p + half for p in point),
                          alpha, 'unit-test synthetic bundle', T0,
                          tuple(T0 + timedelta(minutes=10 * (i + 1)) for i in range(6)), T0 - timedelta(hours=1))


def decide(forecast, previous=1000., energy=ENERGY, **config):
    return decide_stochastic('stochastic', forecast, T0, energy, previous, BATTERY, StochasticMPCConfig(**config))


class ConfigAndScenarioTests(unittest.TestCase):
    def test_invalid_configs_rejected(self):
        for bad in (dict(scenarios='x'), dict(soc_mode='x'), dict(ramp_limit_kw=0.), dict(gate_kw=-1.),
                    dict(band_low_soc=.8, band_high_soc=.5), dict(horizon_steps=5), dict(throughput_weight=float('nan'))):
            with self.assertRaises(ValueError):
                StochasticMPCConfig(**bad)

    def test_scenarios_are_ordered_inside_interval_and_centred(self):
        b = bundle([1000, 1100, 1200, 1300, 1400, 1500], half=100.)
        wind, p = scenario_wind(b, StochasticMPCConfig())
        self.assertEqual(wind.shape, (5, 6))
        self.assertAlmostEqual(p.sum(), 1.)
        np.testing.assert_allclose(wind[2], b.point_kw)
        self.assertTrue(np.all(np.diff(wind, axis=0) > 0))
        self.assertTrue(np.all(wind[0] >= np.asarray(b.lower_kw)) and np.all(wind[-1] <= np.asarray(b.upper_kw)))
        point, _ = scenario_wind(b, StochasticMPCConfig(scenarios='point'))
        np.testing.assert_allclose(point[0], b.point_kw)
        for nodes, probabilities in SCENARIO_SETS.values():
            self.assertAlmostEqual(sum(probabilities), 1.)
            self.assertAlmostEqual(sum(n * q for n, q in zip(nodes, probabilities)), 0.)


class RampScenarioTests(unittest.TestCase):
    def test_comonotone_ramps_match_level_scenarios(self):
        b = bundle([1100, 1300, 1200, 1500, 1400, 1600], half=120.)
        ramps, _ = ramp_scenarios(b, 1000., StochasticMPCConfig())
        wind, _ = scenario_wind(b, StochasticMPCConfig())
        np.testing.assert_allclose(ramps, np.diff(np.c_[np.full(5, 1000.), wind], axis=1))

    def test_independent_increment_spreads(self):
        point = [1000.] * 6
        sigmas = np.array([50., 70., 85., 100., 110., 120.])
        edge = 1.6448536269514722
        b = ForecastBundle(T0, tuple(point), tuple(p - s * edge for p, s in zip(point, sigmas)),
                           tuple(p + s * edge for p, s in zip(point, sigmas)), .1, 'unit', T0,
                           tuple(T0 + timedelta(minutes=10 * (i + 1)) for i in range(6)), T0 - timedelta(hours=1))
        ramps, p = ramp_scenarios(b, 1000., StochasticMPCConfig(dependence='independent_increments'))
        spread = ramps[-1] / 1.2815515655446004  # top node, zero centre
        np.testing.assert_allclose(spread, np.sqrt(np.diff(np.r_[0., sigmas ** 2])), rtol=1e-9)
        np.testing.assert_allclose(p @ ramps, 0., atol=1e-9)
        comonotone, _ = ramp_scenarios(b, 1000., StochasticMPCConfig())
        self.assertTrue(np.all(np.abs(ramps[-1, 1:]) > np.abs(comonotone[-1, 1:])))
        with self.assertRaises(ValueError):
            StochasticMPCConfig(dependence='x')

    def test_independent_increments_decision_is_certified(self):
        d = decide(bundle([1000, 1500, 900, 1400, 1000, 1300], half=80.), gate_kw=0.,
                   dependence='independent_increments')
        self.assertEqual(d.status, 'optimal')
        self.assertEqual(d.plan['config']['dependence'], 'independent_increments')


class SkillGateTests(unittest.TestCase):
    def with_skill(self, score):
        b = bundle([1600] * 6, half=20.)
        return replace(b, provenance=json.dumps({'released_skill': {'pooled_skill_score': score}}))

    def test_released_skill_from_ledger(self):
        o = [T0 - timedelta(minutes=10 * k) for k in range(4, 0, -1)]
        def rec(origin, minutes, prediction, observed):
            return {'origin_time': origin.isoformat(), 'target_time': (origin + timedelta(minutes=minutes)).isoformat(),
                    'prediction_kw': prediction, 'observed_kw': observed}
        h10 = [rec(o[0] - timedelta(minutes=10), 10, 0., 100.), rec(o[0], 10, 110., 120.), rec(o[1], 10, 120., 140.)]
        ledgers = [h10] + [[] for _ in range(5)]
        result = released_skill(ledgers, T0)
        # origins o[0] (anchor 100) and o[1] (anchor 120); first record's origin has no anchor
        self.assertEqual(result['pairs'], 2)
        self.assertAlmostEqual(result['pooled_skill_score'], 1 - (10 ** 2 + 20 ** 2) / (20 ** 2 + 20 ** 2))
        future = [rec(T0, 10, 0., 1.)]  # target after decision is ignored
        self.assertEqual(released_skill([h10 + future] + [[] for _ in range(5)], T0)['pairs'], 2)

    def test_adapter_reports_skill(self):
        stream = SyntheticStream(ScenarioSpec('k', profile='stochastic', forecast_mode='persistence', seed=1000))
        audit = adapt_forecast(stream.packet(0), T0, stream.registry).audit
        self.assertEqual(audit['released_skill']['pooled_skill_score'], 0.)
        self.assertGreater(audit['released_skill']['pairs'], 300)

    def test_gate_closed_without_or_below_skill(self):
        for score in (None, -.5, .1):
            d = decide(self.with_skill(score), skill_gate=.1)
            self.assertEqual(d.status, 'skill_gated')
            self.assertEqual((d.charge_kw, d.discharge_kw), (0., 0.))
            self.assertFalse(d.fallback)
        self.assertEqual(decide(bundle([1600] * 6, half=20.), skill_gate=.1).status, 'skill_gated')

    def test_gate_open_above_skill_and_disabled_by_default(self):
        self.assertEqual(decide(self.with_skill(.5), skill_gate=.1).status, 'optimal')
        self.assertEqual(decide(self.with_skill(None)).status, 'optimal')
        for bad in (1., -2., True, float('nan')):
            with self.assertRaises(ValueError):
                StochasticMPCConfig(skill_gate=bad)

    def test_closed_loop_skill_gate_blocks_biased_forecaster(self):
        spec = ScenarioSpec('k', profile='stochastic', forecast_mode='damped_trend', seed=1000, steps=8)
        run = run_episode(spec, 'stochastic', decider=decide_stochastic,
                          decider_config=StochasticMPCConfig(skill_gate=.1))
        self.assertEqual(run['metrics']['total_throughput_kwh'], 0.)
        self.assertTrue(all(r['status'] == 'skill_gated' for r in run['rows']))


class DecisionTests(unittest.TestCase):
    def test_missing_and_invalid_forecasts_fall_back_to_zero(self):
        d = decide(None)
        self.assertTrue(d.fallback)
        self.assertEqual((d.charge_kw, d.discharge_kw), (0., 0.))
        late = replace(bundle([1000] * 6), issue_time=T0 + timedelta(minutes=1))
        self.assertTrue(decide(late).fallback)

    def test_flat_forecast_is_gated_to_zero(self):
        d = decide(bundle([1000] * 6))
        self.assertEqual(d.status, 'gated')
        self.assertEqual((d.charge_kw, d.discharge_kw), (0., 0.))
        self.assertTrue(d.plan['gated'])

    def test_predicted_up_ramp_is_absorbed_by_charging(self):
        d = decide(bundle([1600] * 6, half=20.))
        self.assertEqual(d.status, 'optimal')
        self.assertGreater(d.charge_kw, 300.)
        opt = d.plan['optimised']
        self.assertLess(opt['objective_components']['expected_ramp_exceedance'],
                        d.plan['zero_dispatch']['objective_components']['expected_ramp_exceedance'])

    def test_objective_is_independently_recomputed_and_physical(self):
        d = decide(bundle([1000, 1500, 900, 1400, 1000, 1300], half=80.), gate_kw=0.)
        opt = d.plan['optimised']
        energies = [ENERGY]
        for c, x in zip(opt['charge_kw'], opt['discharge_kw']):
            self.assertFalse(c > 1e-6 and x > 1e-6)
            energies.append(transition(BATTERY, energies[-1], c, x))
        np.testing.assert_allclose(energies, opt['energy_kwh'], atol=1e-6)
        ramps = np.asarray(d.plan['scenario_ramp_kw'])
        cost = plan_cost(opt['charge_kw'], opt['discharge_kw'], opt['energy_kwh'], ramps,
                         np.asarray(d.plan['scenario_probabilities']), BATTERY, StochasticMPCConfig(gate_kw=0.))[0]
        # independent check through explicit grid trajectories (comonotone scenarios)
        wind, p = scenario_wind(bundle([1000, 1500, 900, 1400, 1000, 1300], half=80.), StochasticMPCConfig())
        net = np.asarray(opt['discharge_kw']) - np.asarray(opt['charge_kw'])
        grid_ramps = np.diff(np.c_[np.full(5, 1000.), wind + net], axis=1)
        expected = float(p @ np.maximum(0., np.abs(grid_ramps) - 200.).sum(axis=1)) / (6 * 200.)
        self.assertAlmostEqual(expected, opt['objective_components']['expected_ramp_exceedance'], places=9)
        self.assertAlmostEqual(cost, opt['objective'], places=6)
        self.assertLessEqual(d.plan['solver_maximum_constraint_violation'], 1e-5)

    def test_applied_plan_never_costs_more_than_zero_dispatch(self):
        for point in ([1000] * 6, [1300] * 6, [1000, 1400, 800, 1500, 900, 1200]):
            d = decide(bundle(point, half=150.))
            self.assertLessEqual(d.plan['optimised']['objective'], d.plan['zero_dispatch']['objective'] + 1e-9)

    def test_vanishing_interval_converges_to_point_decision(self):
        # NB: wider intervals do NOT generally reduce dispatch under an expected-
        # exceedance objective (the optimum tracks the scenario distribution).
        point = [1350, 1500, 1200, 1450, 1100, 1300]
        reference = decide(bundle(point, half=0.), gate_kw=0., scenarios='point')
        tiny = decide(bundle(point, half=1e-3), gate_kw=0.)
        self.assertAlmostEqual(tiny.charge_kw, reference.charge_kw, places=2)
        self.assertAlmostEqual(tiny.discharge_kw, reference.discharge_kw, places=2)

    def test_band_mode_does_not_force_terminal_restoration(self):
        low = .55 * BATTERY.capacity_kwh  # inside the band, away from 65%
        band = decide(bundle([1000] * 6), energy=low, gate_kw=0.)
        self.assertEqual((band.charge_kw, band.discharge_kw), (0., 0.))
        terminal = decide(bundle([1000] * 6), energy=low, gate_kw=0., soc_mode='terminal', terminal_weight=5.)
        self.assertGreater(terminal.charge_kw, 0.)

    def test_band_mode_restores_soc_outside_band(self):
        d = decide(bundle([1000] * 6), energy=.42 * BATTERY.capacity_kwh, gate_kw=0., band_weight=5.)
        self.assertGreater(d.charge_kw, 0.)


class ClosedLoopTests(unittest.TestCase):
    def spec(self, **kwargs):
        base = dict(episode_name='s33', profile='stochastic', forecast_mode='announced_noisy',
                    forecast_noise_kw=25., seed=1000, steps=10)
        base.update(kwargs)
        return ScenarioSpec(**base)

    def run_stochastic(self, spec, **kwargs):
        return run_episode(spec, 'stochastic', decider=decide_stochastic,
                           decider_config=StochasticMPCConfig(), **kwargs)

    def test_episode_invariants(self):
        run = self.run_stochastic(self.spec())
        m = run['metrics']
        self.assertEqual(m['soc_constraint_violations'] + m['power_constraint_violations']
                         + m['simultaneous_charge_discharge_events'] + m['optimisation_failures'], 0)
        self.assertEqual(run['controller_config']['scenarios'], 'gaussian5')
        self.assertEqual(run['mpc_config']['ramp_limit_kw'], 200.)

    def test_counterfactual_future_does_not_change_past_decisions(self):
        spec = self.spec(forecast_mode='damped_trend', forecast_noise_kw=0.)
        k = 4
        a = self.run_stochastic(spec)
        b = self.run_stochastic(spec, wind=lambda i: forcing(spec, i) + (600. if i >= k else 0.))
        for i in range(k + 1):
            self.assertEqual((a['rows'][i]['charge_kw'], a['rows'][i]['discharge_kw']),
                             (b['rows'][i]['charge_kw'], b['rows'][i]['discharge_kw']))

    def test_unknown_controller_without_decider_rejected(self):
        with self.assertRaises(ValueError):
            run_episode(self.spec(), 'stochastic')


if __name__ == '__main__':
    unittest.main()
