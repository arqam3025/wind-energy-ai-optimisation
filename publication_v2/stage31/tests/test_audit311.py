"""Exploratory diagnostic design stays disclosed, paired and synthetic."""
from dataclasses import asdict,replace
from datetime import timedelta
import unittest
from publication_v2.stage31.audit311 import (SEED,DiagnosticCase,WEIGHT_SETTINGS,
    declared_cases,announced_wind,packet_for_case,simulate_case)
from publication_v2.stage31.controllers import MPCConfig
from publication_v2.stage31.evaluation import reproducibility_payload,canonical_sha256
from publication_v2.stage31.scenarios import START

class AuditDiagnosticTests(unittest.TestCase):
    def test_all_thirty_configurations_declared_without_selection(self):
        cases=declared_cases()
        self.assertEqual(len(cases),30);self.assertEqual(len({c.case_id for c in cases}),30)
        self.assertEqual({c.profile for c in cases},{'stable','rapid'})
        self.assertEqual({c.forecast_mode for c in cases},{'announced_perfect','imperfect'})
        self.assertEqual({c.initial_soc for c in cases},{.4,.65,.9})
        self.assertEqual({c.half_width_kw for c in cases},{50.,200.,400.})
        self.assertEqual({c.weight_setting for c in cases},set(WEIGHT_SETTINGS))

    def test_announced_perfect_is_exact_schedule_including_beyond_scored_end(self):
        case=DiagnosticCase('fixture','rapid','announced_perfect',50.,.65,'default')
        for index in (0,3,12,15):
            time=START+timedelta(minutes=10*index)
            packet=packet_for_case(case,(600.,)*6,time,index);packet.validate(time)
            self.assertEqual(packet.point_kw,tuple(announced_wind('rapid',index+h) for h in range(6)))
            self.assertIn('IDEAL_INFORMATION_ONLY',packet.provenance)
            self.assertEqual(packet.target_times[-1],time+timedelta(minutes=60))

    def test_imperfect_forecast_uses_history_not_announced_future_profile(self):
        case=DiagnosticCase('fixture','stable','imperfect',200.,.65,'default')
        history=(600.,600.,600.,600.,600.,600.)
        a=packet_for_case(case,history,START,0)
        b=packet_for_case(replace(case,profile='rapid'),history,START,0)
        self.assertEqual(a,b)
        self.assertNotEqual(a.point_kw,(600.,)*6)

    def test_uncertainty_ablation_preserves_all_point_forecasts(self):
        case=DiagnosticCase('fixture','rapid','imperfect',50.,.65,'default')
        history=(600.,)*6;a=packet_for_case(case,history,START,0)
        b=packet_for_case(replace(case,half_width_kw=400.),history,START,0)
        self.assertEqual(a.point_kw,b.point_kw)
        self.assertNotEqual(a.lower_kw,b.lower_kw);self.assertNotEqual(a.upper_kw,b.upper_kw)
        self.assertEqual(a.alpha,b.alpha)

    def test_physical_perfect_forecast_replay_has_no_forecast_error(self):
        case=DiagnosticCase('fixture','rapid','announced_perfect',50.,.65,'default')
        run=simulate_case(case,'deterministic',steps=8)
        self.assertEqual(run['diagnostics']['first_step_forecast_mae_kw'],0)
        self.assertEqual(run['metrics']['soc_constraint_violations'],0)
        self.assertEqual(run['metrics']['power_constraint_violations'],0)
        self.assertTrue(all(r['forecast_error_kw']==0 for r in run['rows']))

    def test_initial_soc_ablation_is_explicit_and_uncontrolled_battery_idle(self):
        for soc in (.4,.65,.9):
            case=DiagnosticCase('fixture','stable','imperfect',200.,soc,'default')
            run=simulate_case(case,'uncontrolled',steps=8)
            self.assertEqual(run['metrics']['initial_energy_kwh'],2000*soc)
            self.assertEqual(run['metrics']['terminal_energy_kwh'],2000*soc)
            self.assertEqual(run['metrics']['total_throughput_kwh'],0)

    def test_alternative_weights_do_not_mutate_controller_defaults(self):
        before=asdict(MPCConfig())
        for setting in WEIGHT_SETTINGS:
            case=DiagnosticCase('fixture','stable','imperfect',200.,.65,setting)
            simulate_case(case,'uncontrolled',steps=8)
        self.assertEqual(asdict(MPCConfig()),before)
        self.assertEqual(before['ramp_weight'],1.)
        self.assertEqual(before['uncertainty_weight'],.5)
        self.assertEqual(before['throughput_weight'],.05)

    def test_seeded_diagnostic_reproduction_excludes_timings(self):
        case=DiagnosticCase('fixture','stable','imperfect',200.,.65,'default')
        a=simulate_case(case,'adaptive',seed=SEED,steps=8)
        b=simulate_case(case,'adaptive',seed=SEED,steps=8)
        self.assertEqual(canonical_sha256(reproducibility_payload(a)),canonical_sha256(reproducibility_payload(b)))
        c=simulate_case(case,'adaptive',seed=SEED+1,steps=8)
        self.assertNotEqual(a['rows'][0]['forecast_sha256'],c['rows'][0]['forecast_sha256'])

if __name__=='__main__':unittest.main()
