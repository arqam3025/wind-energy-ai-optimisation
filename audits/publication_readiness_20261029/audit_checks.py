"""Read-only independent audit; writes only new evidence in its own directory."""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8',errors='replace')
def main():
    protected=[p for folder in ['scripts','tests','docs','documentation_backups','data','models','results'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    protected += [ROOT/'README.md',ROOT/'.gitignore',ROOT/'requirements.txt']
    snapshot={str(p.relative_to(ROOT)):sha(p) for p in protected}
    report={'protected_files':len(snapshot)}
    freeze=ROOT/'results/development_controller_freeze_manifest.json'
    assert sha(freeze)=='b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a'
    m=json.loads(freeze.read_text())
    frozen=list(m['source_files'].values())+[e for g in m['development_result_files'].values() for e in g.values()]
    assert all(sha(ROOT/e['path'])==e['sha256'] for e in frozen)
    report['freeze']={'sha256':sha(freeze),'verified_referenced_files':len(frozen),'created_utc':m['created_utc']}
    run=ROOT/'results/frozen_heldout/final_20261029'
    report['manifest_mismatches']={}
    for p in [run/'provenance.json',run/'release_manifest_v1.json',run/'release_manifest_v2.json']:
        data=json.loads(p.read_text())
        report['manifest_mismatches'][p.name]=[name for name,h in data['sha256'].items() if sha(ROOT/name)!=h]
    schedule=pd.read_csv(ROOT/'results/evaluation_schedule.csv')
    valid=schedule.loc[schedule.evaluation_role.eq('evaluation'),'block_id'].astype(int).tolist()
    assert 6 not in valid and len(valid)==49
    blocks={int(b):pd.read_csv(ROOT/f'data/processed/evaluation_block_{b}.csv',parse_dates=['timestamp']) for b in schedule.block_id}
    calib=pd.read_csv(ROOT/'results/multistep_calibration_split.csv',parse_dates=['timestamp'])
    dev=pd.concat([pd.read_csv(ROOT/f'data/processed/controller_development_blocks/development_block_{b}.csv',parse_dates=['timestamp']) for b in range(1,19)],ignore_index=True)
    history=pd.concat([calib,dev,*blocks.values()],ignore_index=True).sort_values('timestamp').reset_index(drop=True)
    assert not history.timestamp.duplicated().any()
    raw=pd.read_csv(ROOT/'data/raw/T1.csv')
    raw.index=pd.to_datetime(raw['Date/Time'],format='%d %m %Y %H:%M')
    measured=raw['LV ActivePower (kW)'].clip(lower=0)
    # Constants read structurally; quantile selection implemented independently.
    uncertainty=ast.parse((ROOT/'scripts/causal_one_sided_uncertainty.py').read_text())
    floors=None
    for node in uncertainty.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STATIC_FLOORS_KW' for t in node.targets):
            floors=np.array(ast.literal_eval(node.value.args[0]))
    assert floors is not None
    margins_error=0.; target_checks=0; physical_checks=0; outcomes=[]; no_battery=[]
    horizon_origins=history.timestamp.to_numpy()
    fixed_quantiles=[]; signed_quantiles=[]
    rank=int(np.ceil((len(calib)+1)*.9))
    fixed_table=pd.read_csv(ROOT/'results/multistep_uncertainty_calibration_split.csv')
    for h in range(1,7):
        errors=(calib[f'xgboost_h{h}_kw']-calib[f'actual_h{h}_kw']).to_numpy()
        fixed_quantiles.append(float(np.sort(np.abs(errors))[rank-1]))
        signed_quantiles.append(float(np.sort(errors)[rank-1]))
    np.testing.assert_allclose(fixed_quantiles,fixed_table.calibration_quantile_kw,atol=1e-8,rtol=0)
    for b in valid:
        block=blocks[b]
        assert len(block)==144 and block.timestamp.diff().iloc[1:].eq(pd.Timedelta(minutes=10)).all()
        assert not dev.timestamp.between(block.timestamp.min()-pd.Timedelta(minutes=60),block.timestamp.max()+pd.Timedelta(minutes=60)).any()
        wind=np.maximum(0,block.actual_h1_kw.to_numpy())
        initial=max(0,float(block.current_power_kw.iloc[0]))
        baseline=np.abs(np.diff(np.r_[initial,wind]))
        no_battery.append({'block_id':b,'violations':int(np.count_nonzero(baseline>200.001)),'exceedance_kw':float(np.maximum(0,baseline-200).sum())})
        adaptive=pd.read_csv(run/'adaptive_one_sided'/f'adaptive_charging_mpc_block_{b}_weight_0p500.csv')
        for h in range(1,7):
            actual=measured.reindex(block.timestamp+pd.Timedelta(minutes=10*h)).to_numpy()
            np.testing.assert_allclose(actual,block[f'actual_h{h}_kw'],atol=.001,rtol=0)
            target_checks+=len(actual)
            targets=horizon_origins+np.timedelta64(10*h,'m')
            errors=(history[f'xgboost_h{h}_kw']-history[f'actual_h{h}_kw']).to_numpy()
            for i,t in enumerate(block.timestamp):
                end=np.searchsorted(targets,np.datetime64(t),'left')
                assert end>=144
                chosen=slice(end-144,end)
                assert targets[end-1]<np.datetime64(t)
                q=float(np.sort(errors[chosen])[130])
                post=int(np.count_nonzero(horizon_origins[chosen]>=np.datetime64('2018-10-31T16:50')))
                fallback=t>=pd.Timestamp('2018-10-31 16:50') and post<72
                margin=floors[h-1] if fallback else max(q,floors[h-1])
                margins_error=max(margins_error,abs(margin-adaptive.loc[i,f'adaptive_margin_h{h}_kw']))
        for kind in ['fixed','adaptive_one_sided']:
            d=pd.read_csv(run/kind/f'adaptive_charging_mpc_block_{b}_weight_0p500.csv')
            assert len(d)==144
            assert (pd.to_datetime(d.timestamp).to_numpy()==(block.timestamp+pd.Timedelta(minutes=10)).to_numpy()).all()
            charge=d.charge_kw.to_numpy(); discharge=d.discharge_kw.to_numpy(); curtail=d.curtailment_kw.to_numpy(); export=d.grid_export_kw.to_numpy()
            energy=d.soc_percent.to_numpy()*20; before=np.r_[1000,energy[:-1]]
            np.testing.assert_allclose(energy,before+(charge*.95-discharge/.95)/6,atol=1e-5,rtol=0)
            np.testing.assert_allclose(wind-charge+discharge-curtail,export,atol=1e-6,rtol=0)
            assert energy.min()>=800-1e-5 and energy.max()<=1800+1e-5
            assert np.minimum(charge,discharge).max()<1e-5
            assert min(charge.min(),discharge.min(),export.min(),curtail.min())>=-1e-6
            assert max(charge.max(),discharge.max())<=1000+1e-5 and (charge+curtail<=wind+1e-5).all()
            ramps=np.abs(np.diff(np.r_[initial,export])); delta=energy[-1]-1000
            loss=float((.05*charge+(1/.95-1)*discharge).sum()/6)
            assert abs(wind.sum()/6-export.sum()/6-curtail.sum()/6-loss-delta)<1e-4
            outcomes.append(dict(block_id=b,controller=kind,throughput_kwh=float((charge+discharge).sum()/6),ramp_exceedance_kw=float(np.maximum(0,ramps-200).sum()),ramp_violations=int((ramps>200.001).sum()),loss_kwh=loss,export_kwh=float(export.sum()/6),adjusted_export_kwh=float(export.sum()/6+(.95*delta if delta>=0 else delta/.95))))
            physical_checks+=1
    assert margins_error<1e-6
    df=pd.DataFrame(outcomes); totals=df.groupby('controller').sum(numeric_only=True).drop(columns='block_id')
    f=totals.loc['fixed'];a=totals.loc['adaptive_one_sided'];base=pd.DataFrame(no_battery).sum()
    report['independent_recalculation']={'totals':totals.to_dict('index'),'throughput_reduction_percent':float(100*(1-a.throughput_kwh/f.throughput_kwh)),
        'exceedance_reduction_percent':float(100*(1-a.ramp_exceedance_kw/f.ramp_exceedance_kw)), 'fewer_violations':int(f.ramp_violations-a.ramp_violations),
        'raw_target_checks':target_checks,'physical_controller_blocks':physical_checks,'margin_max_error_kw':margins_error,
        'no_battery':{'violations':int(base.violations),'exceedance_kw':float(base.exceedance_kw)},
        'adaptive_vs_no_battery_exceedance_increase_percent':float(100*(a.ramp_exceedance_kw/base.exceedance_kw-1)),
        'fixed_vs_no_battery_exceedance_increase_percent':float(100*(f.ramp_exceedance_kw/base.exceedance_kw-1))}
    report['calibration']={'samples':len(calib),'last_h60_target':str(calib.timestamp.max()+pd.Timedelta(minutes=60)),
        'fixed_reconstructed':fixed_quantiles,'signed_90pct_reconstructed':signed_quantiles,'adaptive_floors':floors.tolist()}
    # Current model inference only: never fit or save models.
    from xgboost import XGBRegressor
    features=pd.read_csv(ROOT/'data/processed/wind_multistep_features.csv',parse_dates=['timestamp']).set_index('timestamp')
    origins=pd.concat([blocks[b] for b in valid]).reset_index(drop=True)
    columns=['power_kw','wind_speed','wind_direction',*[f'power_lag_{n}min' for n in [10,20,30,60]],*[f'wind_lag_{n}min' for n in [10,20,30,60]],'power_change_10min','wind_change_10min','power_mean_40min']
    selected=features.loc[origins.timestamp,columns]
    max_model_error=[]
    for h in range(1,7):
        model=XGBRegressor();model.load_model(ROOT/f'models/wind_xgboost_h{h}.json')
        predicted=np.maximum(0,model.predict(selected))
        max_model_error.append(float(np.max(np.abs(predicted-origins[f'xgboost_h{h}_kw'].to_numpy()))))
    report['current_model_vs_stored_forecast_max_errors_kw']=max_model_error
    feature_errors={}
    current=raw['LV ActivePower (kW)'].reindex(origins.timestamp).to_numpy()
    feature_errors['power_kw']=float(np.max(np.abs(current-selected.power_kw)))
    for n in [10,20,30,60]:
        for field,source in [('power','LV ActivePower (kW)'),('wind','Wind Speed (m/s)')]:
            expected=raw[source].reindex(origins.timestamp-pd.Timedelta(minutes=n)).to_numpy()
            feature_errors[f'{field}_lag_{n}min']=float(np.nanmax(np.abs(expected-selected[f'{field}_lag_{n}min'].to_numpy())))
    for name,source in [('wind_speed','Wind Speed (m/s)'),('wind_direction','Wind Direction (°)')]:
        feature_errors[name]=float(np.max(np.abs(raw[source].reindex(origins.timestamp).to_numpy()-selected[name].to_numpy())))
    for field,name in [('power','power_kw'),('wind','wind_speed')]:
        feature_errors[f'{field}_change_10min']=float(np.max(np.abs(selected[f'{field}_change_10min']-(selected[name]-selected[f'{field}_lag_10min']))))
    feature_errors['power_mean_40min']=float(np.max(np.abs(selected.power_mean_40min-selected[['power_kw','power_lag_10min','power_lag_20min','power_lag_30min']].mean(axis=1))))
    report['causal_feature_raw_lookup_max_errors']=feature_errors
    # Secret checks report paths only; never print candidate secret material.
    patterns={'aws_access_key':r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b','github_token':r'\bgh[pousr]_[A-Za-z0-9]{30,}\b','private_key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----','openai_key':r'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b'}
    scan_paths=set(git('ls-files').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
    matches=[]
    for name in scan_paths:
        p=ROOT/name
        if p.is_file() and p.suffix.lower() in ['.py','.md','.txt','.json','.csv','.yml','.yaml','.env']:
            value=p.read_text(encoding='utf-8',errors='replace')
            for label,pattern in patterns.items():
                if re.search(pattern,value):matches.append({'path':name,'pattern':label})
    historical=[]
    objects=git('rev-list','--objects','--all').splitlines()
    blob_ids=[line.split(' ',1) for line in objects if ' ' in line]
    for oid,name in blob_ids:
        if Path(name).suffix.lower() not in ['.py','.md','.txt','.json','.csv','.yml','.yaml','.env']:continue
        value=git('cat-file','-p',oid)
        for label,pattern in patterns.items():
            if re.search(pattern,value):historical.append({'path':name,'object':oid,'pattern':label})
    report['git']={'head':git('rev-parse','HEAD').strip(),'untracked_count':len(git('ls-files','--others','--exclude-standard').splitlines()),
        'secret_pattern_matches':matches,'history_secret_pattern_matches':historical,
        'tracked_data_models_results':[p for p in git('ls-files').splitlines() if p.startswith(('data/','models/','results/'))],
        'historical_sensitive_paths':[name for oid,name in blob_ids if name.startswith(('.aws/','.env','data/raw/','models/'))]}
    assert all(sha(ROOT/name)==expected for name,expected in snapshot.items()),'Protected artifact changed'
    report['protected_files_unchanged']=True
    with (OUT/'independent_evidence.json').open('x',encoding='utf-8') as handle:json.dump(report,handle,indent=2)
    with (OUT/'protected_sha256_before_after.json').open('x',encoding='utf-8') as handle:json.dump(snapshot,handle,indent=2)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
