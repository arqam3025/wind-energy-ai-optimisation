"""Read-only diagnostics of frozen traces; exclusively create a new report set.

No optimisation, fitting, controller selection or scored-set change occurs here.
Reconstructed scenario ramps refer only to the first predicted interval under
the saved committed requests, not to unavailable stage-one/stage-two objectives.
"""
from pathlib import Path
import hashlib
import json
import os
import tempfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'wind-completion-diagnostic-mpl'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator

FREEZE_SHA = 'b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a'
KINDS = ['fixed', 'adaptive_one_sided']
COLORS = {'fixed':'#D55E00', 'adaptive_one_sided':'#0072B2'}
DT = 1/6

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def first_export(wind, charge_request, discharge_request, curtail_request):
    """Exact scenario first-step realised export in the frozen MILP."""
    wind=np.maximum(0,np.asarray(wind,dtype=float))
    charge=np.minimum(charge_request,wind)
    curtail=np.minimum(curtail_request,wind-charge)
    return wind-charge-curtail+discharge_request

def diagnose(block, trace, kind, block_id, segment_id):
    """Recompute transitions and physical identities independently from CSVs."""
    n=len(block)
    if n!=144 or len(trace)!=n:
        raise ValueError('Expected 144 paired intervals')
    if not np.array_equal(pd.to_datetime(trace.timestamp).to_numpy(),(block.timestamp+pd.Timedelta(minutes=10)).to_numpy()):
        raise ValueError('Origin-to-target timestamp misalignment')
    w=np.maximum(0,block.actual_h1_kw.to_numpy(float))
    g=trace.grid_export_kw.to_numpy(float)
    c=trace.charge_kw.to_numpy(float)
    d=trace.discharge_kw.to_numpy(float)
    u=trace.curtailment_kw.to_numpy(float)
    e=trace.soc_percent.to_numpy(float)*20
    e_before=np.r_[1000.,e[:-1]]
    initial=max(0,float(block.current_power_kw.iloc[0]))
    prior_g=np.r_[initial,g[:-1]]
    prior_w=np.r_[initial,w[:-1]]
    injection=d-c-u
    delta_injection=np.diff(np.r_[0.,injection])
    dw=w-prior_w
    dg=g-prior_g
    np.testing.assert_allclose(dg,dw+delta_injection,atol=1e-7,rtol=0)
    np.testing.assert_allclose(w-c-u+d,g,atol=1e-7,rtol=0)
    np.testing.assert_allclose(e,e_before+(.95*c-d/.95)*DT,atol=1e-5,rtol=0)
    if e.min()<800-1e-5 or e.max()>1800+1e-5:
        raise ValueError('SOC violation')
    if np.minimum(c,d).max()>1e-5 or max(c.max(),d.max())>1000+1e-5:
        raise ValueError('Battery power or simultaneous-operation violation')
    if min(c.min(),d.min(),u.min(),g.min())<-1e-6 or np.max(c+u-w)>1e-5:
        raise ValueError('Wind charging, curtailment or export violation')
    charge_request=trace.committed_charge_kw.to_numpy(float)
    discharge_request=trace.committed_discharge_kw.to_numpy(float)
    curtail_request=trace.committed_curtailment_kw.to_numpy(float)
    nom=np.maximum(0,block.xgboost_h1_kw.to_numpy(float))
    down=trace.downside_forecast_kw.to_numpy(float)
    pred_nom=first_export(nom,charge_request,discharge_request,curtail_request)
    pred_down=first_export(down,charge_request,discharge_request,curtail_request)
    pred_dr_nom=pred_nom-prior_g
    pred_dr_down=pred_down-prior_g
    excess=np.maximum(abs(dg)-200,0)
    wind_excess=np.maximum(abs(dw)-200,0)
    gv=abs(dg)>200.001
    wv=abs(dw)>200.001
    out=pd.DataFrame({
        'controller':kind,'block_id':block_id,'segment_id':segment_id,'interval':np.arange(n),
        'origin_time':block.timestamp,'target_time':pd.to_datetime(trace.timestamp),
        'wind_kw':w,'grid_kw':g,'previous_grid_kw':prior_g,'wind_ramp_kw':dw,'grid_ramp_kw':dg,
        'net_battery_kw':d-c,'curtailment_kw':u,'net_injection_kw':injection,
        'delta_net_injection_kw':delta_injection,'charge_kw':c,'discharge_kw':d,
        'energy_before_kwh':e_before,'energy_after_kwh':e,'soc_percent':e/20,
        'wind_exceedance_kw':wind_excess,'grid_exceedance_kw':excess,
        'exceedance_change_kw':excess-wind_excess,'grid_violation':gv,'wind_violation':wv,
        'introduced_violation':gv&~wv,'removed_violation':wv&~gv,
        'nominal_forecast_kw':nom,'downside_forecast_kw':down,
        'forecast_error_actual_minus_nominal_kw':w-nom,
        'reconstructed_first_nominal_export_kw':pred_nom,
        'reconstructed_first_downside_export_kw':pred_down,
        'reconstructed_first_nominal_ramp_kw':pred_dr_nom,
        'reconstructed_first_downside_ramp_kw':pred_dr_down,
        'reconstructed_first_weighted_exceedance_kw':.5*(np.maximum(abs(pred_dr_nom)-200,0)+np.maximum(abs(pred_dr_down)-200,0)),
        'realised_minus_nominal_export_kw':g-pred_nom,
        'charge_request_kw':charge_request,'discharge_request_kw':discharge_request,
        'curtail_request_kw':curtail_request,
        'wind_or_safety_limited_charge':charge_request-c>.001,
        'safety_limited_discharge':discharge_request-d>.001,
        'below_reserve_after':e<1000-.001,'at_lower_bound_after':e<=800+.01,
        'at_upper_bound_after':e>=1800-.01,
        'operating_mode':np.where(c>.001,'charging',np.where(d>.001,'discharging','idle')),
    })
    loss=float(((1-.95)*c+(1/.95-1)*d).sum()*DT)
    delta=e[-1]-1000
    export=float(g.sum()*DT)
    np.testing.assert_allclose(w.sum()*DT,export+u.sum()*DT+loss+delta,atol=1e-4,rtol=0)
    stats=dict(controller=kind,block_id=block_id,segment_id=segment_id,intervals=n,transitions=n,
        violations=int(gv.sum()),wind_violations=int(wv.sum()),introduced_violations=int((gv&~wv).sum()),
        removed_violations=int((wv&~gv).sum()),exceedance_kw=float(excess.sum()),
        wind_exceedance_kw=float(wind_excess.sum()),throughput_kwh=float((c+d).sum()*DT),
        conversion_losses_kwh=loss,export_kwh=export,curtailment_kwh=float(u.sum()*DT),
        inventory_change_kwh=float(delta),terminal_adjusted_export_kwh=float(export+(.95*delta if delta>=0 else delta/.95)),
        min_soc_percent=float(e.min()/20),max_soc_percent=float(e.max()/20),
        mean_absolute_grid_ramp_kw=float(abs(dg).mean()),max_grid_ramp_kw=float(abs(dg).max()))
    return out,stats

