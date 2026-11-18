"""Synthetic replay, comparison, leakage and energy-accounting regressions."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import unittest
from unittest.mock import patch
from publication_v2.stage31.battery import BatteryConfig, transition
from publication_v2.stage31.controllers import CONTROLLERS, MPCConfig
from publication_v2.stage31.scenarios import START, make_scenarios, past_only_forecast, forecast_for_step
from publication_v2.stage31.evaluation import (simulate,summarize_trace,paired_comparisons,
    reproducibility_payload,canonical_sha256,validate_plan)

class SyntheticEvaluationTests(unittest.TestCase):
    def test_all_ten_scenarios_seeded_and_complete(self):
        scenarios=make_scenarios(42,8)
        self.assertEqual(len(scenarios),10)
        self.assertEqual(scenarios,make_scenarios(42,8))
        self.assertNotEqual(scenarios,make_scenarios(43,8))
        self.assertEqual({s.name for s in scenarios},{'stable','gradual_increase','gradual_decrease','sudden_ramps','forecast_bias','high_uncertainty','low_initial_soc','high_initial_soc','invalid_forecasts','conflicting_constraints'})

    def test_future_outcome_suffix_cannot_affect_issued_forecast(self):
        scenario=make_scenarios(7,8)[3]
        altered=replace(scenario,wind_kw=(999999.,)*8)
        a=forecast_for_step(scenario,scenario.initial_history_kw,START,0)
        b=forecast_for_step(altered,scenario.initial_history_kw,START,0)
        self.assertEqual(a,b)

    def test_current_outcome_not_visible_to_dispatch(self):
        scenario=make_scenarios(7,8)[0]
        altered=replace(scenario,wind_kw=(2000.,)+scenario.wind_kw[1:])
        a,b=simulate(scenario,'deterministic'),simulate(altered,'deterministic')
        self.assertEqual(a['rows'][0]['forecast_sha256'],b['rows'][0]['forecast_sha256'])
        self.assertEqual(a['rows'][0]['charge_kw'],b['rows'][0]['charge_kw'])
        self.assertEqual(a['rows'][0]['discharge_kw'],b['rows'][0]['discharge_kw'])
        self.assertNotEqual(a['rows'][0]['grid_kw'],b['rows'][0]['grid_kw'])

    def test_uncontrolled_baseline_has_no_battery_or_fallback(self):
        run=simulate(make_scenarios(3,8)[3],'uncontrolled')
        m=run['metrics']
        self.assertEqual(m['total_throughput_kwh'],0)
        self.assertEqual(m['terminal_inventory_change_kwh'],0)
        self.assertEqual(m['safe_fallback_events'],0)
        self.assertTrue(all(r['grid_kw']==r['wind_kw'] for r in run['rows']))
        self.assertGreater(m['ramp_violations'],0)

    def test_all_five_controllers_share_trace_forecasts_and_denominators(self):
        scenario=make_scenarios(3,8)[0]
        runs=[simulate(scenario,c) for c in CONTROLLERS]
        pairs=paired_comparisons(runs)
        self.assertEqual(len(pairs),6)
        self.assertTrue(all(r['metrics']['intervals']==8 for r in runs))
        self.assertTrue(all(r['metrics']['soc_constraint_violations']==0 for r in runs))
        self.assertTrue(all(r['metrics']['power_constraint_violations']==0 for r in runs))
        self.assertTrue(all(r['metrics']['simultaneous_charge_discharge_events']==0 for r in runs))
        self.assertTrue(all(abs(r['metrics']['energy_accounting_residual_kwh'])<1e-6 for r in runs))

    def test_all_faults_retained_with_safe_fallback_denominators(self):
        scenario=make_scenarios(3,12)[8]
        run=simulate(scenario,'adaptive')
        self.assertEqual(run['metrics']['intervals'],12)
        self.assertEqual(run['metrics']['forecast_fault_events'],3)
        self.assertEqual(run['metrics']['safe_fallback_events'],3)
        self.assertEqual(run['metrics']['optimisation_failures'],0)
        self.assertTrue(all(r['charge_kw']==r['discharge_kw']==0 for r in run['rows'] if r['forecast_fault']))

    def test_conflicting_grid_case_records_infeasibility_and_actual_violations(self):
        scenario=make_scenarios(3,8)[9]
        run=simulate(scenario,'adaptive')
        self.assertEqual(run['metrics']['optimisation_failures'],8)
        self.assertEqual(run['metrics']['safe_fallback_events'],8)
        self.assertEqual(run['metrics']['grid_limit_violations'],8)
        self.assertEqual(run['metrics']['soc_constraint_violations'],0)
        self.assertEqual(run['metrics']['total_throughput_kwh'],0)

    def test_reproducibility_excludes_only_wall_clock_timings(self):
        scenario=make_scenarios(17,8)[3]
        a,b=simulate(scenario,'adaptive'),simulate(scenario,'adaptive')
        self.assertEqual(canonical_sha256(reproducibility_payload(a)),canonical_sha256(reproducibility_payload(b)))
        modified=deepcopy(a);modified['rows'][0]['charge_kw']+=1
        self.assertNotEqual(canonical_sha256(reproducibility_payload(a)),canonical_sha256(reproducibility_payload(modified)))

    def test_one_move_applied_then_state_and_anchor_replanned(self):
        scenario=make_scenarios(3,8)[3]
        run=simulate(scenario,'deterministic')
        for i,row in enumerate(run['rows']):
            plan=run['plans'][i]
            self.assertEqual(row['charge_kw'],plan['charge_kw'][0])
            self.assertEqual(row['discharge_kw'],plan['discharge_kw'][0])
            self.assertEqual(row['energy_before_kwh'],plan['energy_kwh'][0])
            if i:
                self.assertEqual(row['energy_before_kwh'],run['rows'][i-1]['energy_after_kwh'])
                self.assertEqual(row['previous_grid_kw'],run['rows'][i-1]['grid_kw'])

    def test_heuristic_one_step_plan_is_honest_and_validated(self):
        run=simulate(make_scenarios(3,8)[3],'heuristic')
        self.assertTrue(all(len(p['charge_kw'])==1 for p in run['plans']))
        self.assertEqual(run['metrics']['power_constraint_violations'],0)

    def test_duplicate_or_unpaired_comparison_cannot_silently_drop_a_run(self):
        scenario=make_scenarios(3,8)[0];runs=[simulate(scenario,c) for c in CONTROLLERS]
        with self.assertRaises(ValueError):paired_comparisons(runs+[runs[0]])
        with self.assertRaises(ValueError):paired_comparisons(runs[:-1])
        modified=deepcopy(runs);modified[1]['wind_sha256']='wrong'
        with self.assertRaises(ValueError):paired_comparisons(modified)
        modified=deepcopy(runs);modified[1]['rows'][0]['forecast_sha256']='wrong'
        with self.assertRaises(ValueError):paired_comparisons(modified)

    def test_accounting_detects_tampered_power_or_ramp(self):
        b=BatteryConfig();cfg=MPCConfig();run=simulate(make_scenarios(3,8)[0],'uncontrolled')
        rows=deepcopy(run['rows']);rows[0]['grid_kw']+=1
        with self.assertRaises(ValueError):summarize_trace(rows,b,cfg)
        rows=deepcopy(run['rows']);rows[1]['energy_before_kwh']+=1
        with self.assertRaises(ValueError):summarize_trace(rows,b,cfg)

    def test_round_trip_loss_and_signed_import_accounting(self):
        b=BatteryConfig();cfg=MPCConfig();energy=b.initial_energy_kwh
        rows=[];previous_grid=0.
        for c,d in [(100.,0.),(0.,90.25)]:
            nxt=transition(b,energy,c,d);grid=d-c;ramp=abs(grid-previous_grid)
            rows.append({'wind_kw':0.,'grid_kw':grid,'charge_kw':c,'discharge_kw':d,'energy_before_kwh':energy,'energy_after_kwh':nxt,
                'previous_grid_kw':previous_grid,'ramp_kw':ramp,'ramp_exceedance_kw':max(0.,ramp-200.),'optimization_failed':False,'fallback':False,'forecast_fault':None,'computation_time_s':0.})
            energy=nxt;previous_grid=grid
        m=summarize_trace(rows,b,cfg)
        self.assertAlmostEqual(m['terminal_inventory_change_kwh'],0)
        self.assertAlmostEqual(m['conversion_loss_kwh'],1.625)
        self.assertAlmostEqual(m['actual_import_energy_kwh'],100/6)
        self.assertAlmostEqual(m['actual_export_energy_kwh'],90.25/6)
        self.assertAlmostEqual(m['energy_accounting_residual_kwh'],0)

    def test_invalid_seed_steps_history_and_unsupported_controller_rejected(self):
        for seed,steps in [(True,8),(1,7),(1,True)]:
            with self.assertRaises(ValueError):make_scenarios(seed,steps)
        with self.assertRaises(ValueError):past_only_forecast((),START,seed=1,decision_index=0)
        with self.assertRaises(ValueError):simulate(make_scenarios(1,8)[0],'unknown')

if __name__=='__main__':unittest.main()
