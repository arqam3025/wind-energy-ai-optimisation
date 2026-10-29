"""Exclusive, read-only analysis of completed versioned controller experiments."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .dependent_statistics import paired_uncertainty
from .protocol import ProtocolError, require_new_output_directory

CASES = ('uncontrolled', 'persistence_nominal', 'xgboost_nominal', 'fixed_margin',
         'adaptive_one_sided', 'perfect_forecast_oracle')
LABELS = ('Wind', 'Persistence', 'XGBoost nominal', 'Fixed margin', 'Adaptive', 'Perfect oracle')
COLORS = ('#666666', '#56B4E9', '#009E73', '#D55E00', '#0072B2', '#CC79A7')


def complete_study(directory: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Reject incomplete runs instead of presenting successful subsets as a study."""
    completion = json.loads((directory / 'completion.json').read_text())
    protocol = json.loads((directory / 'protocol.json').read_text())
    if not completion['complete'] or completion['failed_jobs']:
        raise ProtocolError(f'Incomplete experiment: {directory}')
    blocks = pd.read_csv(directory / 'block_metrics.csv')
    aggregate = pd.read_csv(directory / 'aggregate_metrics.csv')
    expected = {(v['variant'], v['controller'], b) for v in protocol['variants'] for b in protocol['blocks']}
    actual = set(blocks[['variant', 'controller', 'block_id']].itertuples(index=False, name=None))
    if actual != expected or len(actual) != len(blocks) or not aggregate.complete.all():
        raise ProtocolError('Missing/duplicated variant-controller-block combination')
    if blocks.soc_violations.sum() or blocks.solver_failures.sum():
        raise ProtocolError('Failed physical or solver validation')
    return blocks, aggregate, protocol


def transition_diagnostics(controlled: pd.DataFrame, wind: pd.DataFrame) -> dict:
    """Pair actual scored transitions, including each episode's first transition."""
    keys = ['block_id', 'timestamp']
    if controlled.duplicated(keys).any() or wind.duplicated(keys).any():
        raise ProtocolError('Duplicate transition')
    aligned = controlled.merge(wind[keys + ['grid_ramp_kw', 'ramp_violation']], on=keys,
                               how='outer', suffixes=('', '_wind'), indicator=True)
    if len(aligned) != len(controlled) or not aligned._merge.eq('both').all():
        raise ProtocolError('Unmatched scored transition')
    violation = aligned.ramp_violation.astype(bool)
    previous = aligned.ramp_violation_wind.astype(bool)
    introduced = int((violation & ~previous).sum())
    removed = int((~violation & previous).sum())
    return {'transitions': len(aligned), 'introduced_violations': introduced,
            'removed_violations': removed, 'net_additional_violations': introduced - removed,
            'ramp_improved_intervals': int((aligned.grid_ramp_kw < aligned.grid_ramp_kw_wind - .001).sum()),
            'ramp_worsened_intervals': int((aligned.grid_ramp_kw > aligned.grid_ramp_kw_wind + .001).sum()),
            'lower_soc_intervals': int((aligned.soc_percent <= 40.0001).sum()) if 'soc_percent' in aligned else 0,
            'upper_soc_intervals': int((aligned.soc_percent >= 89.9999).sum()) if 'soc_percent' in aligned else 0,
            'committed_charge_limited_by_wind_intervals': int((aligned.committed_charge_kw > aligned.charge_kw + .001).sum())
                if 'committed_charge_kw' in aligned else 0}