def table(frame, columns=None, digits=3):
    if columns is not None:frame=frame[columns]
    def cell(v):
        if isinstance(v,(float,np.floating)):return f'{v:,.{digits}f}'
        return str(v)
    return '| '+' | '.join(frame.columns)+' |\n| '+' | '.join(['---']*len(frame.columns))+' |\n'+'\n'.join('| '+' | '.join(cell(x) for x in row)+' |' for row in frame.itertuples(index=False,name=None))+'\n'

def main():
    manifest_path=ROOT/'results/development_controller_freeze_manifest.json'
    if sha(manifest_path)!=FREEZE_SHA:
        raise ValueError('Freeze hash mismatch')
    manifest=json.loads(manifest_path.read_text())
    schedule=pd.read_csv(ROOT/'results/evaluation_schedule.csv')
    valid=schedule.loc[schedule.evaluation_role.eq('evaluation')]
    source_paths=[manifest_path,ROOT/'results/evaluation_schedule.csv',ROOT/'scripts/frozen_fixed_heldout.py',ROOT/'scripts/frozen_adaptive_one_sided_heldout.py']
    details=[];blocks=[]
    for row in valid.itertuples():
        b=int(row.block_id)
        inp=ROOT/f'data/processed/evaluation_block_{b}.csv'
        block=pd.read_csv(inp,parse_dates=['timestamp'])
        source_paths.append(inp)
        for kind in KINDS:
            path=ROOT/f'results/frozen_heldout/final_20261029/{kind}/adaptive_charging_mpc_block_{b}_weight_0p500.csv'
            source_paths.append(path)
            trace=pd.read_csv(path)
            detail,stats=diagnose(block,trace,kind,b,int(row.segment_id))
            details.append(detail);blocks.append(stats)
    intervals=pd.concat(details,ignore_index=True)
    metrics=pd.DataFrame(blocks)
    out=ROOT/'docs/completion_tables'
    figs=ROOT/'docs/completion_figures'
    if out.exists() or figs.exists() or (ROOT/'docs/grid_ramp_diagnostic.md').exists():
        raise FileExistsError('Diagnostic outputs already exist; choose a new version, never overwrite')
    out.mkdir();figs.mkdir()
    def csv(frame,name):frame.to_csv(out/name,index=False,mode='x')
    csv(intervals,'interval_ramp_attribution.csv')
    csv(metrics,'block_diagnostic_metrics.csv')
    summary=[]
    for kind,g in intervals.groupby('controller'):
        both_safe=(abs(g.reconstructed_first_nominal_ramp_kw)<=200.001)&(abs(g.reconstructed_first_downside_ramp_kw)<=200.001)
        summary.append(dict(controller=kind,intervals=len(g),introduced_violations=int(g.introduced_violation.sum()),
            removed_violations=int(g.removed_violation.sum()),net_additional_violations=int(g.introduced_violation.sum()-g.removed_violation.sum()),
            gross_exceedance_added_kw=float(g.exceedance_change_kw.clip(lower=0).sum()),
            gross_exceedance_removed_kw=float(-g.exceedance_change_kw.clip(upper=0).sum()),
            net_exceedance_added_kw=float(g.exceedance_change_kw.sum()),
            realised_violations_with_both_first_predictions_safe=int((g.grid_violation&both_safe).sum()),
            realised_violations_with_nominal_prediction_safe=int((g.grid_violation&(abs(g.reconstructed_first_nominal_ramp_kw)<=200.001)).sum()),
            below_reserve_intervals=int(g.below_reserve_after.sum()),at_lower_bound_intervals=int(g.at_lower_bound_after.sum()),
            at_upper_bound_intervals=int(g.at_upper_bound_after.sum()),wind_or_safety_limited_charge_intervals=int(g.wind_or_safety_limited_charge.sum()),
            safety_limited_discharge_intervals=int(g.safety_limited_discharge.sum())))
    summary=pd.DataFrame(summary)
    csv(summary,'ramp_event_summary.csv')
    mode=intervals.groupby(['controller','operating_mode']).agg(intervals=('interval','size'),
        introduced=('introduced_violation','sum'),removed=('removed_violation','sum'),
        exceedance_added_kw=('exceedance_change_kw','sum'),mean_absolute_forecast_error_kw=('forecast_error_actual_minus_nominal_kw',lambda x:x.abs().mean())).reset_index()
    csv(mode,'operating_mode_diagnostics.csv')
    examples=[]
    for kind,g in intervals.groupby('controller'):
        for label,index in [('largest_worsening',g.exceedance_change_kw.idxmax()),('largest_improvement',g.exceedance_change_kw.idxmin())]:
            ex=intervals.loc[index].to_dict();ex['selection_rule']=label
            examples.append(ex)
    examples=pd.DataFrame(examples)
    csv(examples,'representative_intervals.csv')
    paired=metrics.pivot(index='block_id',columns='controller')
    differences=pd.DataFrame({name:paired[name]['adaptive_one_sided']-paired[name]['fixed'] for name in ['exceedance_kw','violations','throughput_kwh','conversion_losses_kwh','export_kwh','terminal_adjusted_export_kwh']}).reset_index()
    differences=differences.merge(valid[['block_id','segment_id']],on='block_id')
    csv(differences,'paired_block_differences.csv')
    segment=differences.groupby('segment_id').agg(blocks=('block_id','size'),exceedance_difference_kw=('exceedance_kw','sum'),
        violations_difference=('violations','sum'),throughput_difference_kwh=('throughput_kwh','sum')).reset_index()
    csv(segment,'segment_paired_differences.csv')
    dependence=[]
    for metric in ['exceedance_kw','violations','throughput_kwh']:
        for lag in [1,2,3]:
            first=[];later=[]
            for _,g in differences.groupby('segment_id'):
                first.extend(g[metric].iloc[:-lag]);later.extend(g[metric].iloc[lag:])
            dependence.append(dict(metric=metric,lag_blocks=lag,within_segment_pairs=len(first),pearson_correlation=float(np.corrcoef(first,later)[0,1])))
    dependence=pd.DataFrame(dependence)
    csv(dependence,'temporal_dependence_descriptive.csv')
    development=[]
    for kind in KINDS:
        values=manifest['development_results'][kind]
        development.append(dict(period='development',controller=kind,blocks=18,intervals=18*144,
            throughput_kwh=values['throughput_kwh'],losses_kwh=values['conversion_losses_kwh'],exceedance_kw=values['ramp_exceedance_kw'],violations=values['ramp_violations'],
            actual_export_mwh=values['actual_export_mwh'],adjusted_export_mwh=values['terminal_adjusted_export_mwh']))
        g=metrics.loc[metrics.controller.eq(kind)]
        development.append(dict(period='reserved_evaluation',controller=kind,blocks=49,intervals=49*144,
            throughput_kwh=g.throughput_kwh.sum(),losses_kwh=g.conversion_losses_kwh.sum(),exceedance_kw=g.exceedance_kw.sum(),violations=int(g.violations.sum()),
            actual_export_mwh=g.export_kwh.sum()/1000,adjusted_export_mwh=g.terminal_adjusted_export_kwh.sum()/1000))
    development=pd.DataFrame(development)
    development['throughput_kwh_per_interval']=development.throughput_kwh/development.intervals
    development['violation_rate_percent']=100*development.violations/development.intervals
    csv(development,'development_vs_evaluation.csv')
    plt.rcParams.update({'font.size':10,'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False})
    def save(fig,name):
        fig.tight_layout()
        fig.savefig(figs/(name+'.png'),dpi=300,bbox_inches='tight')
        fig.savefig(figs/(name+'.pdf'),bbox_inches='tight')
        plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
    for kind,g in metrics.groupby('controller'):
        axes[0].plot(g.block_id,g.exceedance_kw-g.wind_exceedance_kw,'o-',ms=3,lw=1,label=kind,color=COLORS[kind])
        axes[1].plot(g.block_id,g.violations-g.wind_violations,'o-',ms=3,lw=1,label=kind,color=COLORS[kind])
    for ax in axes:ax.axhline(0,color='grey',ls='--');ax.legend()
    axes[0].set_ylabel('Added exceedance (kW)');axes[1].set_ylabel('Added violations');axes[1].set_xlabel('Scheduled block (6 excluded)')
    save(fig,'control_minus_uncontrolled_by_block')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    x=np.arange(2);width=.35
    axes[0].bar(x-width/2,summary.introduced_violations,width,label='Introduced',color='#D55E00')
    axes[0].bar(x+width/2,summary.removed_violations,width,label='Removed',color='#0072B2')
    axes[1].bar(x-width/2,summary.gross_exceedance_added_kw,width,label='Added',color='#D55E00')
    axes[1].bar(x+width/2,summary.gross_exceedance_removed_kw,width,label='Removed',color='#0072B2')
    for ax in axes:ax.set_xticks(x,summary.controller,rotation=12);ax.legend()
    axes[0].set_ylabel('Transitions');axes[1].set_ylabel('Exceedance sum (kW)')
    save(fig,'gross_ramp_changes')
    for ex in examples.itertuples():
        g=intervals.loc[intervals.controller.eq(ex.controller)&intervals.block_id.eq(ex.block_id)&intervals.interval.between(max(0,ex.interval-4),min(143,ex.interval+4))]
        fig,axes=plt.subplots(3,1,figsize=(10,7),sharex=True)
        axes[0].plot(g.target_time,g.wind_kw,'o-',label='Uncontrolled wind',lw=1,color='grey')
        axes[0].plot(g.target_time,g.grid_kw,'o-',label='Controlled export',lw=1,color=COLORS[ex.controller])
        axes[1].plot(g.target_time,g.wind_ramp_kw,'o-',label='Wind ramp',lw=1,color='grey')
        axes[1].plot(g.target_time,g.grid_ramp_kw,'o-',label='Grid ramp',lw=1,color=COLORS[ex.controller])
        axes[1].plot(g.target_time,g.reconstructed_first_nominal_ramp_kw,'--',label='Reconstructed first nominal ramp',lw=1)
        for limit in [-200,200]:axes[1].axhline(limit,color='black',ls=':',lw=.8)
        axes[2].plot(g.target_time,g.net_battery_kw,'o-',label='Discharge minus charge (kW)',lw=1)
        axes[2].plot(g.target_time,g.curtailment_kw,'--',label='Curtailment (kW)',lw=1)
        for ax in axes:
            ax.axvline(pd.Timestamp(ex.target_time),color='#CC79A7',ls=':');ax.legend(loc='best',fontsize=8)
        axes[0].set_ylabel('Power (kW)');axes[1].set_ylabel('Signed ramp (kW)');axes[2].set_ylabel('Battery / curtailment (kW)')
        axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        axes[2].set_xlabel('Target time, dataset clock, '+str(pd.Timestamp(ex.target_time).date()))
        axes[0].set_title(f'{ex.controller}: {ex.selection_rule.replace("_"," ")}, block {ex.block_id}')
        save(fig,f'event_{ex.controller}_{ex.selection_rule}')
    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
    for kind,g in intervals.groupby('controller'):
        daily=g.groupby('block_id').soc_percent.agg(['min','median','max'])
        axes[0].plot(daily.index,daily['median'],label=kind,color=COLORS[kind])
        axes[0].fill_between(daily.index,daily['min'],daily['max'],alpha=.12,color=COLORS[kind])
        axes[1].plot(daily.index,metrics.loc[metrics.controller.eq(kind)].set_index('block_id').inventory_change_kwh,label=kind,color=COLORS[kind])
    for level in [40,90]:axes[0].axhline(level,color='grey',ls=':',lw=.8)
    axes[1].axhline(0,color='grey',ls='--');axes[0].set_ylabel('SOC: median and range (%)');axes[1].set_ylabel('Final minus initial energy (kWh)');axes[1].set_xlabel('Scheduled block')
    axes[0].legend();axes[1].legend();save(fig,'soc_inventory_diagnostic')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for kind,g in intervals.groupby('controller'):
        axes[0].scatter(g.wind_ramp_kw,g.delta_net_injection_kw,s=2,alpha=.15,label=kind,color=COLORS[kind])
        violation=g.loc[g.grid_violation]
        axes[1].scatter(violation.reconstructed_first_nominal_ramp_kw,violation.grid_ramp_kw,s=4,alpha=.2,label=kind,color=COLORS[kind])
    axes[0].set(xlabel='Uncontrolled signed wind change (kW)',ylabel='Change in battery minus curtailment injection (kW)')
    axes[1].set(xlabel='Reconstructed first nominal ramp (kW)',ylabel='Realised grid ramp (kW)')
    for ax in axes:ax.legend(markerscale=3);ax.xaxis.set_major_locator(MaxNLocator(5));ax.yaxis.set_major_locator(MaxNLocator(5))
    save(fig,'ramp_attribution_and_prediction')
    source_hashes={str(p.relative_to(ROOT)):sha(p) for p in source_paths}
    with (out/'diagnostic_provenance.json').open('x',encoding='utf-8') as f:
        json.dump({'source_sha256':source_hashes,'freeze_sha256':FREEZE_SHA,'scored_blocks':valid.block_id.astype(int).tolist(),
            'scope':'Read-only post-hoc diagnostic of unchanged frozen outputs; no new controller or resampled confidence interval',
            'unavailable':'Full horizon planned trajectories, stage-one optimum, stage-two achieved primary, solver gaps/times are not in saved traces'},f,indent=2)
    report=build_report(metrics,summary,mode,examples,segment,dependence,development)
    with (ROOT/'docs/grid_ramp_diagnostic.md').open('x',encoding='utf-8') as f:f.write(report)
    print(summary.to_string(index=False))
    print(examples[['controller','selection_rule','block_id','interval','target_time','wind_ramp_kw','grid_ramp_kw','exceedance_change_kw','charge_kw','discharge_kw','soc_percent']].to_string(index=False))
    print('Created docs/grid_ramp_diagnostic.md, completion_tables and completion_figures; originals untouched.')

def build_report(metrics,summary,mode,examples,segment,dependence,development):
    totals=metrics.groupby('controller').sum(numeric_only=True)
    baseline=metrics.loc[metrics.controller.eq('fixed')]
    overview=pd.DataFrame([
        {'strategy':'uncontrolled','violations':int(baseline.wind_violations.sum()),'exceedance_kw':baseline.wind_exceedance_kw.sum(),'throughput_kwh':0.,'conversion_losses_kwh':0.},
        *[{'strategy':k,'violations':int(totals.loc[k,'violations']),'exceedance_kw':totals.loc[k,'exceedance_kw'],'throughput_kwh':totals.loc[k,'throughput_kwh'],'conversion_losses_kwh':totals.loc[k,'conversion_losses_kwh']} for k in KINDS]])
    brief=summary[['controller','introduced_violations','removed_violations','net_additional_violations','gross_exceedance_added_kw','gross_exceedance_removed_kw','net_exceedance_added_kw']]
    selected=examples[['controller','selection_rule','block_id','interval','target_time','wind_ramp_kw','grid_ramp_kw','exceedance_change_kw','charge_kw','discharge_kw','soc_percent']].copy()
    predicted=summary[['controller','realised_violations_with_both_first_predictions_safe','realised_violations_with_nominal_prediction_safe','wind_or_safety_limited_charge_intervals','safety_limited_discharge_intervals']]
    operational=summary[['controller','below_reserve_intervals','at_lower_bound_intervals','at_upper_bound_intervals']]
    mechanisms=[]
    for ex in examples.itertuples():
        previous_injection=ex.net_injection_kw-ex.delta_net_injection_kw
        mechanisms.append(f'- **{ex.controller}, {ex.selection_rule.replace("_"," ")}, block {ex.block_id} at {ex.target_time}:** '
            f'the wind change is {ex.wind_ramp_kw:+.3f} kW. Net battery-minus-curtailment injection changes from '
            f'{previous_injection:+.3f} to {ex.net_injection_kw:+.3f} kW, adding {ex.delta_net_injection_kw:+.3f} kW to that wind change. '
            f'The resulting grid change is {ex.grid_ramp_kw:+.3f} kW. The reconstructed first nominal ramp is '
            f'{ex.reconstructed_first_nominal_ramp_kw:+.3f} kW and actual wind minus nominal forecast is '
            f'{ex.forecast_error_actual_minus_nominal_kw:+.3f} kW. This is an exact trajectory decomposition; '
            'it does not identify why the full-horizon optimum preferred that command.')
    return f'''# Grid-ramp diagnostic of the unchanged frozen comparison

29 October 2026. This is a post-hoc, read-only diagnostic, not a new controller experiment. It preserves all 49 scored episodes and their original results. The reserved-period comparison is retrospective; historical test inspection and development-target overlap prevent a clean confirmatory interpretation.

## Verified accounting and principal finding

{table(overview)}
Both battery controllers worsen aggregate exceedance and violation counts relative to uncontrolled wind. Adaptive one-sided improves on fixed margins but does not demonstrate net mitigation in these metrics. The original 27.86% throughput reduction, approximately 27.92% conversion-loss reduction, 0.77% exceedance reduction and 16 fewer violations versus fixed are unchanged.

For every episode, both baselines use the same target times, origin current power, nonnegative wind, 200 kW threshold, >200.001 kW violation test and 144 transitions. The first transition is origin current power to the first target; later transitions are within the episode. No cross-episode transition is added. The battery begins at 1,000 kWh with zero prior battery/curtailment injection. All 98 traces satisfy power and stored-energy conservation, SOC 40–90%, power bounds and wind-only charging. This diagnostic did not identify a transition-counting or physical-balance implementation bug explaining the negative finding.

## Exact ramp attribution

Let `b = discharge - charge` and `j = b - curtailment`. The measured identity is:

`signed_grid_ramp = signed_wind_ramp + (j[k] - j[k-1])`, with `j[-1]=0` at episode initialization.

This identity held to numerical tolerance for every controlled interval. A change in battery injection can either cancel a wind change or reinforce it. Charging during one interval also changes the reference export for the next interval. Consequently, the sign of current charge/discharge alone does not establish whether a transition is improved.

{table(brief)}
Gross added and removed exceedance refer to `controlled_exceedance - uncontrolled_exceedance` at paired transitions. Their difference is the observed net deterioration; they are not energy quantities. Introduced violations are transitions below threshold without control but above threshold with control; removed violations reverse that classification.

![Control-minus-uncontrolled outcomes by unchanged scheduled block.](completion_figures/control_minus_uncontrolled_by_block.png)

![Introduced versus removed violations and gross exceedance contributions.](completion_figures/gross_ramp_changes.png)

## Representative intervals: deliberately selected diagnostic extremes

The examples below are selected by the largest positive and negative change in exceedance for each controller. They illustrate mechanisms, not typical or independent evidence; no favourable event selection informs controller choice.

{table(selected)}
The CSV `completion_tables/representative_intervals.csv` also contains requested/realised commands, previous export, forecast error, reconstructed scenario ramps and stored energy. Local event windows preserve each controller's actual prior export and do not restart the simulation at the event.

{chr(10).join(mechanisms)}

![Fixed margin: largest worsening interval and neighbouring trajectory.](completion_figures/event_fixed_largest_worsening.png)

![Fixed margin: largest improvement interval and neighbouring trajectory.](completion_figures/event_fixed_largest_improvement.png)

![Adaptive one-sided: largest worsening interval and neighbouring trajectory.](completion_figures/event_adaptive_one_sided_largest_worsening.png)

![Adaptive one-sided: largest improvement interval and neighbouring trajectory.](completion_figures/event_adaptive_one_sided_largest_improvement.png)

## Predicted versus realised first-step ramps

The saved traces contain requested first-step charge, discharge and curtailment, plus nominal/downside wind. For each scenario, this diagnostic reconstructs `charge=min(request, scenario wind)` and `curtail=min(request, scenario wind-charge)`, then computes predicted first export and its change from the **actual previous controlled export**. This reproduces the frozen first-step scenario relations without solving or altering the optimisation.

{table(predicted)}
Realised violations despite both reconstructed first scenarios being within threshold demonstrate forecast/scenario mismatch for those transitions. They do not prove which term caused a particular optimiser choice, nor provide stage-one/stage-two full-horizon objective values. The weighted reconstructed first-step exceedance is only one component of the six-step objective, evaluated at the committed command.

![Injection-change attribution and realised violations against reconstructed first nominal ramps.](completion_figures/ramp_attribution_and_prediction.png)

The 100 kW primary allowance permits the secondary solution to be up to 100 kW worse than the **predicted weighted six-step** primary optimum. It is not a cap on the realised ramp or an allowance applied independently to every interval. The primary target uses nominal/downside forecasts, not actual future wind. The secondary cost additionally penalises absolute ramps, battery ramps, throughput, terminal SOC deviation, curtailment and reserve shortfall. Minimising that forecast-based objective does not guarantee improving realised ramps over the realised uncontrolled trajectory.

## SOC, reserve, commands and energy trade-offs

{table(operational)}
Counts refer to end-of-interval energy: below the 1,000 kWh soft reserve, within 0.01 kWh of the 800 kWh lower bound, or within 0.01 kWh of the 1,800 kWh upper bound. They diagnose operation, not independent infeasibility; the hard bounds remain satisfied. `wind_or_safety_limited_charge` records request minus realised charge >0.001 kW and does not independently distinguish every limiting cause.

{table(mode)}
Grouping by current operating mode is descriptive. Ramp outcomes depend on the change in battery injection and previous controlled export, so these groups cannot identify the causal effect of charging or reserve penalties.

![Daily SOC median/range and final stored-energy changes.](completion_figures/soc_inventory_diagnostic.png)

Actual export, curtailment, modelled losses and inventory changes are in `completion_tables/block_diagnostic_metrics.csv`. The identity `wind energy = export + curtailment + conversion losses + inventory change` is checked. Actual and hypothetical terminal-adjusted export must remain separate: the adjustment is not a feasible restoration dispatch or additional realised generation.

## Development versus reserved-period behaviour

{table(development[['period','controller','blocks','throughput_kwh_per_interval','violation_rate_percent','exceedance_kw','actual_export_mwh','adjusted_export_mwh']])}
Development showed throughput reduction 43.70%, exceedance reduction 0.66%, and 11 **additional** violations for adaptive versus fixed. The reserved-period differences are 27.86%, 0.77%, and 16 fewer violations. Different observation counts and weather mean raw totals across these periods should not be compared as if exposures were equal. The table provides per-interval throughput and violation rates but does not convert this observational comparison into a causal distribution-shift estimate.

## Temporal dependence and heterogeneity

{table(segment)}
Differences are adaptive minus fixed. The four chronological segments do not show uniform violation improvement. They are only four segments, not four assured independent replications.

{table(dependence)}
Lag correlations use adjacent daily blocks within the same contiguous segment; gaps are not bridged. These correlations are descriptive diagnostics with limited sample sizes, not a fitted stochastic model. The existing ordinary paired day-bootstrap resamples days independently. Its intervals must remain labelled descriptive and are not dependence-adjusted confidence intervals. No new bootstrap method, significance test, controller choice or scored-set modification was introduced by this diagnostic.

## Classification of findings

| Category | Evidence and interpretation |
| --- | --- |
| Confirmed scientific-design problem | Prior evaluation-period inspection predates the freeze. Excluding development block 6 by origin still leaves five measured target times shared with block 7 (15 horizon-target pairs and five scored h1 outcomes). The existing preflight omits block 6 from its development-overlap inputs. This prevents an untouched, target-disjoint confirmatory claim; it is distinct from runtime causal residual eligibility. |
| Confirmed reporting/diagnostic limit | Original CSVs do not retain full planned trajectories, stage-one optimum, stage-two achieved primary, solver gaps or per-step solve times. Full-stage causal attribution cannot be recovered from these traces. No such values are invented here. |
| Confirmed implementation checks passed | Same transition definitions and timestamps; 144 transitions per episode; physical balance, SOC/power limits and no simultaneous charging/discharging. No serious physical or ramp-accounting implementation error was found in these checks. |
| Expected optimisation trade-off | Requests optimise forecast-based scenarios and a composite secondary objective, with a frozen 100 kW primary allowance. Actual wind can differ from both scenarios, and reserve/terminal/curtailment/battery-ramp costs can change actions. These are demonstrated design properties, not proven individual causal contributions. |
| Modelling limitation | Soft ramps, two downward scenarios, scenario-dependent future recourse, short horizon, episode resets and idealised wind-limited execution do not guarantee actual ramp mitigation. No hard realised-ramp or network constraint is implemented. |
| Hypothesis requiring a new experiment | Reserve penalty, 100 kW allowance, asymmetric scenario coverage, horizon length and end-of-episode inventory incentives may each contribute to deterioration. Establishing their separate effects requires predeclared development-only ablations or genuinely new evaluation data, with new frozen versions and filenames. |

The existing aggregate adaptive-versus-fixed arithmetic remains supported. Claims of clean confirmatory generalisation or improved uncontrolled-wind ramp performance must stop. No controller or evaluated set was changed to obtain more favourable results.

## Reproduction and artifacts

Run `python scripts/build_completion_diagnostics.py` from the repository root in a fresh output checkout. It requires the original local inputs and exclusively creates this report, `docs/completion_tables/` and `docs/completion_figures/`; it refuses to overwrite existing outputs. Source SHA256 values and scope are recorded in `completion_tables/diagnostic_provenance.json`. Every figure is available as 300 dpi PNG and vector PDF. Original models, calibration, controllers and evaluation outputs are read only.
'''

if __name__=='__main__':
    main()
