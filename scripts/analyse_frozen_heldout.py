"""Independent physical audit, paired metrics and archival figures for frozen runs."""
import argparse
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parents[1]/'.mplconfig'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from heldout_support import ROOT, VALID_BLOCKS, preflight

def validate_and_measure(frame, block, kind):
    d = frame
    dt = 1/6
    assert len(d) == len(block) == 144
    assert (pd.to_datetime(d.timestamp).to_numpy() == (block.timestamp+pd.Timedelta(minutes=10)).to_numpy()).all()
    assert np.isfinite(d.select_dtypes('number')).all().all()
    c, b, w, u, g = [d[name].to_numpy() for name in ['charge_kw','discharge_kw','wind_generation_kw','curtailment_kw','grid_export_kw']]
    energy = d.soc_percent.to_numpy()*20
    before = np.r_[1000., energy[:-1]]
    np.testing.assert_allclose(energy, before+.95*c*dt-b*dt/.95, atol=1e-5, rtol=0)
    np.testing.assert_allclose(w-c-u+b, g, atol=1e-6, rtol=0)
    np.testing.assert_allclose(w, np.maximum(0, block.actual_h1_kw), atol=1e-6, rtol=0)
    assert energy.min() >= 800-1e-5 and energy.max() <= 1800+1e-5
    assert min(c.min(), b.min(), u.min(), g.min()) >= -1e-6
    assert max(c.max(), b.max()) <= 1000+1e-5
    assert np.minimum(c,b).max() <= .01
    assert (c+u-w).max() <= 1e-5
    assert (c-d.committed_charge_kw).max() <= 1e-5
    assert (b-d.committed_discharge_kw).max() <= 1e-5
    np.testing.assert_allclose(c,np.minimum.reduce([d.committed_charge_kw.to_numpy(),w,np.full(len(d),1000.),np.maximum(0,1800-before)/(.95*dt)]),atol=1e-5,rtol=0)
    np.testing.assert_allclose(b,np.minimum.reduce([d.committed_discharge_kw.to_numpy(),np.full(len(d),1000.),np.maximum(0,before+.95*c*dt-800)*.95/dt]),atol=1e-5,rtol=0)
    np.testing.assert_allclose(u,np.minimum(d.committed_curtailment_kw.to_numpy(),np.maximum(0,w-c)),atol=1e-5,rtol=0)
    if kind == 'adaptive_one_sided':
        assert (pd.to_datetime(d.newest_residual_target).to_numpy() < block.timestamp.to_numpy()).all()
    charge, discharge, curtailed, wind, export = [float(x.sum()*dt) for x in [c,b,u,w,g]]
    losses = (1-.95)*charge+(1/.95-1)*discharge
    delta = float(energy[-1]-1000)
    assert abs(wind-export-curtailed-losses-delta) < 1e-4
    ramps = np.abs(np.diff(np.r_[max(0, block.current_power_kw.iloc[0]),g]))
    # Frozen convention: >200.001 kW; include the initial decision ramp.
    return dict(intervals=len(d), transitions=len(ramps), ramp_violations=int((ramps>200.001).sum()),
                ramp_exceedance_kw=float(np.maximum(ramps-200,0).sum()),
                max_ramp_kw=float(ramps.max()), mean_ramp_kw=float(ramps.mean()),
                throughput_kwh=charge+discharge, charge_kwh=charge, discharge_kwh=discharge,
                conversion_losses_kwh=losses, curtailment_kwh=curtailed, wind_kwh=wind,
                export_kwh=export, terminal_energy_delta_kwh=delta,
                terminal_adjusted_export_kwh=export+(.95*delta if delta>=0 else delta/.95),
                final_soc_percent=float(d.soc_percent.iloc[-1]), physical_checks='pass')