def run_analysis(root: Path, studies: Path, output: Path, figures: Path) -> dict:
    """Generate tables, paired conditional intervals and publication figures."""
    benchmark, comparison, protocol = complete_study(studies / 'benchmark')
    sensitivity, sens_aggregate, sens_protocol = complete_study(studies / 'sensitivity')
    ablations, ablation_aggregate, ablation_protocol = complete_study(studies / 'ablations')
    if set(benchmark.controller) != set(CASES) or not protocol['full_predeclared_cohort']:
        raise ProtocolError('Expected the complete six-case retrospective cohort')
    require_new_output_directory(output)
    require_new_output_directory(figures)
    schedule = pd.read_csv(root / 'results/evaluation_schedule.csv')
    normalized = benchmark.rename(columns={'total_ramp_exceedance_kw': 'ramp_exceedance_kw',
        'actual_export_kwh': 'export_kwh', 'hypothetical_terminal_adjusted_export_kwh': 'terminal_adjusted_export_kwh'})
    intervals, pairs = [], []
    for case in CASES[1:]:
        interval, paired, _ = paired_uncertainty(normalized.loc[normalized.controller.isin(['uncontrolled', case])],
            schedule, reference='uncontrolled', comparison=case)
        intervals.append(interval)
        pairs.append(paired.assign(reference='uncontrolled', comparison=case))
    pd.concat(intervals).to_csv(output / 'paired_dependent_intervals.csv', index=False, mode='x')
    pd.concat(pairs).to_csv(output / 'paired_block_differences.csv', index=False, mode='x')
    comparison.to_csv(output / 'controller_comparison.csv', index=False, mode='x')
    sens_aggregate.to_csv(output / 'sensitivity_comparison.csv', index=False, mode='x')
    ablation_aggregate.to_csv(output / 'ablation_comparison.csv', index=False, mode='x')
    diagnostic_rows, runtimes, traces = [], [], {}
    for case in CASES:
        trace = pd.concat([pd.read_csv(studies / f'benchmark/base/{case}/block_{b:02d}_trace.csv')
                           for b in protocol['blocks']], ignore_index=True)
        traces[case] = trace
        if case == 'uncontrolled':
            continue
        diagnostic_rows.append({'controller': case, **transition_diagnostics(trace, traces['uncontrolled']),
            'violations_with_near_zero_primary_optimum': int((trace.ramp_violation.astype(bool) &
                trace.stage1_objective.le(.001)).sum()),
            'violations_with_positive_primary_optimum': int((trace.ramp_violation.astype(bool) &
                trace.stage1_objective.gt(.001)).sum())})
        for stage in ('stage1', 'stage2'):
            times = trace[f'{stage}_wall_seconds']
            runtimes.append({'controller': case, 'stage': stage, 'decisions': len(trace),
                'median_seconds': times.median(), 'p95_seconds': times.quantile(.95), 'max_seconds': times.max(),
                'nonoptimal_decisions': int(trace[f'{stage}_status'].ne('optimal').sum()),
                'available_mip_gaps': int(trace[f'{stage}_mip_gap'].notna().sum()),
                'max_reported_mip_gap': trace[f'{stage}_mip_gap'].max()})
    pd.DataFrame(diagnostic_rows).to_csv(output / 'transition_diagnostics.csv', index=False, mode='x')
    pd.DataFrame(runtimes).to_csv(output / 'solver_runtime.csv', index=False, mode='x')
    divergence = benchmark.loc[benchmark.controller.isin(['fixed_margin', 'adaptive_one_sided']),
        ['block_id', 'controller'] + [c for c in benchmark if c.startswith('frozen_')]]
    divergence.to_csv(output / 'frozen_trajectory_differences.csv', index=False, mode='x')
    energy_columns = ['variant', 'controller', 'charge_energy_kwh', 'discharge_energy_kwh', 'throughput_kwh',
        'conversion_losses_kwh', 'curtailment_kwh', 'actual_export_kwh', 'hypothetical_terminal_adjusted_export_kwh']
    energy = comparison[energy_columns].merge(benchmark.groupby('controller', as_index=False).agg(
        terminal_inventory_change_kwh=('terminal_inventory_change_kwh', lambda v: v.sum(min_count=1)),
        equivalent_full_cycle_proxy=('equivalent_full_cycle_proxy', lambda v: v.sum(min_count=1))), on='controller')
    energy.to_csv(output / 'energy_accounting.csv', index=False, mode='x')
    _plots(comparison, benchmark, sens_aggregate, ablation_aggregate, traces, figures)
    sources = [studies / study / filename for study in ('benchmark', 'sensitivity', 'ablations')
               for filename in ('completion.json', 'protocol.json', 'block_metrics.csv', 'aggregate_metrics.csv')]
    record = {'scope': 'New versioned exploratory retrospective study, not replacement frozen scores',
        'benchmark_jobs': len(benchmark), 'sensitivity_jobs': len(sensitivity), 'ablation_jobs': len(ablations),
        'sensitivity_development_blocks': sens_protocol['blocks'], 'ablation_development_blocks': ablation_protocol['blocks'],
        'warnings': ['Repeated initial SOC per episode', 'Oracle is not a guaranteed upper bound on every metric',
            'Approximate within-segment stationary moving-block intervals; all lengths 2/3/7 published',
            'Fixed exposure and 49 paired episodes; no IID overlapping-horizon significance tests',
            'Exploratory runtime includes logging and differs from a real-time deployment benchmark',
            'Terminal-adjusted export is hypothetical inventory restoration, not measured export'],
        'source_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    with (output / 'provenance.json').open('x') as stream:
        json.dump(record, stream, indent=2)
    return record


def _plots(comparison, benchmark, sensitivity, ablations, traces, directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'pdf.fonttype': 42, 'savefig.dpi': 300})
    def save(fig, name):
        fig.tight_layout()
        fig.savefig(directory / f'{name}.png', bbox_inches='tight')
        fig.savefig(directory / f'{name}.pdf', bbox_inches='tight')
        plt.close(fig)
    table = comparison.set_index('controller').loc[list(CASES)]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.3))
    for ax, metric, label, scale in zip(axes,
            ['total_ramp_exceedance_kw', 'ramp_violations', 'throughput_kwh'],
            ['Summed exceedance (10³ kW)', 'Violation count', 'AC throughput (MWh)'], [1000, 1, 1000]):
        ax.bar(range(6), table[metric] / scale, color=COLORS)
        ax.set(xticks=range(6), xticklabels=LABELS, ylabel=label)
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', alpha=.2)
    fig.suptitle('Six cases · same 49 retrospective episodes · versioned deterministic solver')
    save(fig, 'six_case_comparison')
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for case, label, color in zip(CASES, LABELS, COLORS):
        row = table.loc[case]
        ax.scatter(row.throughput_kwh / 1000, row.total_ramp_exceedance_kw / 1000, s=70, color=color, label=label)
    ax.set(xlabel='AC battery throughput (MWh)', ylabel='Summed ramp exceedance (10³ kW)')
    ax.legend(fontsize=8); ax.grid(alpha=.2)
    save(fig, 'throughput_ramp_tradeoff')
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for case, label, color in zip(CASES, LABELS, COLORS):
        part = benchmark.loc[benchmark.controller.eq(case)].sort_values('block_id')
        axes[0].plot(part.block_id, part.total_ramp_exceedance_kw / 1000, color=color, lw=1, label=label)
        axes[1].plot(part.block_id, part.throughput_kwh, color=color, lw=1)
    axes[0].set(ylabel='Exceedance (10³ kW)'); axes[0].legend(ncol=3, fontsize=8)
    axes[1].set(xlabel='Scheduled block ID (6 excluded; states reset per episode)', ylabel='Throughput (kWh)')
    save(fig, 'paired_block_performance')
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for case, label, color in zip(CASES, LABELS, COLORS):
        part = traces[case].loc[traces[case].block_id.eq(1)]
        axes[0].plot(pd.to_datetime(part.timestamp), part.grid_export_kw, color=color, lw=1, label=label)
        if case != 'uncontrolled':
            axes[1].plot(pd.to_datetime(part.timestamp), part.soc_percent, color=color, lw=1)
    axes[0].set(ylabel='Grid export (kW)', title='Predeclared example: first scheduled evaluation block')
    axes[0].legend(ncol=3, fontsize=8)
    axes[1].axhline(40, ls='--', color='gray'); axes[1].axhline(90, ls='--', color='gray')
    axes[1].set(ylabel='Battery SOC (%)', xlabel='Historical timestamp (dataset timezone unverified)')
    fig.autofmt_xdate(); save(fig, 'export_soc_example')
    for part, name, title in [(sensitivity, 'development_sensitivity', 'Development-only OFAT sensitivity'),
                              (ablations, 'development_ablations', 'Development-only ablations')]:
        part = part.sort_values('variant')
        base = part.loc[part.variant.eq('base')].iloc[0]
        fig, axes = plt.subplots(1, 2, figsize=(12, max(4.5, len(part) * .27)))
        for ax, metric, label in zip(axes, ['throughput_kwh', 'reference_200kw_exceedance_kw'],
                                    ['Throughput change (kWh)', 'Exceedance change at common 200 kW (kW)']):
            delta = part[metric] - base[metric]
            ax.barh(range(len(part)), delta, color=['#0072B2' if v <= 0 else '#D55E00' for v in delta])
            ax.axvline(0, color='gray', lw=1)
            ax.set(yticks=range(len(part)), yticklabels=part.variant if ax is axes[0] else [], xlabel=label)
        fig.suptitle(f'{title} · three predeclared 24-hour episodes; no generalisation claim')
        save(fig, name)
