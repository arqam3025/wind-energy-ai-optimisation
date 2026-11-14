"""Explicit synthetic clocks, causal forecasts and actual Stage 2 calibration.

No fitted model is represented here. Descriptor hashes identify announced rules,
not authenticated real models. The native Residual training-cutoff field carries
an explicitly labelled synthetic rule-specification cutoff solely for API reuse.
The announced-perfect benchmark evaluates a public deterministic forcing recipe;
it never accepts an array of future realised observations.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import math
import random

from publication_v2.protocol import HORIZONS, Residual
from publication_v2.stage2.conformal import CalibrationConfig, calibrate
from .adapter import SCHEMA, TARGET_SEMANTICS, SyntheticRegistry, canonical_sha256

START = datetime(2032, 1, 1, tzinfo=timezone.utc)
STEP = timedelta(minutes=10)
CUTOFF_SEMANTICS = 'SIMULATED_RULE_SPECIFICATION_CUTOFF_NOT_TRAINING'
MODES = ('announced_perfect', 'persistence', 'biased', 'noisy')
PROFILES = ('stable', 'gradual', 'rapid', 'oscillatory')
FAULTS = ('missing', 'stale', 'future_generation', 'future_availability',
          'unsupported_model', 'invalid_calibration', 'stale_calibration',
          'invalid_bounds', 'invalid_horizon')


@dataclass(frozen=True)
class ScenarioSpec:
    episode_name: str
    profile: str = 'rapid'
    forecast_mode: str = 'persistence'
    calibration_method: str = 'rolling'
    seed: int = 20320101
    steps: int = 16
    initial_soc: float = .65
    bias_kw: float = 0.
    forecast_noise_kw: float = 0.
    drift_at: int | None = None
    drift_bias_kw: float = 0.
    faults: tuple[tuple[int, str], ...] = ()
    warmup_origins: int = 64

    def __post_init__(self):
        if not isinstance(self.episode_name, str) or not self.episode_name or self.episode_name.strip() != self.episode_name:
            raise ValueError('Explicit synthetic episode name required')
        if self.profile not in PROFILES or self.forecast_mode not in MODES or self.calibration_method not in ('static','rolling','weighted'):
            raise ValueError('Unsupported synthetic profile, forecast rule or calibration method')
        if type(self.seed) is not int or type(self.steps) is not int or self.steps < 8 or type(self.warmup_origins) is not int or self.warmup_origins < 64:
            raise ValueError('Integer seed, >=8 intervals and >=64 warm-up origins required')
        for v in (self.initial_soc,self.bias_kw,self.forecast_noise_kw,self.drift_bias_kw):
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
                raise ValueError('Finite synthetic parameters required')
        if not .4 <= self.initial_soc <= .9 or self.forecast_noise_kw < 0:
            raise ValueError('Invalid synthetic SOC or forecast noise')
        if self.drift_at is not None and (type(self.drift_at) is not int or not 0 <= self.drift_at < self.steps):
            raise ValueError('Drift index must be a prespecified scored interval')
        if self.forecast_mode == 'announced_perfect' and (self.bias_kw != 0 or self.forecast_noise_kw != 0 or self.drift_bias_kw != 0):
            raise ValueError('Announced-perfect benchmark cannot contain forecast perturbations')
        if type(self.faults) is not tuple:
            raise ValueError('Immutable prespecified fault schedule required')
        seen=set()
        for fault in self.faults:
            if type(fault) is not tuple or len(fault)!=2:
                raise ValueError('Invalid synthetic fault schedule')
            index,kind=fault
            if type(index) is not int or not 0<=index<self.steps or index in seen or kind not in FAULTS:
                raise ValueError('Invalid or duplicate synthetic fault')
            if kind=='stale_calibration' and index<7:
                raise ValueError('A stale-calibration fault needs >=7 intervals to reuse a genuinely old registered artifact')
            seen.add(index)

    @property
    def name(self):
        return self.episode_name


def forcing(spec: ScenarioSpec, interval_index: int) -> float:
    """Public preannounced deterministic interval-mean forcing, never SCADA.

    interval i covers [START+10*i, START+10*(i+1)) minutes. The runner calls this
    simulation-source function only after dispatch; the perfect rule separately
    evaluates this same announced recipe, not an outcome vector.
    """
    if not isinstance(spec,ScenarioSpec) or type(interval_index) is not int:
        raise ValueError('Explicit synthetic source specification and integer index required')
    if interval_index < 0:
        return 1000.
    if spec.profile == 'stable':
        return 1000.
    if spec.profile == 'gradual':
        return 1000.+min(700.,25.*interval_index)
    if spec.profile == 'rapid':
        return (1000.,1800.,400.,1500.)[min(3,interval_index//max(2,spec.steps//4))]
    return max(0.,1000.+500.*math.sin(interval_index*.9))


def _serial(value):
    if isinstance(value,datetime): return value.isoformat()
    if isinstance(value,dict): return {k:_serial(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [_serial(v) for v in value]
    return value


class SyntheticStream:
    """Issue -> seal dispatch -> observe; future outcomes are never an input.

    Warm-up is a chronological synthetic replay, not fitted-model training.
    Static membership is fixed before the first scored decision. Adaptive
    alternatives share the same released residual candidates and last-48 window.
    All operational clocks explicitly assume zero synthetic latency.
    """
    def __init__(self,spec:ScenarioSpec):
        if not isinstance(spec,ScenarioSpec): raise ValueError('ScenarioSpec required')
        self.spec=spec
        self.clock_start=START
        self.config=CalibrationConfig(alpha=.1,window=48,half_life_minutes=1440.,floor_kw=0.,min_samples=30)
        self._source_descriptor={'kind':'PREANNOUNCED_SYNTHETIC_INTERVAL_MEAN_RECIPE_V1',
            'profile':spec.profile,'seed':spec.seed,'steps':spec.steps,
            'start':START.isoformat(),'step_minutes':10,'warmup_origins':spec.warmup_origins,
            'scoring_tail_intervals':5,'units':'kW'}
        self.scenario_sha256=canonical_sha256(self._source_descriptor)
        self.source_id='SIMULATED_FORCING_'+self.scenario_sha256[:16]
        self.cohort_id='SIMULATED_COHORT_'+self.scenario_sha256[:16]
        self.rule_cutoff=START-STEP*(spec.warmup_origins+2)
        self.model_available_at=self.rule_cutoff
        parameters={'forecast_mode':spec.forecast_mode,'seed':spec.seed,'bias_kw':spec.bias_kw,
            'forecast_noise_kw':spec.forecast_noise_kw,'drift_at':spec.drift_at,
            'drift_bias_kw':spec.drift_bias_kw,'forcing_recipe':self._source_descriptor if spec.forecast_mode=='announced_perfect' else None}
        self.model_id='SIMULATED_RULE_'+canonical_sha256([parameters,self.source_id,self.rule_cutoff.isoformat()])[:16]
        self.model_version='1'
        required=[] if spec.forecast_mode=='announced_perfect' else ['last_released_generation_kw']
        self.model_descriptor={'id':self.model_id,'version':self.model_version,
            'identity_kind':'SYNTHETIC_RULE_DESCRIPTOR','rule':'synthetic_rule_v1',
            'parameters':parameters,'required_inputs':required,
            'access_mode':'PREANNOUNCED_DETERMINISTIC_FORCING' if spec.forecast_mode=='announced_perfect' else 'PAST_RELEASED_OBSERVATIONS_ONLY',
            'source_id':self.source_id,'cohort_id':self.cohort_id,'scenario_sha256':self.scenario_sha256,
            'units':'kW','quantity':'measured_wind_generation','target_semantics':TARGET_SEMANTICS,
            'available_at':self.model_available_at.isoformat(),'rule_specification_cutoff':self.rule_cutoff.isoformat(),
            'fitting_status':'NOT_FITTED_SYNTHETIC_RULE','actual_fitting_cutoff':None,
            'residual_cutoff_semantics':CUTOFF_SEMANTICS}
        self.model_sha256=canonical_sha256(self.model_descriptor)
        self.config_id='SIMULATED_CALIBRATION_'+spec.calibration_method+'_V1'
        cfg={'config_id':self.config_id,'version':'1','method':spec.calibration_method,
            'parameters':asdict(self.config),'source_id':self.source_id,'cohort_id':self.cohort_id,
            'model_id':self.model_id,'model_version':self.model_version,
            'model_descriptor_sha256':self.model_sha256,'available_at':self.model_available_at.isoformat()}
        cohort={'cohort_id':self.cohort_id,'source_id':self.source_id,'scenario_sha256':self.scenario_sha256,
            'study_role':'SYNTHETIC_DEVELOPMENT','admission':'SYNTHETIC_ONLY','data_kind':'SYNTHETIC',
            'units':'kW','quantity':'measured_wind_generation','target_semantics':TARGET_SEMANTICS}
        self._models={self.model_id:deepcopy(self.model_descriptor)}
        self._cohorts={self.cohort_id:cohort}
        self._configs={self.config_id:cfg}
        self._artifacts={}
        self.registry=SyntheticRegistry(self._models,self._cohorts,self._configs,self._artifacts)
        self._observed={i:forcing(spec,i-1) for i in range(-spec.warmup_origins-6,-spec.warmup_origins+1)}
        self._residuals=[]
        self._pending=[]
        self._forecast_records=[]
        self._packet_cache={}
        self._next_index=0
        self._issued_index=None
        for i in range(-spec.warmup_origins,0):
            points=self._points(i)
            self._queue(i,points,record=False)
            self._record_observation(i,forcing(spec,i))
        self.initial_history_kw=tuple(self._observed[i] for i in range(-5,1))
        self._static={h:tuple(r for r in self._residuals if r.horizon_minutes==h and r.target_time<START)[-48:] for h in HORIZONS}

    def _points(self,index):
        if self.spec.forecast_mode=='announced_perfect':
            return tuple(forcing(self.spec,index+j) for j in range(6))
        last=self._observed[index]
        bias=self.spec.bias_kw
        if self.spec.drift_at is not None and index>=self.spec.drift_at:
            bias+=self.spec.drift_bias_kw
        rng=random.Random(self.spec.seed+104729*(index+self.spec.warmup_origins+1))
        return tuple(max(0.,last+bias+rng.gauss(0.,self.spec.forecast_noise_kw)) for _ in HORIZONS)

    def _queue(self,index,points,*,record):
        origin=START+STEP*index
        for h,p in zip(HORIZONS,points):
            self._pending.append((index,index+h//10,h,float(p)))
            if record:
                self._forecast_records.append({'origin_time':origin.isoformat(),'decision_time':origin.isoformat(),
                    'target_time':(origin+timedelta(minutes=h)).isoformat(),'horizon_minutes':h,
                    'prediction_kw':float(p),'model':self.model_id,'model_sha256':self.model_sha256})

    def _record_observation(self,index,value):
        endpoint=index+1
        target=START+STEP*endpoint
        self._observed[endpoint]=float(value)
        remaining=[]
        for origin_index,target_index,h,p in self._pending:
            if target_index==endpoint:
                origin=START+STEP*origin_index
                self._residuals.append(Residual(origin,origin,target,h,p,float(value),target,target,
                    self.model_sha256,self.rule_cutoff,self.model_available_at,START))
            elif target_index>endpoint:
                remaining.append((origin_index,target_index,h,p))
            else:
                raise ValueError('Synthetic observation release skipped a pending target')
        self._pending=remaining

    @property
    def forecast_records(self):
        return deepcopy(self._forecast_records)

    @property
    def outcome_ledger(self):
        return [{'target_time':(START+STEP*i).isoformat(),'actual_available_at':(START+STEP*i).isoformat(),
            'actual_kw':v,'interval_index':i-1} for i,v in sorted(self._observed.items())]

    @property
    def residual_records(self):
        return tuple(self._residuals)

    def packet(self,index:int):
        if type(index) is not int or index!=self._next_index or not 0<=index<self.spec.steps:
            raise ValueError('Forecast issuance must follow the explicit sequential decision clock')
        if index in self._packet_cache: return deepcopy(self._packet_cache[index])
        issue=START+STEP*index
        points=self._points(index)
        horizons=[]
        for h,p in zip(HORIZONS,points):
            records=self._static[h] if self.spec.calibration_method=='static' else tuple(r for r in self._residuals if r.horizon_minutes==h and r.target_time<issue and r.residual_available_at<=issue)
            result=calibrate(records,issue,h,self.spec.calibration_method,self.model_sha256,self.config)
            lower,upper=result.interval(p)
            artifact={'config_id':self.config_id,'version':'1','method':self.spec.calibration_method,
                'generated_at':issue.isoformat(),'available_at':issue.isoformat(),'result':result.as_dict(),
                'residuals':[_serial(asdict(r)) for r in records],'source_id':self.source_id,
                'cohort_id':self.cohort_id,'model_id':self.model_id,'model_version':self.model_version,
                'model_descriptor_sha256':self.model_sha256}
            artifact_hash=canonical_sha256(artifact)
            self._artifacts[artifact_hash]=deepcopy(artifact)
            horizons.append({'horizon_minutes':h,'target_time':(issue+timedelta(minutes=h)).isoformat(),
                'point_kw':float(p),'lower_kw':float(lower),'upper_kw':float(upper),
                'calibration':{**artifact,'artifact_sha256':artifact_hash}})
        self.registry=SyntheticRegistry(self._models,self._cohorts,self._configs,self._artifacts)
        feature_inputs=[] if self.spec.forecast_mode=='announced_perfect' else [
            {'name':'last_released_generation_kw','value':self._observed[index],
             'source_times':[issue.isoformat()],'source_available_ats':[issue.isoformat()],
             'available_at':issue.isoformat()}]
        model_fields=('id','version','identity_kind','available_at','rule_specification_cutoff',
            'fitting_status','actual_fitting_cutoff','residual_cutoff_semantics')
        packet={'schema':SCHEMA,'packet_id':'SIMULATED_PACKET_'+canonical_sha256([self.model_sha256,self.spec.calibration_method,index])[:24],
            'study_role':'SYNTHETIC_DEVELOPMENT','source_id':self.source_id,'cohort_id':self.cohort_id,
            'scenario_sha256':self.scenario_sha256,'admission':'SYNTHETIC_ONLY','data_kind':'SYNTHETIC',
            'units':'kW','quantity':'measured_wind_generation','target_semantics':TARGET_SEMANTICS,
            'clock_assumption':'SYNTHETIC_ZERO_LATENCY','forecast_origin':issue.isoformat(),
            'issue_time':issue.isoformat(),'generated_at':issue.isoformat(),'available_at':issue.isoformat(),
            'model':{**{k:self.model_descriptor[k] for k in model_fields},'descriptor_sha256':self.model_sha256},
            'feature_inputs':feature_inputs,'horizons':horizons,'alpha':self.config.alpha}
        fault=dict(self.spec.faults).get(index)
        if fault is None:
            self._queue(index,points,record=True)
        stale_artifacts=None
        if fault=='stale_calibration':
            original=self._packet_cache.get(0)
            if original is None:
                raise ValueError('A genuine registered earlier calibration artifact is required for staleness injection')
            stale_artifacts=[row['calibration'] for row in original['horizons']]
        packet=apply_fault(packet,fault,issue,stale_artifacts=stale_artifacts) if fault else packet
        self._issued_index=index
        self._packet_cache[index]=deepcopy(packet)
        return deepcopy(packet)

    def observe(self,index:int,actual_kw:float):
        """Release an outcome only after its action; tail observations may finish scoring."""
        if type(index) is not int or index!=self._next_index or index>=self.spec.steps+5 or (index<self.spec.steps and self._issued_index!=index):
            raise ValueError('Observe requires the next sealed decision (or prespecified five-step scoring tail)')
        if isinstance(actual_kw,bool) or not isinstance(actual_kw,(int,float)) or not math.isfinite(actual_kw) or actual_kw<0:
            raise ValueError('Finite nonnegative synthetic outcome required')
        self._record_observation(index,float(actual_kw))
        self._next_index=index+1
        self._issued_index=None


def apply_fault(packet,fault,issue,*,stale_artifacts=None):
    """Fault injection changes supplied packets, never their trusted registries."""
    packet=deepcopy(packet)
    if fault=='missing': return None
    if fault=='stale':
        for field in ('forecast_origin','issue_time','generated_at','available_at'):
            packet[field]=(issue-STEP).isoformat()
    elif fault=='future_generation': packet['generated_at']=(issue+timedelta(seconds=1)).isoformat()
    elif fault=='future_availability': packet['available_at']=(issue+timedelta(seconds=1)).isoformat()
    elif fault=='unsupported_model': packet['model']['id']='SIMULATED_UNREGISTERED_MODEL'
    elif fault=='invalid_calibration': packet['horizons'][0]['calibration']['result']['margin_kw']+=1.
    elif fault=='stale_calibration':
        if not isinstance(stale_artifacts,list) or len(stale_artifacts)!=6:
            raise ValueError('Genuinely old registered artifacts required; timestamps cannot be fabricated')
        for row,artifact in zip(packet['horizons'],stale_artifacts):
            row['calibration']=deepcopy(artifact)
    elif fault=='invalid_bounds': packet['horizons'][0]['lower_kw']=packet['horizons'][0]['upper_kw']+1.
    elif fault=='invalid_horizon': packet['horizons'][0]['horizon_minutes']=5
    else: raise ValueError('Unsupported prespecified synthetic fault')
    return packet
