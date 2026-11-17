"""Guarded development workflow; no confirmation or MPC execution path."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import re
import xml.sax.saxutils

from publication_v2.integrity import digest,inside,verify_preservation,verify_frozen
from publication_v2.protocol import Forecast,Residual,HORIZONS,validate_forecast
from publication_v2.runner import _atomic_json,_reject_redirect_ancestors
from .data import load_bundle,DatasetError
from .forecasting import MODEL_NAMES,fit_forecaster,save_forecaster,load_forecaster,matrix_sha256
from .conformal import CalibrationConfig,calibrate
from .metrics import evaluate_forecasts,evaluate_intervals
from .environment import capture_environment,validate_environment

SOURCE_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = SOURCE_ROOT/'publication_v2/stage2'


class WorkflowError(ValueError): pass


def environment() -> dict:
    result = capture_environment()
    validate_environment(result,result)
    return result


def preservation() -> dict:
    baseline=json.loads((PACKAGE/'preservation_baseline.json').read_text(encoding='utf-8'))
    return {'status':'pass','protected':verify_preservation(SOURCE_ROOT,baseline),'freeze':verify_frozen(SOURCE_ROOT)}


def source_hashes() -> dict:
    paths=[p for p in PACKAGE.rglob('*.py') if 'runs' not in p.parts and '__pycache__' not in p.parts]
    paths += [PACKAGE/name for name in ('config.json','preservation_baseline.json','requirements.txt','provenance_policy.json')]
    return {p.relative_to(SOURCE_ROOT).as_posix():digest(p) for p in sorted(paths)}


def _directory(root: Path, run_id: str) -> Path:
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,79}',run_id) or re.fullmatch(r'CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]',run_id.upper()):
        raise WorkflowError('A safe unique run ID is required')
    directory=root/'publication_v2/stage2/runs'/run_id
    _reject_redirect_ancestors(directory)
    directory.parent.mkdir(parents=True,exist_ok=True)
    directory.mkdir(exist_ok=False)
    return directory


def _config() -> dict:
    config=json.loads((PACKAGE/'config.json').read_text(encoding='utf-8'))
    if (config.get('stage')!=2 or config.get('scope')!='DEVELOPMENT_ONLY' or
        config.get('models')!=list(MODEL_NAMES) or config.get('horizons_minutes')!=list(HORIZONS) or
        config.get('confirmatory_status')!='BLOCKED_CONFIRMATORY_TEST'):
        raise WorkflowError('Only the locked development-only three-model/six-horizon protocol is supported')
    if not config.get('uncertainty_ablations') or len({a['name'] for a in config['uncertainty_ablations']})!=len(config['uncertainty_ablations']):
        raise WorkflowError('Distinct prespecified uncertainty ablations are required')
    return config


def _check_inputs(root: Path, hashes: dict) -> None:
    for relative, expected in hashes.items():
        if digest(inside(root,relative))!=expected: raise WorkflowError(f'Input changed during experiment: {relative}')


def _finish(directory: Path, status: str, identity: dict, *, input_hashes: dict, extra: dict) -> dict:
    preservation_after=preservation()
    _atomic_json(directory,'preservation_after.json',preservation_after)
    if source_hashes()!=identity['source_sha256'] or environment()!=identity['environment']:
        raise WorkflowError('Implementation or environment changed during the run')
    artifacts={p.relative_to(directory).as_posix():digest(p) for p in directory.rglob('*') if p.is_file()}
    manifest={'schema_version':'publication_v2.stage2.run.v1','stage':2,'scope':'DEVELOPMENT_ONLY','status':status,
              'confirmatory_status':'BLOCKED_CONFIRMATORY_TEST','input_sha256':input_hashes,
              'artifact_sha256':artifacts,**identity,**extra}
    _atomic_json(directory,'manifest.json',manifest)
    _atomic_json(directory,'COMPLETED.json',{'schema_version':'publication_v2.stage2.run.v1','stage':2,
        'status':status,'experiment_executed':extra['experiment_executed'],
        'confirmatory_status':'BLOCKED_CONFIRMATORY_TEST','manifest_sha256':digest(directory/'manifest.json')})
    return manifest


def _begin(root: Path, run_id: str) -> tuple[Path,dict,dict]:
    root=root.resolve(); config=_config()
    identity={'workspace_root':str(root),'implementation_root':str(SOURCE_ROOT),'source_sha256':source_hashes(),
              'environment':environment(),'created_utc':datetime.now(timezone.utc).isoformat(),'seed':config['seed']}
    directory=_directory(root,run_id)
    _atomic_json(directory,'STARTED.json',{'schema_version':'publication_v2.stage2.run.v1',
        'stage':2,'run_id':run_id,'scope':'DEVELOPMENT_ONLY'})
    try: _atomic_json(directory,'preservation_before.json',preservation())
    except BaseException as error:
        _failed(directory,error); raise
    return directory,identity,config


def _failed(directory: Path, error: BaseException) -> None:
    if not (directory/'COMPLETED.json').exists():
        _atomic_json(directory,'FAILED.json',{'status':'FAILED','error_type':type(error).__name__,'message':str(error),
            'admission_report':getattr(error,'report',{'status':'REJECTED','reason':str(error)})})


def preflight(run_id: str) -> tuple[Path,dict]:
    """Inventory existing unknown metadata; never relabel it as an eligible ledger."""
    directory,identity,config=_begin(SOURCE_ROOT,run_id)
    try:
        path=SOURCE_ROOT/'publication_v2/metadata.json'
        metadata=json.loads(path.read_text(encoding='utf-8'))
        dataset=metadata['dataset']
        checks={name:dataset[name] for name in ('upstream_dataset_version','timezone','measurement_window_semantics',
                                               'measurement_release_latency','licensing')}
        blockers=[{'code':'MISSING_'+name.upper(),'evidence':item} for name,item in checks.items() if item.get('value') is None]
        blockers += [{'code':'MISSING_ELIGIBLE_DEVELOPMENT_LEDGER','message':'Supply an authenticated source/receipt/feature/target ledger; existing naive CSVs are not automatically admitted.'}]
        if metadata['models']['historical_training_data_access_attestation']['value'] is None:
            blockers.append({'code':'UNATTESTED_HISTORICAL_FITTING','message':'Frozen model provenance cannot be reconstructed as an attestation.'})
        inputs={'publication_v2/metadata.json':digest(path)}
        _atomic_json(directory,'blockers.json',{'status':'BLOCKED_DEVELOPMENT_EXPERIMENT','blockers':blockers})
        _atomic_json(directory,'forecast_metrics.json',{'status':'NOT_RUN_BLOCKED_PROVENANCE','per_horizon':[
            {'model':m,'horizon_minutes':h,'n':None,'mae_kw':None,'rmse_kw':None,'rapid_mae_kw':None,'rapid_rmse_kw':None}
            for m in MODEL_NAMES for h in HORIZONS]})
        _atomic_json(directory,'uncertainty_metrics.json',{'status':'NOT_RUN_BLOCKED_PROVENANCE','per_horizon':[
            {'model':m,'method':a['name'],'horizon_minutes':h,'coverage':None,'rapid_coverage':None,'mean_width_kw':None,
             'floor_binding_fraction':None,'calibration_error':None} for m in MODEL_NAMES for a in config['uncertainty_ablations'] for h in HORIZONS]})
        _atomic_json(directory,'ablation_metrics.json',{'status':'NOT_RUN_BLOCKED_PROVENANCE','planned_variants':config['uncertainty_ablations'],
            'results':[],'reason':'No real-data fit, coverage comparison or ablation result can be computed without admitting eligible inputs.'})
        _readiness_figures(directory,blockers)
        _check_inputs(SOURCE_ROOT,inputs)
        manifest=_finish(directory,'BLOCKED_DEVELOPMENT_EXPERIMENT',identity,input_hashes=inputs,
            extra={'experiment_executed':False,'new_real_models_trained':0,'blockers':blockers,'research_metrics_available':False})
        return directory,manifest
    except BaseException as error: _failed(directory,error); raise


def _readiness_figures(directory: Path, blockers: list) -> None:
    """Original protocol/readiness diagrams: no invented forecasts or metric bars."""
    esc=xml.sax.saxutils.escape
    for name,title,labels in [
        ('data_readiness','Actual Stage 2 preflight — real experiments blocked',[item['code'] for item in blockers]),
        ('causal_contract','Normative causal contract — diagram, not measured telemetry',[
            'source event ≤ source receipt ≤ feature availability ≤ forecast origin',
            'origin ≤ issuance ≤ decision < origin + horizon',
            'calibration target < decision; observation and residual available by decision',
            'training/calibration/development targets separated by horizon-specific embargo',
            'BLOCKED_CONFIRMATORY_TEST persists; no new efficacy result'])]:
        height=110+42*len(labels)
        content=f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="{height}" viewBox="0 0 1080 {height}"><rect width="1080" height="{height}" fill="#101b2c"/><g font-family="sans-serif" fill="#edf3fa"><text x="30" y="43" font-size="22">{esc(title)}</text>'
        for i,label in enumerate(labels):
            content+=f'<circle cx="35" cy="{85+42*i}" r="5" fill="#e9a35b"/><text x="55" y="{91+42*i}" font-size="16">{esc(label)}</text>'
        content+='</g></svg>'
        (directory/f'{name}.svg').open('x',encoding='utf-8',newline='').write(content)


def run_development(dataset_path: Path,run_id: str,*,root: Path=SOURCE_ROOT,allow_synthetic: bool=False) -> tuple[Path,dict]:
    """Synthetic mode is an explicit Python testing API, absent from the real CLI."""
    directory,identity,config=_begin(root,run_id)
    try:
        bundle=load_bundle(dataset_path,root.resolve(),allow_synthetic=allow_synthetic)
        synthetic=bundle.dataset_kind=='SYNTHETIC_FIXTURE'
        _atomic_json(directory,'admission_report.json',bundle.admission_report)
        _check_inputs(root,bundle.input_hashes)
        x=bundle.features_for('train'); y=bundle.targets_for_fit()
        latest_training=max(o.target_time for s in bundle.partitions['train'] for o in s.observations)
        prediction_rows=[]; interval_rows=[]; diagnostics=[]; model_manifests={}
        for name in MODEL_NAMES:
            fitted=fit_forecaster(name,x,y,seed=config['seed'],hyperparameters=config['model_hyperparameters'][name])
            model_directory=directory/'models'/name
            save_forecaster(fitted,model_directory,training_provenance={
                'dataset_kind':bundle.dataset_kind,'scope':'DEVELOPMENT_ONLY','dataset_sha256':bundle.dataset_sha256,
                'input_sha256':bundle.input_hashes,'data_clock_fit_time':bundle.fit_time.isoformat(),
                'latest_training_target':latest_training.isoformat(),'fit_time_is_not_a_filesystem_mtime':True,
                'training_observations':len(x),'selection_on_scoring_outcomes':False})
            model_sha=digest(model_directory/'manifest.json');model_manifests[name]=model_sha
            frozen=load_forecaster(model_directory,expected_manifest_sha256=model_sha)
            calibration_predictions=frozen.predict(bundle.features_for('calibration'))
            history=[]
            for sample,predictions in zip(bundle.partitions['calibration'],calibration_predictions):
                for h,pred,obs in zip(HORIZONS,predictions,sample.observations):
                    validate_forecast(Forecast(sample.origin,sample.issued,sample.decision,obs.target_time,h,float(pred),
                        sample.features,model_sha,latest_training,bundle.fit_time,bundle.grid_anchor))
                    history.append(Residual(sample.origin,sample.issued,obs.target_time,h,float(pred),obs.value_kw,
                        obs.available_at,obs.residual_available_at,model_sha,latest_training,bundle.fit_time,bundle.grid_anchor))
            static_history=tuple(history)
            development_predictions=frozen.predict(bundle.features_for('development'))
            for sample,predictions in zip(bundle.partitions['development'],development_predictions):
                # Seal all uncertainty bounds BEFORE exposing this origin's scoring outcomes.
                sealed=[]
                for h,pred in zip(HORIZONS,predictions):
                    target_time=sample.origin+timedelta(minutes=h)
                    validate_forecast(Forecast(sample.origin,sample.issued,sample.decision,target_time,h,float(pred),sample.features,
                        model_sha,latest_training,bundle.fit_time,bundle.grid_anchor))
                    for ablation in config['uncertainty_ablations']:
                        cc=CalibrationConfig(alpha=config['alpha'],window=ablation['window'],half_life_minutes=ablation['half_life_minutes'],
                            floor_kw=ablation['floor_kw'],min_samples=config['min_calibration_samples'])
                        pool=static_history if ablation['method']=='static' else history
                        result=calibrate(pool,sample.decision,h,ablation['method'],model_sha,cc)
                        lower,upper=result.interval(float(pred))
                        sealed.append((h,ablation['name'],lower,upper,result))
                for h,pred,obs in zip(HORIZONS,predictions,sample.observations):
                    row={'model':name,'origin_time':sample.origin.isoformat(),'decision_time':sample.decision.isoformat(),
                        'target_time':obs.target_time.isoformat(),'horizon_minutes':h,'prediction_kw':float(pred),'actual_kw':obs.value_kw,
                        'actual_available_at':obs.available_at.isoformat(),'scored_at':max(obs.available_at,obs.previous_available_at,obs.residual_available_at).isoformat(),
                        'previous_target_time':obs.previous_target_time.isoformat(),'previous_actual_kw':obs.previous_value_kw,
                        'previous_actual_available_at':obs.previous_available_at.isoformat()}
                    prediction_rows.append(row)
                    for sealed_h,variant,lower,upper,result in sealed:
                        if sealed_h==h:
                            interval_rows.append({**row,'method':variant,'lower_kw':lower,'upper_kw':upper,'alpha':config['alpha'],
                                'floor_binding':result.floor_binding,'calibration_newest_target_time':result.newest_target_time.isoformat()})
                            diagnostics.append({'model':name,'origin_time':row['origin_time'],'horizon_minutes':h,'variant':variant,**result.as_dict()})
                    history.append(Residual(sample.origin,sample.issued,obs.target_time,h,float(pred),obs.value_kw,obs.available_at,
                        obs.residual_available_at,model_sha,latest_training,bundle.fit_time,bundle.grid_anchor))
        _require_full_panel(prediction_rows,len(bundle.partitions['development']))
        point=evaluate_forecasts(prediction_rows,rapid_threshold_kw=config['rapid_event_threshold_kw'])
        coverage=evaluate_intervals(interval_rows,expected_methods=tuple(a['name'] for a in config['uncertainty_ablations']),
                                    rapid_threshold_kw=config['rapid_event_threshold_kw'])
        label='SYNTHETIC_SOFTWARE_TEST_ONLY' if synthetic else 'RETROSPECTIVE_DEVELOPMENT_ONLY'
        for filename,payload in [('forecast_metrics.json',point),('uncertainty_metrics.json',coverage),
                                 ('predictions.json',{'rows':prediction_rows}),('intervals.json',{'rows':interval_rows}),
                                 ('calibration_diagnostics.json',{'rows':diagnostics})]:
            _atomic_json(directory,filename,{'interpretation':label,**payload})
        _atomic_json(directory,'ablation_metrics.json',{'interpretation':label,'variants':config['uncertainty_ablations'],
                                                       'per_horizon':coverage['per_horizon']})
        from .plots import research_figures
        research_figures(prediction_rows,interval_rows,point,coverage,directory,label)
        _check_inputs(root,bundle.input_hashes)
        _atomic_json(directory,'comparison_contract.json',{'same_training_features_sha256':matrix_sha256(x),
            'same_training_targets_sha256':matrix_sha256(y,targets=True),'training_rows':len(x),
            'calibration_rows':len(bundle.partitions['calibration']),'development_rows':len(bundle.partitions['development']),
            'models':list(MODEL_NAMES),'horizons':list(HORIZONS),'model_manifest_sha256':model_manifests})
        manifest=_finish(directory,'SYNTHETIC_WORKFLOW_COMPLETED' if synthetic else 'DEVELOPMENT_COMPLETED',identity,
            input_hashes=bundle.input_hashes,extra={'experiment_executed':True,'interpretation':label,
                'new_real_models_trained':0 if synthetic else 12,'research_metrics_available':not synthetic,
                'dataset_kind':bundle.dataset_kind})
        return directory,manifest
    except BaseException as error: _failed(directory,error); raise


def _require_full_panel(rows: list,origins: int) -> None:
    keys={(row['model'],row['origin_time'],row['horizon_minutes']) for row in rows}
    if len(rows)!=len(keys) or len(rows)!=len(MODEL_NAMES)*origins*len(HORIZONS):
        raise WorkflowError('Incomplete or duplicated joint six-horizon scoring panel')
    for model in MODEL_NAMES:
        if {r['horizon_minutes'] for r in rows if r['model']==model}!=set(HORIZONS):
            raise WorkflowError('Missing horizon in scoring panel')


def verify_run(directory: Path, *,root: Path=SOURCE_ROOT) -> dict:
    _reject_redirect_ancestors(directory)
    if not directory.resolve().is_relative_to((root/'publication_v2/stage2/runs').resolve()):
        raise WorkflowError('Run outside the isolated Stage2 namespace')
    for name in ('FAILED.json','COMPLETED.json','manifest.json'):
        inside(directory,name)  # Includes dangling symlinks and directory junctions.
    if (directory/'FAILED.json').exists() or not (directory/'COMPLETED.json').is_file():
        raise WorkflowError('Failed/partial run cannot be consumed')
    marker=json.loads((directory/'COMPLETED.json').read_text(encoding='utf-8'))
    if marker['manifest_sha256']!=digest(directory/'manifest.json'): raise WorkflowError('Completion/manifest identity mismatch')
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    _validate_completion_scope(manifest,marker)
    started=json.loads((directory/'STARTED.json').read_text(encoding='utf-8'))
    if (started.get('schema_version')!='publication_v2.stage2.run.v1' or started.get('stage')!=2 or
        started.get('scope')!='DEVELOPMENT_ONLY' or started.get('run_id')!=directory.name):
        raise WorkflowError('Started marker does not identify this development-only run')
    if marker['status']!=manifest['status'] or marker['experiment_executed'] is not manifest['experiment_executed']:
        raise WorkflowError('Completion scope differs from manifest')
    if manifest['source_sha256']!=source_hashes() or manifest['environment']!=environment():
        raise WorkflowError('Source or environment differs from authenticated run')
    _check_inputs(root,manifest['input_sha256'])
    for relative,expected in manifest['artifact_sha256'].items():
        if digest(inside(directory,relative))!=expected: raise WorkflowError(f'Run artifact changed: {relative}')
    preservation()
    return manifest


def _validate_completion_scope(manifest: dict,marker: dict) -> None:
    for obj in (manifest,marker):
        if (obj.get('schema_version')!='publication_v2.stage2.run.v1' or type(obj.get('stage')) is not int or obj.get('stage')!=2 or
            obj.get('confirmatory_status')!='BLOCKED_CONFIRMATORY_TEST'):
            raise WorkflowError('Invalid Stage2 schema/stage/confirmatory claim')
    if manifest.get('scope')!='DEVELOPMENT_ONLY': raise WorkflowError('Run scope is not development-only')
    status=manifest.get('status')
    if status=='BLOCKED_DEVELOPMENT_EXPERIMENT':
        if manifest.get('experiment_executed') is not False or manifest.get('research_metrics_available') is not False or manifest.get('new_real_models_trained')!=0 or not manifest.get('blockers'):
            raise WorkflowError('Blocked run falsely claims an experiment or results')
        required={'blockers.json','data_readiness.svg','causal_contract.svg'}
    elif status=='SYNTHETIC_WORKFLOW_COMPLETED':
        if (manifest.get('experiment_executed') is not True or manifest.get('research_metrics_available') is not False or
            manifest.get('new_real_models_trained')!=0 or manifest.get('dataset_kind')!='SYNTHETIC_FIXTURE' or
            manifest.get('interpretation')!='SYNTHETIC_SOFTWARE_TEST_ONLY'):
            raise WorkflowError('Synthetic run misrepresents dataset identity or research results')
        required={'predictions.json','intervals.json','calibration_diagnostics.json','comparison_contract.json','admission_report.json'}
    elif status=='DEVELOPMENT_COMPLETED':
        if (manifest.get('experiment_executed') is not True or manifest.get('research_metrics_available') is not True or
            manifest.get('new_real_models_trained')!=12 or manifest.get('dataset_kind')!='REAL_DEVELOPMENT' or
            manifest.get('interpretation')!='RETROSPECTIVE_DEVELOPMENT_ONLY'):
            raise WorkflowError('Completed development run has inconsistent scientific claims')
        required={'predictions.json','intervals.json','calibration_diagnostics.json','comparison_contract.json','admission_report.json'}
    else: raise WorkflowError('Unsupported completion status')
    required|={'STARTED.json','preservation_before.json','preservation_after.json','forecast_metrics.json','uncertainty_metrics.json','ablation_metrics.json'}
    if status!='BLOCKED_DEVELOPMENT_EXPERIMENT':
        required|={f'models/{model}/manifest.json' for model in MODEL_NAMES}
        required|={f'models/xgboost/h{h}.json' for h in range(1,7)}|{f'models/lightgbm/h{h}.txt' for h in range(1,7)}
        required|={f'{name}.{extension}' for name in ('forecast_errors','uncertainty_coverage','forecast_interval_example','conditional_coverage_width') for extension in ('png','pdf')}
    if not required.issubset(manifest.get('artifact_sha256',{})):
        raise WorkflowError('Completion omits required models, metrics, plots or lifecycle artifacts')
