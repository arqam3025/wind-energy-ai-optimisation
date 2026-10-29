"""Paired daily moving-block uncertainty, preserving original segment boundaries.

This is supplementary retrospective inference, not restoration of test blindness.
Small/nonstationary segments limit coverage; alternative lengths are all reported.
"""
from pathlib import Path
from typing import Sequence
import hashlib
import json
import numpy as np
import pandas as pd
from .protocol import ProtocolError, require_new_output_directory

METRICS=('throughput_kwh','conversion_losses_kwh','ramp_exceedance_kw',
         'ramp_violations','export_kwh','terminal_adjusted_export_kwh')

def moving_block_indices(segment_ids: Sequence[int], replicates: int,
                         block_length: int, seed: int) -> np.ndarray:
    """Non-circular blocks sampled within each segment; fixed original exposure."""
    labels=np.asarray(segment_ids)
    if labels.ndim!=1 or len(labels)==0 or replicates<2 or block_length<1:
        raise ProtocolError('Need nonempty segment labels, at least two draws and positive length.')
    rng=np.random.default_rng(seed)
    samples=np.empty((replicates,len(labels)),dtype=int)
    seen=[]
    for value in labels:
        if not seen or value!=seen[-1]:seen.append(value)
    if len(set(seen))!=len(seen):
        raise ProtocolError('A segment must be one contiguous chronological group.')
    for label in seen:
        positions=np.flatnonzero(labels==label)
        size=len(positions);length=min(block_length,size)
        starts=rng.integers(0,size-length+1,size=(replicates,int(np.ceil(size/length))))
        local=(starts[:,:,None]+np.arange(length)[None,None,:]).reshape(replicates,-1)[:,:size]
        samples[:,positions]=positions[local]
    return samples

def recentered_basic_interval(point: float, draws: np.ndarray) -> tuple[float,float]:
    values=np.asarray(draws,dtype=float)
    if not np.isfinite(point) or not np.isfinite(values).all():
        return float('nan'),float('nan')
    deviations=values-values.mean()
    low,high=np.quantile(deviations,[.025,.975])
    return float(point-high),float(point-low)

def paired_uncertainty(metrics: pd.DataFrame,schedule: pd.DataFrame,*,
        reference: str='fixed',comparison: str='adaptive_one_sided',
        lengths: Sequence[int]=(2,3,7),replicates: int=10000,seed: int=20261029
    ) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    required={'block_id','controller',*METRICS}
    if not required.issubset(metrics):raise ProtocolError('Incomplete paired metric schema.')
    if metrics.duplicated(['block_id','controller']).any():raise ProtocolError('Duplicate case/block row.')
    target=schedule.loc[schedule.evaluation_role.eq('evaluation')].copy()
    target['start_timestamp']=pd.to_datetime(target.start_timestamp)
    target=target.sort_values('start_timestamp')
    block_ids=target.block_id.to_numpy()
    a=metrics.loc[metrics.controller.eq(comparison)].set_index('block_id')
    b=metrics.loc[metrics.controller.eq(reference)].set_index('block_id')
    if set(a.index)!=set(block_ids) or set(b.index)!=set(block_ids):
        raise ProtocolError('Every declared episode must have both cases; no silent complete-case deletion.')
    a=a.loc[block_ids];b=b.loc[block_ids]
    if not np.isfinite(a[list(METRICS)].to_numpy(float)).all() or not np.isfinite(b[list(METRICS)].to_numpy(float)).all():
        raise ProtocolError('Non-finite paired metric.')
    differences=a[list(METRICS)]-b[list(METRICS)]
    records=[];segment_records=[]
    for length in lengths:
        indices=moving_block_indices(target.segment_id.to_numpy(),replicates,int(length),seed)
        for segment,group in target.groupby('segment_id',sort=False):
            effective=min(int(length),len(group))
            segment_records.append({'block_length_requested':length,'segment_id':int(segment),'episodes':len(group),
                'effective_block_length':effective,'available_original_blocks':len(group)-effective+1,
                'warning':'No resampling variation for this segment at this length' if effective==len(group) else 'Short segment; local stationarity and block-length adequacy unproven'})
        for metric in METRICS:
            av=a[metric].to_numpy(float);bv=b[metric].to_numpy(float)
            points={'mean_paired_difference':float((av-bv).mean()),
                    'total_difference_fixed_exposure':float((av-bv).sum()),
                    'relative_aggregate_change_percent':float(100*(av.sum()/bv.sum()-1)) if bv.sum()!=0 else float('nan')}
            adraw=av[indices].sum(axis=1);bdraw=bv[indices].sum(axis=1)
            draws={'mean_paired_difference':(adraw-bdraw)/len(av),
                   'total_difference_fixed_exposure':adraw-bdraw,
                   'relative_aggregate_change_percent':np.divide(100*(adraw-bdraw),bdraw,out=np.full_like(adraw,np.nan),where=bdraw!=0)}
            for estimand,point in points.items():
                lower,upper=recentered_basic_interval(point,draws[estimand])
                records.append({'reference':reference,'comparison':comparison,'metric':metric,'estimand':estimand,
                    'episodes':len(av),'block_length_days':length,'replicates':replicates,'seed':seed,'estimate':point,
                    'lower_approx95':lower,'upper_approx95':upper,
                    'bootstrap_mean':float(np.nanmean(draws[estimand])) if np.isfinite(draws[estimand]).any() else float('nan'),
                    'method':'segment-aware non-circular moving-block; recentered basic',
                    'interpretation':'approximate conditional retrospective uncertainty; not confirmatory significance'})
    differences=differences.reset_index()
    return pd.DataFrame(records),differences,pd.DataFrame(segment_records)

