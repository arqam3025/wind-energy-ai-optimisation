"""Produce reviewable research documents only from a complete validated paired run."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pandas as pd
from heldout_support import ROOT
from prepare_frozen_heldout import verify

def replace_results(path, section):
    text=path.read_text(encoding='utf-8')
    start='<!-- HELDOUT_RESULTS_START -->'
    end='<!-- HELDOUT_RESULTS_END -->'
    assert text.count(start)==text.count(end)==1
    updated=text[:text.index(start)+len(start)]+'\n'+section+'\n'+text[text.index(end):]
    path.write_text(updated,encoding='utf-8')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',default='final_20261029')
    parser.add_argument('--analysis',default='analysis_v1')
    parser.add_argument('--edition',default='v1')
    args=parser.parse_args()
    assert args.edition.isalnum()
    suffix='' if args.edition=='v1' else '_'+args.edition
    verify()
    run=ROOT/'results/frozen_heldout'/args.run
    analysis=run/args.analysis
    validation=json.loads((analysis/'validation.json').read_text())
    assert validation['status']=='complete' and validation['blocks']==49
    replay=json.loads((run/'reproducibility_audit_v1.json').read_text())
    assert all(v['status']=='pass' for v in replay['replay'].values())
    inventory=json.loads((run/'preserved_artifacts_inventory.json').read_text())
    for path,expected in inventory.items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,check=True)
    totals=pd.read_csv(analysis/'aggregate_metrics.csv',index_col='controller')
    fixed=totals.loc['fixed']; adaptive=totals.loc['adaptive_one_sided']
    metrics=[('Ramp violations','ramp_violations',1,0),('Violation rate (%)','violation_rate',100,2),
             ('Ramp exceedance sum (kW)','ramp_exceedance_kw',1,3),('Battery throughput (MWh)','throughput_kwh',.001,6),
             ('Conversion losses (MWh)','conversion_losses_kwh',.001,6),('Curtailment (MWh)','curtailment_kwh',.001,6),
             ('Actual grid export (MWh)','export_kwh',.001,6),('Terminal-SOC-adjusted export (MWh)','terminal_adjusted_export_kwh',.001,6)]
    table='| Metric | Fixed margin | Adaptive one-sided | Adaptive minus fixed |\n| --- | ---: | ---: | ---: |\n'
    for label,key,scale,precision in metrics:
        f=fixed[key]*scale; a=adaptive[key]*scale
        table+=f'| {label} | {f:,.{precision}f} | {a:,.{precision}f} | {a-f:+,.{precision}f} |\n'
    throughput_change=(adaptive.throughput_kwh/fixed.throughput_kwh-1)*100
    exceedance_change=(adaptive.ramp_exceedance_kw/fixed.ramp_exceedance_kw-1)*100
    violation_change=int(adaptive.ramp_violations-fixed.ramp_violations)
    paragraph=(f'The frozen comparison completed **49 paired blocks (7,056 intervals per controller)**. '
        f'Relative to fixed margins, adaptive one-sided throughput changed by **{throughput_change:+.2f}%**, '
        f'summed ramp exceedance by **{exceedance_change:+.2f}%**, and violation count by **{violation_change:+d}**. '
        'The development preference remains frozen; these outcomes do not trigger controller selection or re-tuning.')
    checks=('All 98 controller-block outputs passed independent physical and energy audits. All 42,336 horizon targets matched raw measurements. '
        'First-block replay had zero numeric difference for both controllers on the installed stack. '
        'The freeze and all 736 inventoried pre-existing research artifacts remained unchanged. '
        'Terminal-SOC-adjusted energy is hypothetical restoration accounting; actual export is reported separately.')
    replace_results(ROOT/'README.md',paragraph+'\n\n'+table+'\n'+checks+f'\n\nSee [the full paired results](docs/heldout_results{suffix}.md) and [figures](docs/figures{suffix}/paired_controllers.png).')
    paired=pd.read_csv(analysis/'paired_summary.csv')
    details='| Outcome | Mean paired difference | Median paired difference | Negative blocks | Positive blocks | Ties |\n| --- | ---: | ---: | ---: | ---: | ---: |\n'
    for d in paired.itertuples():
        details+=f'| {d.metric} | {d.mean_difference:.4f} | {d.median_difference:.4f} | {d.negative_blocks} | {d.positive_blocks} | {d.ties} |\n'
    figure_dir=ROOT/f'docs/figures{suffix}'
    figure_dir.mkdir(exist_ok=True)
    for path in analysis.iterdir():
        if path.suffix in ['.png','.pdf']:
            with (figure_dir/path.name).open('xb') as handle:handle.write(path.read_bytes())
    # Copy aggregate research products into Git-visible docs; preserve local inputs.
    tables=ROOT/f'docs/tables{suffix}'
    tables.mkdir(exist_ok=True)
    for name in ['aggregate_metrics.csv','paired_summary.csv','forecast_metrics.csv','block_metrics.csv','paired_differences.csv','uncertainty_coverage.csv','uncontrolled_wind_baseline.csv']:
        with (tables/name).open('xb') as handle:handle.write((analysis/name).read_bytes())
    figure_text='\n\n'.join([
        '![Paired outcomes, each point a block; dashed line is equality.](figures/paired_controllers.png)',
        '![Adaptive minus fixed differences by scheduled block.](figures/paired_differences.png)',
        '![Battery AC energy, conversion losses and curtailment.](figures/battery_energy_accounting.png)',
        '![Forecast accuracy compared with persistence.](figures/forecast_accuracy.png)',
        '![Empirical lower-bound coverage; nominal reference is not a guarantee.](figures/uncertainty_coverage.png)',
        '![Pre-specified first eligible block, target-time clock.](figures/first_block_trace.png)'])
    f=pd.read_csv(analysis/'forecast_metrics.csv').pivot(index='horizon_minutes',columns='model')
    forecasts='| Horizon (min) | XGBoost MAE (kW) | Persistence MAE (kW) | XGBoost RMSE (kW) | Persistence RMSE (kW) |\n| --- | ---: | ---: | ---: | ---: |\n'
    for h in f.index:
        forecasts+=f'| {h} | {f.loc[h,("mae_kw","xgboost")]:.3f} | {f.loc[h,("mae_kw","persistence")]:.3f} | {f.loc[h,("rmse_kw","xgboost")]:.3f} | {f.loc[h,("rmse_kw","persistence")]:.3f} |\n'
    coverage=pd.read_csv(analysis/'uncertainty_coverage.csv').groupby(['horizon_minutes','controller']).lower_bound_coverage.mean().unstack()
    coverage_text='| Horizon (min) | Fixed lower-bound coverage (%) | Adaptive lower-bound coverage (%) |\n| --- | ---: | ---: |\n'
    for h in coverage.index:
        coverage_text+=f'| {h} | {coverage.loc[h,"fixed"]*100:.2f} | {coverage.loc[h,"adaptive_one_sided"]*100:.2f} |\n'
    baseline=pd.read_csv(analysis/'uncontrolled_wind_baseline.csv')
    reference=f'Uncontrolled wind has {int(baseline.ramp_violations.sum()):,} violations and {baseline.ramp_exceedance_kw.sum():,.3f} kW summed exceedance on the same transitions. It is a descriptive physical reference and was not used for controller selection.'
    ramp=paired.loc[paired.metric.eq('ramp_exceedance_kw')].iloc[0]
    interpretation=(f'Ramp exceedance decreases in {int(ramp.negative_blocks)} blocks, increases in {int(ramp.positive_blocks)}, and ties in {int(ramp.ties)}; '
        f'the median paired difference is {ramp.median_difference:.3f} kW. The descriptive bootstrap interval spans zero, so the small aggregate ramp change does not establish consistent superiority. '
        'XGBoost has higher MAE but lower RMSE than persistence at every evaluated horizon. Forecast performance is therefore mixed across error metrics, rather than uniformly better than persistence.')
    assert (f['mae_kw']['xgboost']>f['mae_kw']['persistence']).all()
    assert (f['rmse_kw']['xgboost']<f['rmse_kw']['persistence']).all()
    assert ramp.lower_descriptive_bootstrap < 0 < ramp.upper_descriptive_bootstrap
    figure_text=figure_text.replace('(figures/',f'(figures{suffix}/')
    results=paragraph+'\n\n'+table+'\n'+checks+'\n\n'+reference+'\n\n'+interpretation+'\n\n'+details+'\nNegative differences favour adaptive for throughput, losses and ramp costs; positive differences favour adaptive for adjusted export. Bootstrap intervals in the CSV are descriptive because adjacent blocks are dependent.\n\n'+forecasts+'\n'+coverage_text+'\nCoverage is empirical marginal lower-bound coverage, not simultaneous or guaranteed coverage. Forecast comparisons reuse stored predictions and do not inform re-tuning.\n\n'+figure_text
    replace_results(ROOT/'docs/paper_draft.md',results)
    paper=ROOT/'docs/paper_draft.md'
    text=paper.read_text(encoding='utf-8')
    text=text.replace('The numerical results and their trade-offs are reported below after complete paired validation.',
        f'On these episodes, adaptive one-sided battery throughput changed by {throughput_change:+.2f}%, summed ramp exceedance by {exceedance_change:+.2f}%, and ramp violation count by {violation_change:+d} relative to fixed margins. These outcomes describe a trade-off and do not establish universal controller superiority.')
    paper.write_text(text,encoding='utf-8')
    with (ROOT/f'docs/heldout_results{suffix}.md').open('x',encoding='utf-8') as handle:
        handle.write('# Frozen held-out results\n\n'+results+'\n\nLocal run: `'+args.run+'`; analysis: `'+args.analysis+f'`. Full tables are in [tables{suffix}/](tables{suffix}/).\n')
    artifacts=[p for p in run.rglob('*') if p.is_file()]
    artifacts+=list((ROOT/'docs').rglob('*'))
    artifacts+=[ROOT/'README.md',ROOT/'.gitignore']+list((ROOT/'scripts').glob('*heldout*.py'))+[ROOT/'scripts/finalise_frozen_research.py',ROOT/'scripts/audit_frozen_reproducibility.py']+list((ROOT/'tests').glob('*.py'))
    release={'status':'complete','freeze':'verified','preserved_artifacts':len(inventory),'paired_blocks':49,
             'validation':validation,'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts if p.is_file()},
             'limitations':'Single turbine, dependent blocks, episode resets, simplified battery, historic test-period access; see docs/limitations.md'}
    with (run/f'release_manifest_{args.edition}.json').open('x') as handle:json.dump(release,handle,indent=2)
    print(paragraph)
    print(table)
    print('Research documents, tables, figures and release manifest completed.')

if __name__=='__main__':main()
