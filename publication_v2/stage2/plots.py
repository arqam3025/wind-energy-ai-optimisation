"""Publication-format graphs from validated records; synthetic labels are mandatory."""
from datetime import datetime
import os
from pathlib import Path
import tempfile


def research_figures(points, intervals, errors, coverage, directory: Path, interpretation: str):
    os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'publication_v2_stage2_mpl'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    title='SYNTHETIC SOFTWARE TEST — NOT RESEARCH' if interpretation=='SYNTHETIC_SOFTWARE_TEST_ONLY' else 'Retrospective development only — no independent validation'
    colors={'persistence':'#666666','xgboost':'#0072B2','lightgbm':'#D55E00'}
    def save(fig,name):
        fig.suptitle(title,fontsize=10);fig.tight_layout(rect=(0,0,1,.95))
        for extension in ('png','pdf'):
            path=directory/f'{name}.{extension}'
            if path.exists(): raise FileExistsError(f'Refusing figure overwrite: {path}')
            fig.savefig(path,dpi=300,bbox_inches='tight')
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for model,color in colors.items():
        rows=sorted([r for r in errors['per_horizon'] if r['model']==model],key=lambda r:r['horizon_minutes'])
        for ax,metric in zip(axes,('mae_kw','rmse_kw')):
            ax.plot([r['horizon_minutes'] for r in rows],[r[metric] for r in rows],'o-',label=model,color=color)
            ax.set(xlabel='Forecast horizon from origin (minutes)',ylabel=metric.replace('_',' ').upper());ax.grid(alpha=.2)
    axes[0].legend();save(fig,'forecast_errors')
    fig,axes=plt.subplots(1,3,figsize=(12,4),sharey=True)
    for ax,model in zip(axes,colors):
        rows=[r for r in coverage['per_horizon'] if r['model']==model]
        for method in sorted({r['method'] for r in rows}):
            part=sorted([r for r in rows if r['method']==method],key=lambda r:r['horizon_minutes'])
            ax.plot([r['horizon_minutes'] for r in part],[r['marginal_coverage'] for r in part],'o-',label=method,lw=1)
        ax.axhline(1-rows[0]['alpha'],color='gray',ls='--',lw=1);ax.set(title=model,xlabel='Horizon (minutes)',ylim=(0,1.03));ax.grid(alpha=.2)
    axes[0].set_ylabel('Empirical marginal coverage');axes[-1].legend(fontsize=7)
    save(fig,'uncertainty_coverage')
    fig,ax=plt.subplots(figsize=(11,4))
    first=sorted([r for r in points if r['model']=='persistence' and r['horizon_minutes']==10],key=lambda r:r['target_time'])[:60]
    keys={r['origin_time'] for r in first}
    ax.plot([datetime.fromisoformat(r['target_time']) for r in first],[r['actual_kw'] for r in first],color='black',label='actual',lw=1.5)
    for model,color in colors.items():
        rows=sorted([r for r in points if r['model']==model and r['horizon_minutes']==10 and r['origin_time'] in keys],key=lambda r:r['target_time'])
        ax.plot([datetime.fromisoformat(r['target_time']) for r in rows],[r['prediction_kw'] for r in rows],label=model,color=color,lw=1)
    band=sorted([r for r in intervals if r['model']=='xgboost' and r['method']=='static_abs' and r['horizon_minutes']==10 and r['origin_time'] in keys],key=lambda r:r['target_time'])
    ax.fill_between([datetime.fromisoformat(r['target_time']) for r in band],[r['lower_kw'] for r in band],[r['upper_kw'] for r in band],color=colors['xgboost'],alpha=.12,label='XGBoost static interval')
    ax.set(xlabel='Recorded target timestamp',ylabel='Wind generation (kW)',title='Predeclared first 60 available scoring origins · 10-minute horizon');ax.legend(fontsize=8,ncol=3)
    fig.autofmt_xdate();save(fig,'forecast_interval_example')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for model,color in colors.items():
        part=[r for r in coverage['per_horizon'] if r['model']==model and r['horizon_minutes']==10]
        for row in part:
            axes[0].scatter(row['mean_interval_width_kw'],row['marginal_coverage'],color=color,marker='o',s=35)
            axes[0].annotate(f"{model}/{row['method']}",(row['mean_interval_width_kw'],row['marginal_coverage']),fontsize=6)
            if row['rapid_event_coverage'] is not None:
                axes[1].scatter(row['marginal_coverage'],row['rapid_event_coverage'],color=color,s=35)
    axes[0].set(xlabel='Mean interval width (kW)',ylabel='Marginal coverage',title='10-minute width/coverage trade-off')
    axes[1].set(xlabel='Marginal coverage',ylabel='Rapid-event coverage',title='Offline outcome-defined rapid-event stratum',xlim=(0,1.03),ylim=(0,1.03))
    for ax in axes:ax.grid(alpha=.2)
    save(fig,'conditional_coverage_width')
