"""Prespecified exploratory synthetic diagnostics; never a production forecaster.

Perfect forecasts use a fully ANNOUNCED deterministic forcing schedule known at
simulation initialization. They are an ideal-information benchmark, not an
operational forecast, historical observation or conformal guarantee.
"""
from dataclasses import dataclass, asdict, replace
from datetime import timedelta
import csv
import json
from pathlib import Path
import sys
from .battery import BatteryConfig, transition, grid_export, ramp_metrics
from .forecast import ForecastBundle
from .controllers import MPCConfig, CONTROLLERS, decide
from .evaluation import (jsonable,canonical_sha256,summarize_trace,validate_plan,
    reproducibility_payload,paired_comparisons)
from .scenarios import START,past_only_forecast
from . import runner

SEED=20261111

@dataclass(frozen=True)
class DiagnosticCase:
    case_id: str
    profile: str
    forecast_mode: str
    half_width_kw: float
    initial_soc: float
    weight_setting: str

WEIGHT_SETTINGS={
    'default':{},
    'ramp_only':{'throughput_weight':0.,'soc_margin_weight':0.,'uncertainty_weight':0.,'terminal_weight':0.},
    'risk_off':{'uncertainty_weight':0.},
    'risk_high':{'uncertainty_weight':2.},
    'throughput_high':{'throughput_weight':.5},
    'terminal_off':{'terminal_weight':0.},
    'soc_margin_off':{'soc_margin_weight':0.},
}


def declared_cases():
    cases=[]
    for profile in ('stable','rapid'):
        for mode in ('announced_perfect','imperfect'):
            for width in (50.,400.):
                cases.append(DiagnosticCase(f'forecast_{profile}_{mode}_w{int(width)}',profile,mode,width,.65,'default'))
    for profile in ('stable','rapid'):
        for setting in WEIGHT_SETTINGS:
            cases.append(DiagnosticCase(f'weight_{profile}_{setting}',profile,'imperfect',200.,.65,setting))
    for profile in ('stable','rapid'):
        for soc in (.4,.9):
            for setting in ('default','terminal_off'):
                cases.append(DiagnosticCase(f'soc_{profile}_{int(soc*100)}_{setting}',profile,'imperfect',200.,soc,setting))
    assert len(cases)==30 and len({c.case_id for c in cases})==30
    return tuple(cases)