def run_original_statistics(root: Path,output: Path,figures: Path) -> dict:
    config_path=root/'configs/research_audit_v1.json'
    config=json.loads(config_path.read_text())
    require_new_output_directory(output);require_new_output_directory(figures)
    metric_path=root/'results/frozen_heldout/final_20261029/analysis_v2/block_metrics.csv'
    schedule_path=root/'results/evaluation_schedule.csv'
    spec=config['statistics']
    intervals,differences,segments=paired_uncertainty(pd.read_csv(metric_path),pd.read_csv(schedule_path),
        lengths=spec['block_lengths_days'],replicates=spec['replicates'],seed=config['seed'])
    intervals.to_csv(output/'dependent_intervals.csv',index=False,mode='x')
    differences.to_csv(output/'paired_original_differences.csv',index=False,mode='x')
    segments.to_csv(output/'resampling_segment_limits.csv',index=False,mode='x')
    import os,tempfile
    os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'windresearch-stats-mpl'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(11,4.3))
    for ax,metric,title in zip(axes,['throughput_kwh','ramp_exceedance_kw','ramp_violations'],['Throughput','Ramp exceedance','Violation count']):
        part=intervals.loc[intervals.metric.eq(metric)&intervals.estimand.eq('relative_aggregate_change_percent')]
        ax.errorbar(part.estimate,part.block_length_days,xerr=[part.estimate-part.lower_approx95,part.upper_approx95-part.estimate],fmt='o',capsize=4,color='#0072B2')
        ax.axvline(0,color='grey',ls='--',lw=1)
        ax.set(title=title,xlabel='Adaptive relative change (%)',ylabel='Resampling length (days)',yticks=[2,3,7])
        ax.grid(axis='x',alpha=.2)
    fig.suptitle('Approximate segment-aware uncertainty · original retrospective comparison',fontsize=11)
    fig.tight_layout()
    fig.savefig(figures/'dependent_uncertainty.png',dpi=300,bbox_inches='tight')
    fig.savefig(figures/'dependent_uncertainty.pdf',bbox_inches='tight');plt.close(fig)
    metadata={'scope':'Original frozen scores unchanged; supplementary retrospective interval estimator',
        'configuration':spec,'seed':config['seed'],'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [config_path,metric_path,schedule_path]},
        'warnings':['No original block crosses a segment gap','Bootstrap block concatenation assumes finite-range dependence approximation','Segment with length<=requested block has no resampling variation','Only four segments; stationarity and asymptotic coverage not established','No block length selected using significance; all declared lengths reported'],
        'references':[{'title':'The Jackknife and the Bootstrap for General Stationary Observations','doi':'10.1214/aos/1176347265'},
                      {'title':'The Stationary Bootstrap','doi':'10.1080/01621459.1994.10476870','note':'Related background; the implemented method is non-circular fixed-length moving blocks, not stationary bootstrap'}]}
    with (output/'provenance.json').open('x') as handle:json.dump(metadata,handle,indent=2)
    return {'rows':len(intervals),'output':str(output),'all_lengths_reported':spec['block_lengths_days']}
