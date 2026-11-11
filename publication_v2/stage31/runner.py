"""Synthetic-only CLI. This module has no real-data/model-training input path."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import sys
import uuid
from .controllers import CONTROLLERS, MPCConfig
from .battery import BatteryConfig
from .scenarios import make_scenarios
from .evaluation import (jsonable, canonical_sha256, simulate, paired_comparisons,
                         reproducibility_payload, summarize_trace, TOLERANCE)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = 'publication_v2.stage31.synthetic-run.v2'
POLICY_INPUT = 'publication_v2/stage2/provenance_policy.json'
_REQUIRED_ARTIFACTS = frozenset(('STARTED.json', 'summary.csv', 'paired_comparisons.csv',
    'metrics.json', 'trace_fingerprints.json', 'scenarios.json', 'configuration.json', 'validation.json'))


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(path):
    p=Path(path).resolve()
    if not p.is_relative_to(ROOT):raise ValueError('Synthetic output must remain inside this isolated project')
    # Existing symlink/junction targets are resolved above; parents must also stay inside.
    return p


def _json(path, value):
    if path.exists():raise FileExistsError('Refusing to overwrite synthetic artifact')
    temporary=path.with_name(path.name+'.tmp')
    with temporary.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(jsonable(value),f,indent=2,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)


def _csv(path, rows):
    if not rows:raise ValueError('Empty synthetic comparison table')
    with path.open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def environment():
    import numpy,scipy
    highsversion=None
    try:
        from scipy.optimize import _highspy
        core=_highspy._core
        highsversion='.'.join(str(getattr(core,'HIGHS_VERSION_'+x)) for x in ('MAJOR','MINOR','PATCH'))
    except (ImportError,AttributeError):pass
    return {'python':platform.python_version(),'numpy':numpy.__version__,'scipy':scipy.__version__,
        'scipy_bundled_highs':highsversion,'os':platform.system(),'os_release':platform.release(),'machine':platform.machine(),
        'native_clean_environment_reproduction':False,'timings_reproducible':False}


def _source_hashes():
    paths=[p for p in sorted(Path(__file__).parent.rglob('*.py')) if 'runs' not in p.parts and '__pycache__' not in p.parts]
    requirement=Path(__file__).with_name('requirements.txt')
    if requirement.exists():paths.append(requirement)
    for path in paths:
        if not path.resolve().is_relative_to(ROOT):raise ValueError('Source identity escapes isolated project')
    return {p.relative_to(ROOT).as_posix():digest(p) for p in paths}


def run_experiments(*, run_id=None, seed=20261110, steps=24, output_root=None):
    run_id=run_id or 'synthetic_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
    if not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,100}',run_id):raise ValueError('Unsafe or missing run identity')
    # Validate all scenario parameters before creating an output directory.
    scenarios=make_scenarios(seed,steps)
    base=_inside(output_root or ROOT/'publication_v2/stage31/runs');base.mkdir(parents=True,exist_ok=True)
    directory=_inside(base/run_id);directory.mkdir(exist_ok=False)
    _json(directory/'STARTED.json',{'status':'STARTED','data_kind':'SYNTHETIC_ONLY','run_id':run_id})
    try:
        policy=_read_json(ROOT/POLICY_INPUT)
        if policy['real_data_reviews']!={} or policy['confirmatory_status']!='BLOCKED_CONFIRMATORY_TEST':raise ValueError('Unexpected real-data governance state')
        source_before=_source_hashes();environment_before=environment()
        input_before={POLICY_INPUT:digest(ROOT/POLICY_INPUT)}
        traces=directory/'traces';traces.mkdir()
        runs=[];summary=[];fingerprints={}
        for scenario in scenarios:
            for controller in CONTROLLERS:
                run=simulate(scenario,controller);runs.append(run)
                _json(traces/(scenario.name+'__'+controller+'.json'),run)
                summary.append({'data_kind':'SYNTHETIC_ONLY','scenario':scenario.name,'controller':controller,**run['metrics']})
                fingerprints[scenario.name+'__'+controller]=canonical_sha256(reproducibility_payload(run))
        pairs=paired_comparisons(runs)
        _csv(directory/'summary.csv',summary);_csv(directory/'paired_comparisons.csv',pairs)
        _json(directory/'metrics.json',summary);_json(directory/'trace_fingerprints.json',fingerprints)
        _json(directory/'scenarios.json',[asdict(s) for s in scenarios])
        _json(directory/'configuration.json',{'battery_defaults':asdict(BatteryConfig()),'mpc_defaults':asdict(MPCConfig()),'scenario_overrides':'Low/high initial SOC and conflicting grid bounds are explicit in scenarios.json; identical across controllers'})
        checks={'battery_soc_violations':sum(r['metrics']['soc_constraint_violations'] for r in runs),
            'battery_power_violations':sum(r['metrics']['power_constraint_violations'] for r in runs),
            'simultaneous_charge_discharge_events':sum(r['metrics']['simultaneous_charge_discharge_events'] for r in runs),
            'max_power_balance_residual_kw':max(r['metrics']['maximum_power_balance_residual_kw'] for r in runs),
            'max_energy_update_residual_kwh':max(r['metrics']['maximum_energy_update_residual_kwh'] for r in runs),
            'max_total_energy_accounting_residual_kwh':max(abs(r['metrics']['energy_accounting_residual_kwh']) for r in runs),
            'all_controller_pairs_share_inputs':True,'intentional_grid_conflicts_not_hidden':True}
        _json(directory/'validation.json',checks)
        if (_source_hashes()!=source_before or environment()!=environment_before
                or {key:digest(ROOT/key) for key in input_before}!=input_before):
            raise ValueError('Source, governance input or environment changed during synthetic execution')
        source=source_before
        artifacts={p.relative_to(directory).as_posix():digest(p) for p in sorted(directory.rglob('*')) if p.is_file()}
        manifest={'schema_version':SCHEMA_VERSION,'status':'COMPLETED_SYNTHETIC_ONLY','run_id':run_id,
            'created_at_utc':datetime.now(timezone.utc).isoformat(),'seed':seed,'steps_per_scenario':steps,
            'scenario_count':len(scenarios),'controller_count':len(CONTROLLERS),'comparison_rows':len(summary),
            'data_admission':'PENDING_REVIEW','confirmatory_status':'BLOCKED_CONFIRMATORY_TEST','models_trained':0,
            'source_sha256':source,'artifact_sha256':artifacts,'input_sha256':input_before,'environment':environment_before,
            'base_publication_commit':'968773d8f2c85dd28ed5bd28ec873a231c2d3db5','development_stage':'STAGE31_SYNTHETIC_ONLY',
            'forecast_rule':'SYNTHETIC_PAST_ONLY_ANALYTIC_RULE_V1','uncertainty':'synthetic intervals, not calibrated conformal measurements',
            'comparison_fingerprint':canonical_sha256(fingerprints),'reproducibility_scope':'same seeded inputs/software/native stack; wall-clock timing excluded'}
        _json(directory/'manifest.json',manifest)
        _json(directory/'COMPLETED.json',{'status':'COMPLETED_SYNTHETIC_ONLY','manifest_sha256':digest(directory/'manifest.json'),'data_admission':'PENDING_REVIEW','confirmatory_status':'BLOCKED_CONFIRMATORY_TEST'})
        return directory,manifest
    except BaseException as error:
        if not(directory/'COMPLETED.json').exists():_json(directory/'FAILED.json',{'status':'FAILED','error_type':type(error).__name__,'message':str(error),'data_kind':'SYNTHETIC_ONLY'})
        raise


def _read_json(path):
    """Reject duplicate keys and nonfinite JSON instead of repairing evidence."""
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON key in synthetic evidence')
            result[key]=value
        return result
    def invalid_constant(value):
        raise ValueError('Nonfinite JSON value in synthetic evidence: '+value)
    return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=pairs,
                      parse_constant=invalid_constant)


def _inventory(mapping, base, label, *, required=()):
    if not isinstance(mapping,dict) or not mapping:
        raise ValueError(label+' inventory must be a nonempty mapping')
    if not set(required).issubset(mapping):raise ValueError(label+' inventory is incomplete')
    for relative,expected in mapping.items():
        if (not isinstance(relative,str) or not relative or '\\' in relative or ':' in relative
                or PurePosixPath(relative).is_absolute() or any(p in ('','.','..') for p in relative.split('/'))
                or PurePosixPath(relative).as_posix()!=relative):
            raise ValueError('Invalid relative path in '+label+' inventory')
        if not isinstance(expected,str) or not re.fullmatch('[0-9a-f]{64}',expected):
            raise ValueError('Invalid SHA256 in '+label+' inventory')
        target=(base/relative).resolve()
        if not target.is_relative_to(base) or not target.is_file() or digest(target)!=expected:
            raise ValueError('Changed, missing or escaping '+label+' artifact')
    return set(mapping)


def _count(value,name,minimum=0):
    if type(value) is not int or (minimum is not None and value<minimum):raise ValueError('Invalid synthetic '+name)
    return value


def _same_json(left,right,message):
    if canonical_sha256(left)!=canonical_sha256(right):raise ValueError(message)


def _check_csv(path,expected):
    with path.open(encoding='utf-8',newline='') as stream:
        reader=csv.DictReader(stream)
        rows=list(reader)
        if reader.fieldnames!=list(expected[0]):raise ValueError('Changed synthetic CSV columns')
    if rows!=[{key:str(value) for key,value in row.items()} for row in expected]:
        raise ValueError('Synthetic CSV differs from authenticated traces')


def _validation_checks(runs):
    return {'battery_soc_violations':sum(r['metrics']['soc_constraint_violations'] for r in runs),
        'battery_power_violations':sum(r['metrics']['power_constraint_violations'] for r in runs),
        'simultaneous_charge_discharge_events':sum(r['metrics']['simultaneous_charge_discharge_events'] for r in runs),
        'max_power_balance_residual_kw':max(r['metrics']['maximum_power_balance_residual_kw'] for r in runs),
        'max_energy_update_residual_kwh':max(r['metrics']['maximum_energy_update_residual_kwh'] for r in runs),
        'max_total_energy_accounting_residual_kwh':max(abs(r['metrics']['energy_accounting_residual_kwh']) for r in runs),
        'all_controller_pairs_share_inputs':True,'intentional_grid_conflicts_not_hidden':True}


def verify_run(path):
    """Verify complete v2 evidence and recompute metrics/fingerprints without solves.

    This is a consistency/integrity check, not authentication of independent
    authorship or a clean-environment scientific replication. Legacy v1 outputs
    remain untouched and require their archived code and separate audit evidence.
    """
    directory=_inside(path)
    marker=_read_json(directory/'COMPLETED.json')
    if (not isinstance(marker,dict) or marker.get('status')!='COMPLETED_SYNTHETIC_ONLY'
            or marker.get('data_admission')!='PENDING_REVIEW'
            or marker.get('confirmatory_status')!='BLOCKED_CONFIRMATORY_TEST'
            or marker.get('manifest_sha256')!=digest(directory/'manifest.json')
            or (directory/'FAILED.json').exists()):
        raise ValueError('Missing/changed atomic completion evidence')
    manifest=_read_json(directory/'manifest.json')
    if not isinstance(manifest,dict) or manifest.get('schema_version')!=SCHEMA_VERSION:
        raise ValueError('Unsupported synthetic run manifest schema; legacy outputs need archived-code verification')
    if (manifest.get('status')!='COMPLETED_SYNTHETIC_ONLY' or manifest.get('data_admission')!='PENDING_REVIEW'
            or manifest.get('confirmatory_status')!='BLOCKED_CONFIRMATORY_TEST'
            or type(manifest.get('models_trained')) is not int or manifest['models_trained']!=0):
        raise ValueError('Invalid synthetic scope')
    run_id=manifest.get('run_id')
    if not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,100}',run_id) or run_id!=directory.name:
        raise ValueError('Synthetic run identity differs from its directory')
    _count(manifest.get('seed'),'seed',minimum=None)
    steps=_count(manifest.get('steps_per_scenario'),'steps per scenario',8)
    scenario_count=_count(manifest.get('scenario_count'),'scenario count',1)
    controller_count=_count(manifest.get('controller_count'),'controller count',1)
    comparison_rows=_count(manifest.get('comparison_rows'),'comparison rows',1)
    if controller_count!=len(CONTROLLERS) or comparison_rows!=scenario_count*controller_count:
        raise ValueError('Inconsistent declared synthetic comparison counts')
    try:created=datetime.fromisoformat(manifest['created_at_utc'])
    except (KeyError,TypeError,ValueError) as error:raise ValueError('Invalid synthetic creation timestamp') from error
    if created.tzinfo is None or created.utcoffset() is None:raise ValueError('Synthetic creation timestamp requires explicit timezone')
    if not isinstance(manifest.get('environment'),dict) or not manifest['environment']:
        raise ValueError('Missing synthetic environment evidence')
    source=manifest.get('source_sha256')
    _inventory(source,ROOT,'source')
    if source!=_source_hashes():raise ValueError('Current source inventory differs from synthetic run')
    _inventory(manifest.get('input_sha256'),ROOT,'input',required=(POLICY_INPUT,))
    policy=_read_json(ROOT/POLICY_INPUT)
    if policy.get('real_data_reviews')!={} or policy.get('confirmatory_status')!='BLOCKED_CONFIRMATORY_TEST':
        raise ValueError('Unexpected real-data governance state')
    artifacts=_inventory(manifest.get('artifact_sha256'),directory,'synthetic',required=_REQUIRED_ARTIFACTS)
    actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    if actual!=artifacts|{'manifest.json','COMPLETED.json'}:
        raise ValueError('Synthetic artifact inventory differs from on-disk membership')
    started=_read_json(directory/'STARTED.json')
    if started!={'status':'STARTED','data_kind':'SYNTHETIC_ONLY','run_id':run_id}:
        raise ValueError('Changed synthetic start identity')
    scenarios=_read_json(directory/'scenarios.json')
    if not isinstance(scenarios,list) or len(scenarios)!=scenario_count:
        raise ValueError('Synthetic scenario count differs from declared count')
    names=[];expected_traces=set();runs=[];fingerprints={};summary=[]
    for scenario in scenarios:
        if not isinstance(scenario,dict):raise ValueError('Invalid synthetic scenario record')
        name=scenario.get('name')
        if not isinstance(name,str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,100}',name) or name in names:
            raise ValueError('Invalid or duplicate synthetic scenario identity')
        names.append(name)
        if not isinstance(scenario.get('wind_kw'),list) or len(scenario['wind_kw'])!=steps:
            raise ValueError('Synthetic scenario observation denominator differs')
        for controller in CONTROLLERS:
            key=name+'__'+controller;relative='traces/'+key+'.json';expected_traces.add(relative)
            if relative not in artifacts:raise ValueError('Missing scenario/controller trace')
            run=_read_json(directory/relative)
            if (run.get('data_kind')!='SYNTHETIC_ONLY' or run.get('scenario')!=name
                    or run.get('controller')!=controller or run.get('seed')!=scenario.get('seed')):
                raise ValueError('Trace identity differs from its declared scenario/controller')
            rows,plans=run.get('rows'),run.get('plans')
            if not isinstance(rows,list) or not isinstance(plans,list) or len(rows)!=steps or len(plans)!=steps:
                raise ValueError('Trace interval or planning denominator differs')
            if run.get('wind_sha256')!=canonical_sha256(scenario['wind_kw']) or [r['wind_kw'] for r in rows]!=scenario['wind_kw']:
                raise ValueError('Trace wind differs from declared synthetic observations')
            metrics=summarize_trace(rows,BatteryConfig(**run['battery']),MPCConfig(**run['mpc_config']))
            _same_json(run.get('metrics'),metrics,'Saved synthetic metrics do not reproduce from trace')
            if (any(metrics[k] for k in ('soc_constraint_violations','power_constraint_violations','simultaneous_charge_discharge_events'))
                    or abs(metrics['energy_accounting_residual_kwh'])>TOLERANCE
                    or metrics['maximum_energy_update_residual_kwh']>TOLERANCE
                    or metrics['maximum_power_balance_residual_kw']>TOLERANCE):
                raise ValueError('Synthetic trace physical validation failed')
            runs.append(run);summary.append({'data_kind':'SYNTHETIC_ONLY','scenario':name,'controller':controller,**metrics})
            fingerprints[key]=canonical_sha256(reproducibility_payload(run))
    if artifacts!=_REQUIRED_ARTIFACTS|expected_traces or len(runs)!=comparison_rows:
        raise ValueError('Unexpected synthetic artifact or comparison membership')
    pairs=paired_comparisons(runs)
    _same_json(_read_json(directory/'metrics.json'),summary,'Saved metric table differs from authenticated traces')
    _same_json(_read_json(directory/'trace_fingerprints.json'),fingerprints,'Saved trace fingerprints do not reproduce')
    if manifest.get('comparison_fingerprint')!=canonical_sha256(fingerprints):
        raise ValueError('Synthetic comparison fingerprint does not reproduce')
    _same_json(_read_json(directory/'validation.json'),_validation_checks(runs),'Saved validation differs from authenticated traces')
    _check_csv(directory/'summary.csv',summary);_check_csv(directory/'paired_comparisons.csv',pairs)
    return manifest


def compare_runs(first,second):
    a,b=verify_run(first),verify_run(second)
    for key in ('seed','steps_per_scenario','source_sha256','input_sha256','environment'):
        if a[key]!=b[key]:raise ValueError('Reproduction inputs/environment differ')
    if a['comparison_fingerprint']!=b['comparison_fingerprint']:raise ValueError('Synthetic dispatch or non-timing metrics did not reproduce')
    return {'status':'REPRODUCED_EXCLUDING_TIMINGS','comparison_fingerprint':a['comparison_fingerprint'],'data_kind':'SYNTHETIC_ONLY'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('--run-id');run.add_argument('--seed',type=int,default=20261110);run.add_argument('--steps',type=int,default=24);run.add_argument('--output-root',type=Path)
    verify=sub.add_parser('verify');verify.add_argument('--run',required=True,type=Path)
    compare=sub.add_parser('compare');compare.add_argument('--first',required=True,type=Path);compare.add_argument('--second',required=True,type=Path)
    args=parser.parse_args(argv)
    if args.command=='run':
        directory,manifest=run_experiments(run_id=args.run_id,seed=args.seed,steps=args.steps,output_root=args.output_root)
        print(json.dumps({'status':manifest['status'],'run':directory.relative_to(ROOT).as_posix(),'comparison_rows':manifest['comparison_rows'],'confirmatory_status':manifest['confirmatory_status']}))
    elif args.command=='verify':print(json.dumps({'status':'VERIFIED_SYNTHETIC_ONLY','run_id':verify_run(args.run)['run_id']}))
    else:print(json.dumps(compare_runs(args.first,args.second)))
    return 0

if __name__=='__main__':raise SystemExit(main())