def announced_wind(profile,index):
    if profile=='stable':return 1000.
    if profile!='rapid':raise ValueError('Unknown diagnostic forcing schedule')
    if index<0:return 600.
    return (600.,1750.,400.,1500.)[(index//4)%4]


def packet_for_case(case,history,decision_time,index,seed=SEED):
    # No realised observation array is received. The perfect case is an explicit
    # preannounced mathematical schedule; the imperfect case receives past only.
    if case.forecast_mode=='announced_perfect':
        point=tuple(announced_wind(case.profile,index+h) for h in range(6))
        return ForecastBundle(issue_time=decision_time,point_kw=point,
            lower_kw=tuple(max(0.,p-case.half_width_kw) for p in point),
            upper_kw=tuple(p+case.half_width_kw for p in point),alpha=.1,
            provenance='SYNTHETIC_ANNOUNCED_SCHEDULE_IDEAL_INFORMATION_ONLY',
            available_at=decision_time,model_available_at=START-timedelta(days=1),
            target_times=tuple(decision_time+timedelta(minutes=10*(h+1)) for h in range(6)),
            uncertainty_kind='SYNTHETIC_INTERVALS')
    if case.forecast_mode!='imperfect':raise ValueError('Unknown diagnostic forecast mode')
    packet=past_only_forecast(history,decision_time,seed=seed,decision_index=index,
        base_width_kw=0.,width_growth_kw=0.)
    return replace(packet,lower_kw=tuple(max(0.,p-case.half_width_kw) for p in packet.point_kw),
        upper_kw=tuple(p+case.half_width_kw for p in packet.point_kw))


def simulate_case(case,controller,*,seed=SEED,steps=16):
    battery=BatteryConfig(initial_soc=case.initial_soc)
    config=replace(MPCConfig(),**WEIGHT_SETTINGS[case.weight_setting])
    wind=tuple(announced_wind(case.profile,i) for i in range(steps))
    history=tuple(announced_wind(case.profile,i) for i in range(-6,0))
    energy=battery.initial_energy_kwh;previous=history[-1];rows=[];plans=[]
    for index in range(steps):
        time=START+timedelta(minutes=10*index)
        packet=packet_for_case(case,history,time,index,seed);packet.validate(time)
        action=decide(controller,packet,time,energy,previous,battery,config)
        residual=validate_plan(action.plan,battery,energy,1 if controller=='heuristic' else 6)
        # Only now release the realised interval, even for the announced schedule.
        actual=wind[index];nxt=transition(battery,energy,action.charge_kw,action.discharge_kw)
        grid=grid_export(actual,action.charge_kw,action.discharge_kw);ramp,excess=ramp_metrics(grid,previous,config.ramp_limit_kw)
        predicted=packet.point_kw[0]+action.discharge_kw-action.charge_kw
        predicted_ramp,predicted_excess=ramp_metrics(predicted,previous,config.ramp_limit_kw)
        rows.append({'decision_time':time.isoformat(),'interval_end':(time+timedelta(minutes=10)).isoformat(),
            'wind_kw':actual,'previous_grid_kw':previous,'grid_kw':grid,'charge_kw':action.charge_kw,'discharge_kw':action.discharge_kw,
            'energy_before_kwh':energy,'energy_after_kwh':nxt,'ramp_kw':ramp,'ramp_exceedance_kw':excess,
            'forecast_sha256':canonical_sha256(packet),'forecast_fault':None,'status':action.status,'solver_status':action.solver_status,
            'optimization_failed':action.optimization_failed,'fallback':action.fallback,'fallback_reason':action.fallback_reason,
            'computation_time_s':action.computation_time_s,'plan_energy_residual_kwh':residual,
            'first_point_kw':packet.point_kw[0],'first_lower_kw':packet.lower_kw[0],'first_upper_kw':packet.upper_kw[0],
            'forecast_error_kw':actual-packet.point_kw[0],'predicted_first_grid_kw':predicted,
            'predicted_first_ramp_kw':predicted_ramp,'predicted_first_exceedance_kw':predicted_excess,
            'forecast_mode':case.forecast_mode})
        plans.append(jsonable(action.plan));energy=nxt;previous=grid;history=history+(actual,)
    metrics=summarize_trace(rows,battery,config)
    if any(metrics[k] for k in ('soc_constraint_violations','power_constraint_violations','simultaneous_charge_discharge_events')):raise ValueError('Diagnostic physical failure')
    if abs(metrics['energy_accounting_residual_kwh'])>1e-6:raise ValueError('Diagnostic energy accounting failure')
    diagnostics={'first_step_forecast_mae_kw':sum(abs(r['forecast_error_kw']) for r in rows)/steps,
        'predicted_first_violations':sum(r['predicted_first_exceedance_kw']>1e-6 for r in rows),
        'predicted_first_total_exceedance_kw':sum(r['predicted_first_exceedance_kw'] for r in rows),
        'threshold_touch_then_realised_violation':sum(abs(r['predicted_first_ramp_kw']-200.)<1e-5 and r['ramp_exceedance_kw']>1e-6 for r in rows),
        'upper_soc_hits':sum(abs(r['energy_after_kwh']-battery.max_energy_kwh)<1e-5 for r in rows),
        'lower_soc_hits':sum(abs(r['energy_after_kwh']-battery.min_energy_kwh)<1e-5 for r in rows),
        'terminal_plan_target_hits':sum(p is not None and p['horizon_steps']==6 and abs(p['energy_kwh'][-1]-config.terminal_soc*battery.capacity_kwh)<1e-5 for p in plans),
        'actual_terminal_target_deviation_kwh':abs(energy-config.terminal_soc*battery.capacity_kwh),
        'first_interval_bound_misses':sum(not(r['first_lower_kw']<=r['wind_kw']<=r['first_upper_kw']) for r in rows)}
    return {'data_kind':'SYNTHETIC_ONLY','scenario':case.case_id,'controller':controller,'seed':seed,
        'diagnostic_case':asdict(case),'wind_sha256':canonical_sha256(wind),'battery':asdict(battery),'mpc_config':asdict(config),
        'metrics':metrics,'diagnostics':diagnostics,'rows':rows,'plans':plans}


def verify_archived_originals(audit_directory):
    audit=Path(audit_directory);before=json.loads((audit/'before.json').read_text())
    snapshot=audit/'source_before';result=[]
    for name,inventory in before['original_runs'].items():
        run=runner.ROOT/'publication_v2/stage31/runs'/name
        actual={p.relative_to(run).as_posix():runner.digest(p) for p in run.rglob('*') if p.is_file()}
        if actual!=inventory:raise ValueError('Original Stage 3.1 output changed')
        marker=json.loads((run/'COMPLETED.json').read_text());manifest=json.loads((run/'manifest.json').read_text())
        if marker['manifest_sha256']!=runner.digest(run/'manifest.json'):raise ValueError('Archived completion differs')
        for n,h in manifest['artifact_sha256'].items():
            if runner.digest(run/n)!=h:raise ValueError('Archived synthetic artifact differs')
        for n,h in manifest['source_sha256'].items():
            if runner.digest(snapshot/n)!=h:raise ValueError('Archived source snapshot differs')
        traces=[]
        for p in sorted((run/'traces').glob('*.json')):
            trace=json.loads(p.read_text());traces.append((trace['scenario']+'__'+trace['controller'],canonical_sha256(reproducibility_payload(trace))))
        if canonical_sha256(dict(traces))!=manifest['comparison_fingerprint']:raise ValueError('Archived fingerprint differs')
        result.append({'run':name,'status':'ARCHIVED_ARTIFACTS_AND_SOURCE_SNAPSHOT_VERIFIED','files_unchanged':len(inventory),'fingerprint':manifest['comparison_fingerprint']})
    return result


def run_diagnostics(output,*,seed=SEED,steps=16):
    if type(seed) is not int or type(steps) is not int or steps<8:raise ValueError('Integer seed and at least eight diagnostic steps required')
    directory=runner._inside(output);directory.mkdir(exist_ok=False)
    runner._json(directory/'STARTED.json',{'scope':'EXPLORATORY_SYNTHETIC_DIAGNOSTICS','seed':seed,'client_date':'2026-11-11'})
    try:
        cases=declared_cases()
        runner._json(directory/'all_tested_configurations.json',{'cases':[asdict(c) for c in cases],
            'all_weight_values':{k:asdict(replace(MPCConfig(),**v)) for k,v in WEIGHT_SETTINGS.items()},
            'seed':seed,'steps':steps,'controllers':list(CONTROLLERS),
            'perfect_mode':'preannounced deterministic forcing, ideal information; not an operational forecast',
            'case_grid_declared_before_first_diagnostic_solve':True,'controller_selection_performed':False})
        source=runner._source_hashes();environment=runner.environment();policy=runner.ROOT/'publication_v2/stage2/provenance_policy.json'
        input_hash=runner.digest(policy);governance=json.loads(policy.read_text())
        if governance['real_data_reviews']!={} or governance['confirmatory_status']!='BLOCKED_CONFIRMATORY_TEST':raise ValueError('Unexpected governance')
        traces=directory/'traces';traces.mkdir();runs=[];summary=[];fingerprints={}
        for case in cases:
            for controller in CONTROLLERS:
                run=simulate_case(case,controller,seed=seed,steps=steps);runs.append(run)
                key=case.case_id+'__'+controller;runner._json(traces/(key+'.json'),run)
                summary.append({**asdict(case),'controller':controller,**run['metrics'],**run['diagnostics']})
                fingerprints[key]=canonical_sha256(reproducibility_payload(run))
        runner._csv(directory/'diagnostic_summary.csv',summary);runner._json(directory/'diagnostic_summary.json',summary)
        runner._csv(directory/'paired_controller_differences.csv',paired_comparisons(runs));runner._json(directory/'trace_fingerprints.json',fingerprints)
        if source!=runner._source_hashes() or environment!=runner.environment() or input_hash!=runner.digest(policy):raise ValueError('Diagnostic inputs changed during execution')
        artifacts={p.relative_to(directory).as_posix():runner.digest(p) for p in directory.rglob('*') if p.is_file()}
        manifest={'schema_version':'publication_v2.stage311.exploratory-audit.v1','status':'COMPLETED_EXPLORATORY_SYNTHETIC_ONLY',
            'seed':seed,'steps':steps,'case_count':len(cases),'controller_count':len(CONTROLLERS),'rows':len(summary),
            'source_sha256':source,'environment':environment,'input_sha256':{'publication_v2/stage2/provenance_policy.json':input_hash},
            'artifact_sha256':artifacts,'comparison_fingerprint':canonical_sha256(fingerprints),'timings_excluded_from_reproduction':True,
            'data_admission':'PENDING_REVIEW','confirmatory_status':'BLOCKED_CONFIRMATORY_TEST','models_trained':0,
            'default_controller_parameters_changed':False,'selection_or_confirmatory_evaluation':False}
        runner._json(directory/'manifest.json',manifest);runner._json(directory/'COMPLETED.json',{'manifest_sha256':runner.digest(directory/'manifest.json'),'status':manifest['status']})
        return manifest
    except BaseException as error:
        if not(directory/'COMPLETED.json').exists():runner._json(directory/'FAILED.json',{'error_type':type(error).__name__,'message':str(error)})
        raise


def verify_diagnostics(path):
    directory=runner._inside(path);manifest=json.loads((directory/'manifest.json').read_text());marker=json.loads((directory/'COMPLETED.json').read_text())
    if marker.get('manifest_sha256')!=runner.digest(directory/'manifest.json') or marker.get('status')!='COMPLETED_EXPLORATORY_SYNTHETIC_ONLY':raise ValueError('Diagnostic completion differs')
    if manifest.get('schema_version')!='publication_v2.stage311.exploratory-audit.v1' or manifest.get('data_admission')!='PENDING_REVIEW' or manifest.get('confirmatory_status')!='BLOCKED_CONFIRMATORY_TEST' or manifest.get('models_trained')!=0:raise ValueError('Diagnostic scope differs')
    if manifest['source_sha256']!=runner._source_hashes():raise ValueError('Current source differs from diagnostics')
    policy_path=runner.ROOT/'publication_v2/stage2/provenance_policy.json'
    expected_input={'publication_v2/stage2/provenance_policy.json':runner.digest(policy_path)}
    if manifest.get('input_sha256')!=expected_input:raise ValueError('Missing or changed diagnostic governance input')
    policy=json.loads(policy_path.read_text())
    if policy.get('real_data_reviews')!={} or policy.get('confirmatory_status')!='BLOCKED_CONFIRMATORY_TEST':raise ValueError('Unexpected diagnostic governance state')
    actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    if actual!=set(manifest['artifact_sha256'])|{'manifest.json','COMPLETED.json'}:raise ValueError('Diagnostic artifact membership differs')
    for n,h in manifest['artifact_sha256'].items():
        p=(directory/n).resolve()
        if not p.is_relative_to(directory) or runner.digest(p)!=h:raise ValueError('Diagnostic artifact differs')
    for n,h in manifest['input_sha256'].items():
        p=(runner.ROOT/n).resolve()
        if not p.is_relative_to(runner.ROOT) or runner.digest(p)!=h:raise ValueError('Diagnostic governance differs')
    configs=json.loads((directory/'all_tested_configurations.json').read_text());summary=json.loads((directory/'diagnostic_summary.json').read_text())
    expected_cases=[asdict(c) for c in declared_cases()]
    if configs['cases']!=expected_cases or manifest['case_count']!=30 or manifest['controller_count']!=5 or manifest['rows']!=150 or len(summary)!=150:raise ValueError('Diagnostic configured cohort differs')
    fingerprints={}
    for case in declared_cases():
        for controller in CONTROLLERS:
            key=case.case_id+'__'+controller;run=json.loads((directory/'traces'/(key+'.json')).read_text())
            if run['diagnostic_case']!=asdict(case) or run['controller']!=controller or len(run['rows'])!=manifest['steps']:raise ValueError('Diagnostic trace identity differs')
            reconstructed=summarize_trace(run['rows'],BatteryConfig(**run['battery']),MPCConfig(**run['mpc_config']))
            if reconstructed!=run['metrics']:raise ValueError('Diagnostic trace metrics differ')
            fingerprints[key]=canonical_sha256(reproducibility_payload(run))
    if fingerprints!=json.loads((directory/'trace_fingerprints.json').read_text()) or canonical_sha256(fingerprints)!=manifest['comparison_fingerprint']:raise ValueError('Diagnostic fingerprint differs')
    return manifest


def compare_diagnostics(first,second):
    a,b=verify_diagnostics(first),verify_diagnostics(second)
    for key in ('seed','steps','source_sha256','input_sha256','environment','comparison_fingerprint'):
        if a[key]!=b[key]:raise ValueError('Diagnostic reproduction differs: '+key)
    return {'status':'REPRODUCED_EXPLORATORY_DIAGNOSTICS_EXCLUDING_TIMINGS','fingerprint':a['comparison_fingerprint']}


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run');r.add_argument('--output',type=Path,required=True);r.add_argument('--seed',type=int,default=SEED);r.add_argument('--steps',type=int,default=16)
    v=sub.add_parser('verify');v.add_argument('--run',type=Path,required=True)
    c=sub.add_parser('compare');c.add_argument('--first',type=Path,required=True);c.add_argument('--second',type=Path,required=True)
    args=p.parse_args(argv)
    if args.command=='run':
        m=run_diagnostics(args.output,seed=args.seed,steps=args.steps);print(json.dumps({'status':m['status'],'cases':m['case_count'],'rows':m['rows'],'fingerprint':m['comparison_fingerprint']}))
    elif args.command=='verify':print(json.dumps({'status':'VERIFIED_EXPLORATORY_SYNTHETIC_ONLY','fingerprint':verify_diagnostics(args.run)['comparison_fingerprint']}))
    else:print(json.dumps(compare_diagnostics(args.first,args.second)))
    return 0

if __name__=='__main__':raise SystemExit(main())