def target_audit(output):
    raw = pd.read_csv(ROOT/'data/raw/T1.csv')
    times = pd.to_datetime(raw['Date/Time'], format='%d %m %Y %H:%M')
    assert not times.duplicated().any()
    measured = pd.Series(raw['LV ActivePower (kW)'].clip(lower=0).to_numpy(), index=times)
    records=[]
    for b in VALID_BLOCKS:
        d = pd.read_csv(ROOT/f'data/processed/evaluation_block_{b}.csv',parse_dates=['timestamp'])
        for h in range(1,7):
            actual = measured.reindex(d.timestamp+pd.Timedelta(minutes=10*h)).to_numpy()
            assert np.isfinite(actual).all(), f'Missing raw target block {b}, h{h}'
            error = np.abs(actual-d[f'actual_h{h}_kw'].to_numpy())
            assert error.max() < .001, (b,h,error.max())
            records.append(dict(block_id=b,horizon_minutes=h*10,verified=len(error),max_error_kw=error.max()))
    pd.DataFrame(records).to_csv(output/'raw_target_audit.csv',index=False,mode='x')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',required=True)
    parser.add_argument('--output',default='analysis_v1')
    args=parser.parse_args()
    preflight()
    run=ROOT/'results/frozen_heldout'/args.run
    output=run/args.output
    output.mkdir(exist_ok=False)
    target_audit(output)
    rows=[]
    forecast=[]
    coverage=[]
    baselines=[]
    for b in VALID_BLOCKS:
        block=pd.read_csv(ROOT/f'data/processed/evaluation_block_{b}.csv',parse_dates=['timestamp'])
        wind=np.maximum(0,block.actual_h1_kw.to_numpy())
        ramps=np.abs(np.diff(np.r_[max(0,block.current_power_kw.iloc[0]),wind]))
        baselines.append(dict(block_id=b,ramp_violations=int((ramps>200.001).sum()),
            ramp_exceedance_kw=float(np.maximum(0,ramps-200).sum()),wind_energy_kwh=float(wind.sum()/6)))
        for kind in ['fixed','adaptive_one_sided']:
            path=run/kind/f'adaptive_charging_mpc_block_{b}_weight_0p500.csv'
            d=pd.read_csv(path)
            rows.append(dict(block_id=b,controller=kind,**validate_and_measure(d,block,kind)))
            fixed_margins=pd.read_csv(ROOT/'results/multistep_uncertainty_calibration_split.csv').calibration_quantile_kw.to_numpy()
            for h in range(1,7):
                margins = d[f'adaptive_margin_h{h}_kw'].to_numpy() if kind == 'adaptive_one_sided' else np.full(len(d),fixed_margins[h-1])
                lower = np.maximum(0, block[f'xgboost_h{h}_kw'].to_numpy()-margins)
                coverage.append(dict(block_id=b,controller=kind,horizon_minutes=10*h,
                    lower_bound_coverage=float((block[f'actual_h{h}_kw'].to_numpy()>=lower).mean()),
                    mean_margin_kw=float(margins.mean())))
        for h in range(1,7):
            for model in ['xgboost','persistence']:
                error=block[f'{model}_h{h}_kw']-block[f'actual_h{h}_kw']
                forecast.append(dict(block_id=b,horizon_minutes=10*h,model=model,mae_kw=error.abs().mean(),mse_kw=(error**2).mean()))
    metrics=pd.DataFrame(rows)
    pd.DataFrame(baselines).to_csv(output/'uncontrolled_wind_baseline.csv',index=False,mode='x')
    pd.DataFrame(coverage).to_csv(output/'uncertainty_coverage.csv',index=False,mode='x')
    metrics.to_csv(output/'block_metrics.csv',index=False,mode='x')
    totals=metrics.groupby('controller').sum(numeric_only=True).drop(columns=['block_id','final_soc_percent','max_ramp_kw','mean_ramp_kw'])
    totals['violation_rate']=totals.ramp_violations/totals.transitions
    totals['max_ramp_kw']=metrics.groupby('controller').max_ramp_kw.max()
    totals['mean_ramp_kw']=metrics.groupby('controller').mean_ramp_kw.mean()
    totals.to_csv(output/'aggregate_metrics.csv',mode='x')
    paired=metrics.pivot(index='block_id',columns='controller')
    keys=['throughput_kwh','conversion_losses_kwh','ramp_exceedance_kw','ramp_violations','terminal_adjusted_export_kwh']
    differences=pd.DataFrame({key:paired[key]['adaptive_one_sided']-paired[key]['fixed'] for key in keys})
    differences.to_csv(output/'paired_differences.csv',mode='x')
    # Descriptive paired bootstrap; blocks are temporally dependent, so these
    # intervals are exploratory and are not evidence of independent replication.
    rng=np.random.default_rng(20261029)
    draws=rng.integers(0,len(differences),size=(10000,len(differences)))
    stats=[]
    for key in keys:
        values=differences[key].to_numpy()
        lo,hi=np.quantile(values[draws].mean(axis=1),[.025,.975])
        stats.append(dict(metric=key,mean_difference=values.mean(),median_difference=np.median(values),
                          lower_descriptive_bootstrap=lo,upper_descriptive_bootstrap=hi,
                          negative_blocks=int((values<0).sum()),positive_blocks=int((values>0).sum()),ties=int((values==0).sum())))
    pd.DataFrame(stats).to_csv(output/'paired_summary.csv',index=False,mode='x')
    f=pd.DataFrame(forecast).groupby(['model','horizon_minutes'])[['mae_kw','mse_kw']].mean().reset_index()
    f['rmse_kw']=np.sqrt(f.mse_kw)
    f.to_csv(output/'forecast_metrics.csv',index=False,mode='x')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
    def save(fig,name):
        fig.tight_layout()
        fig.savefig(output/f'{name}.png',dpi=300,bbox_inches='tight')
        fig.savefig(output/f'{name}.pdf',bbox_inches='tight')
        plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(10,7))
    for ax,key,label in zip(axes.flat,keys[:4],['Throughput (kWh)','Conversion losses (kWh)','Ramp exceedance sum (kW)','Ramp violation count']):
        ax.scatter(paired[key]['fixed'],paired[key]['adaptive_one_sided'],s=22,alpha=.7)
        lim=max(paired[key].max())*1.05
        ax.plot([0,lim],[0,lim],color='grey',ls='--',lw=1)
        ax.set(xlabel='Fixed margin',ylabel='Adaptive one-sided',title=label)
        ax.xaxis.set_major_locator(MaxNLocator(5))
        ax.yaxis.set_major_locator(MaxNLocator(5))
    save(fig,'paired_controllers')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for model,group in f.groupby('model'):
        axes[0].plot(group.horizon_minutes,group.mae_kw,'o-',label=model)
        axes[1].plot(group.horizon_minutes,group.rmse_kw,'o-',label=model)
    for ax,label in zip(axes,['MAE (kW)','RMSE (kW)']):
        ax.set(xlabel='Forecast horizon (minutes)',ylabel=label); ax.legend()
    save(fig,'forecast_accuracy')
    fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True)
    for ax,key in zip(axes,['throughput_kwh','ramp_exceedance_kw']):
        ax.bar(differences.index,differences[key],color=np.where(differences[key]<0,'#0072B2','#D55E00'))
        ax.axhline(0,color='black',lw=.7); ax.set_ylabel(key.replace('_',' '))
    axes[-1].set_xlabel('Evaluation block (block 6 excluded)')
    save(fig,'paired_differences')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    totals[['charge_kwh','discharge_kwh','throughput_kwh']].div(1000).plot.bar(ax=axes[0],rot=15,color=['#56B4E9','#E69F00','#0072B2'])
    totals[['conversion_losses_kwh','curtailment_kwh']].div(1000).plot.bar(ax=axes[1],rot=15,color=['#D55E00','#009E73'])
    axes[0].set_ylabel('AC energy (MWh)'); axes[1].set_ylabel('Energy (MWh)')
    for ax in axes: ax.set_xlabel('Controller')
    save(fig,'battery_energy_accounting')
    cov=pd.DataFrame(coverage).groupby(['controller','horizon_minutes']).mean(numeric_only=True).reset_index()
    fig,ax=plt.subplots(figsize=(6,4))
    for kind,group in cov.groupby('controller'):
        ax.plot(group.horizon_minutes,group.lower_bound_coverage,'o-',label=kind)
    ax.axhline(.9,color='grey',ls='--',label='Nominal reference (not a guarantee)')
    ax.set(xlabel='Horizon (minutes)',ylabel='Empirical lower-bound coverage',ylim=(0,1.02));ax.legend()
    save(fig,'uncertainty_coverage')
    fig,axes=plt.subplots(3,1,figsize=(11,7),sharex=True)
    # Pre-specified illustrative first valid block; not selected for performance.
    for kind in ['fixed','adaptive_one_sided']:
        d=pd.read_csv(run/kind/'adaptive_charging_mpc_block_1_weight_0p500.csv',parse_dates=['timestamp'])
        for ax,col in zip(axes,['grid_export_kw','soc_percent','adaptive_margin_h1_kw']):
            if col in d: ax.plot(d.timestamp,d[col],label=kind,lw=1)
            elif kind=='fixed':
                margin=pd.read_csv(ROOT/'results/multistep_uncertainty_calibration_split.csv').calibration_quantile_kw.iloc[0]
                ax.plot(d.timestamp,np.full(len(d),margin),label=kind,lw=1,ls='--')
    axes[0].plot(d.timestamp,d.wind_generation_kw,color='grey',alpha=.6,label='Uncontrolled wind',lw=.8)
    for ax,label in zip(axes,['Grid export (kW)','SOC (%)','One-step margin (kW)']):
        ax.set_ylabel(label); ax.legend()
    axes[-1].set_xlabel('Target time (dataset clock; timezone unspecified)')
    save(fig,'first_block_trace')
    report={'status':'complete','blocks':len(VALID_BLOCKS),'intervals_per_controller':49*144,
            'physical_audit':'pass','strict_causal_targets':'pass','raw_target_comparisons':49*144*6,
            'difference_direction':'adaptive minus fixed',
            'terminal_adjustment':'export_kwh + 0.95*delta if delta>=0 else export_kwh+delta/0.95; delta=final_energy_kwh-1000; hypothetical restoration accounting',
            'ramp_convention':'144 transitions per block including current_power to first controlled export; >200.001 kW violations',
            'bootstrap_warning':'Descriptive block resampling only; temporal dependence limits inferential interpretation'}
    with (output/'validation.json').open('x') as handle: json.dump(report,handle,indent=2)
    print(totals.to_string())
    print('Validated and saved:',output)

if __name__=='__main__': main()
