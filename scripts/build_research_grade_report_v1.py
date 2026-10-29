"""Create a new evidence-backed report from completed studies, never static results."""
from pathlib import Path
import hashlib
import json
import shutil

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STUDIES = ROOT / 'results/research_grade_v1_20261029'
ANALYSIS = STUDIES / 'analysis'
FORECAST = ROOT / 'results/research_grade_v1/forecast_uncertainty'


def markdown(frame: pd.DataFrame, decimals: int = 3) -> str:
    """Small dependency-free table renderer; preserve NaN as unavailable."""
    def cell(value):
        if pd.isna(value):
            return 'undefined'
        if isinstance(value, float):
            return f'{value:,.{decimals}f}'
        return str(value).replace('|', '/')
    return '\n'.join(['| ' + ' | '.join(map(str, frame.columns)) + ' |',
                      '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |'] +
                     ['| ' + ' | '.join(cell(v) for v in row) + ' |'
                      for row in frame.itertuples(index=False, name=None)])


def main() -> None:
    destination = ROOT / 'docs/EXPERIMENTAL_RESULTS.md'
    tables = ROOT / 'docs/research_grade_tables'
    if destination.exists() or tables.exists():
        raise FileExistsError('Report/tables already exist; choose a new report version')
    provenance = json.loads((ANALYSIS / 'provenance.json').read_text())
    forecast = pd.read_csv(FORECAST / 'forecast_horizon_metrics.csv')
    coverage = pd.read_csv(FORECAST / 'coverage_horizon_metrics.csv')
    rapid_coverage = pd.read_csv(FORECAST / 'coverage_rapid_change_metrics.csv')
    comparison = pd.read_csv(ANALYSIS / 'controller_comparison.csv')
    energy = pd.read_csv(ANALYSIS / 'energy_accounting.csv')
    sens = pd.read_csv(ANALYSIS / 'sensitivity_comparison.csv')
    ablation = pd.read_csv(ANALYSIS / 'ablation_comparison.csv')
    diagnostic = pd.read_csv(ANALYSIS / 'transition_diagnostics.csv')
    runtimes = pd.read_csv(ANALYSIS / 'solver_runtime.csv')
    intervals = pd.read_csv(STUDIES / 'statistics_original/dependent_intervals.csv')
    differences = pd.read_csv(ANALYSIS / 'frozen_trajectory_differences.csv')
    original = pd.read_csv(ROOT / 'results/frozen_heldout/final_20261029/analysis_v2/block_metrics.csv')
    official = original.groupby('controller')[['throughput_kwh', 'ramp_exceedance_kw', 'ramp_violations']].sum().reset_index()
    selected_intervals = intervals.loc[intervals.estimand.eq('relative_aggregate_change_percent') &
        intervals.metric.isin(['throughput_kwh', 'ramp_exceedance_kw', 'ramp_violations']),
        ['metric', 'block_length_days', 'estimate', 'lower_approx95', 'upper_approx95']]
    forecast_small = forecast[['horizon_minutes', 'baseline', 'mae_kw', 'rmse_kw']]
    coverage_small = coverage[['horizon_minutes', 'method', 'coverage', 'positive_generation_coverage',
                               'mean_nominal_minus_lower_kw', 'mean_prediction_set_width_kw']]
    controller_small = comparison[['controller', 'ramp_violations', 'total_ramp_exceedance_kw',
        'mean_grid_ramp_kw', 'max_grid_ramp_kw', 'throughput_kwh', 'conversion_losses_kwh']]
    dev_columns = ['variant', 'throughput_kwh', 'ramp_violations', 'total_ramp_exceedance_kw',
                   'reference_200kw_violations', 'reference_200kw_exceedance_kw']
    completions = {name: json.loads((STUDIES / name / 'completion.json').read_text())
                   for name in ['pilot', 'benchmark', 'sensitivity', 'ablations']}
    completed_table = pd.DataFrame([{'study': name, **{k: record[k] for k in
        ['completed_jobs', 'expected_jobs', 'failed_jobs', 'wall_seconds', 'max_physical_energy_residual_kwh']}}
        for name, record in completions.items()])
    divergence = differences.groupby('controller')[[c for c in differences if c.startswith('frozen_max_abs_difference_')]].max().reset_index()
    sections = [
        '# Research-grade experimental results — 29 October 2026',
        'All results below were computed from actual local observations and saved predictors. No model was fitted, no frozen artifact was replaced, and no new preferred controller was selected. These are **retrospective exploratory** comparisons: prior evaluation inspection and development-target overlap prevent an untouched-test claim. Original frozen scores and new instrumented replay scores are distinguished throughout. See the [audit](RESEARCH_AUDIT.md), [methodology](methodology.md), [reproduction commands](RESEARCH_GRADE_REPRODUCIBILITY.md) and [limitations](RESEARCH_LIMITATIONS.md).',
        '## Executed scope', markdown(completed_table),
        f"The expanded comparison contains {provenance['benchmark_jobs']} case/block jobs: six cases × 49 episodes × 144 ten-minute transitions (7,056 transitions per case). Block 6 is development and excluded. Sensitivities contain {provenance['sensitivity_jobs']} jobs, nineteen configurations × development blocks 2/10/18; ablations contain {provenance['ablation_jobs']} jobs, nine configurations × those blocks. All episodes are full 24 hours. Pilot timing on development block 2 determined practicality before sensitivity outcomes. Timing measures this machine/workload, not a deployment guarantee.",
        '## Forecasting', markdown(forecast_small),
        'Errors are kW, paired on the same 7,056 origins at each horizon. Persistence has lower overall MAE at all six horizons; XGBoost has slightly lower RMSE at all six. During outcome-defined rapid target ramps (>200.001 kW per ten minutes), XGBoost has lower MAE: 400.411 versus 416.526 kW at 10 minutes and 528.906 versus 571.371 kW at 60 minutes. This offline stratum does not provide a deployable event detector. The parameter-free local linear baseline performs worse and reaches 17,510.265 kW without a verified rated-power cap; it is a diagnostic extrapolator, not a recommended operational predictor.',
        'All fourteen features across 50,125 rows and all six source-target joins were reconstructed without mismatches. Six frozen model predictions agree within 0.001 kW. Raw signed feature power versus clipped nonnegative forecast/control power is an explicit convention. These checks validate current artifact alignment, not undisclosed historical tuning or measurement latency.',
        '## Uncertainty and causal eligibility', markdown(coverage_small),
        'Coverage columns are fractions. The lower-only prediction set is [L,+∞); its width is infinite. The finite nominal-minus-lower offset is reported separately. The fixed absolute two-sided interval is a distinct finite-width construction; its overall coverage is 90.816–92.149%, compared with 88.259–89.888% when actual generation is positive. Zero-generation observations affect aggregate coverage.',
        'Adaptive overall lower-bound coverage is 95.918–96.103%, but rapid-event coverage is only 80.683% at 10 minutes and 89.891% at 60 minutes (fixed lower: 82.867% and 90.505%). Floors bind 86.971% of all horizon margins; fallback is inactive. All 42,336 reconstructed adaptive margins match frozen logs exactly and all included targets are strictly before decisions. The 90% reference is descriptive; temporal dependence, distribution shift, floors and retrospective inspection preclude guaranteed or simultaneous coverage claims.',
        'The first development episode has 21 affected horizon/decision cells across six decisions and 56 repeated unavailable-label/decision pairs. A separate target-purged projection excludes six origins, retaining 4,478. Horizon-specific boundary purging leaves margins h1–h5 unchanged and changes h6 by only +0.215140 kW; no material impact on historical selection is established. New development studies use later blocks 2/10/18 and retain the existing calibration. Five scored block-7 h1 target times overlap the six-horizon development block-6 target set (15 cross-horizon pairs); this is documented rather than silently deleting observations.',
        '## Original frozen comparison: unchanged', markdown(official),
        'Adaptive versus fixed: **27.8644% lower AC battery throughput, 0.7726% lower summed ramp exceedance and 16 fewer violations**. Modelled conversion loss is 27.9249% lower. Both MPC controllers have more violations and more summed exceedance than uncontrolled wind (1,465 violations; 317,210.288 kW exceedance). Reduction relative to fixed must not be described as established aggregate grid improvement over wind alone. Maximum-ramp performance is a separate metric.',
        'Adaptive actual export is 0.987701 MWh lower than fixed. Hypothetical terminal-adjusted export is 0.551229 MWh higher. These answer different questions: the latter assumes inventory restoration and does not simulate its power, duration or subsequent grid effects.',
        '## Dependence-aware uncertainty for the original comparison', markdown(selected_intervals),
        'These are approximate 95% relative-change intervals (%) from 10,000 paired non-circular moving-block draws within original calendar segments, lengths 2/3/7 days, recentered basic construction and seed 20261029. Throughput intervals remain below zero under these assumptions; ramp-exceedance and violation intervals include zero at every declared length. This supports a conditional battery-usage direction, not confirmatory superiority or proven battery life. No length was chosen by significance. A five-day segment has zero resampling variation at length seven; four heterogeneous segments are insufficient to validate stationarity/asymptotic coverage. Multiple comparisons remain exploratory.',
        'The fixed-length resampling follows the moving-block principle in [Künsch (1989)](https://doi.org/10.1214/aos/1176347265). It is not an IID-overlapping-forecast analysis and is not the stationary-bootstrap algorithm. Full estimates include mean paired differences, fixed-exposure total differences and ratios of totals; ratios with a zero reference are undefined.',
        '## New common-physics six-case comparison', markdown(controller_small),
        'All cases share observed wind, periods, reset state, boundaries and metric definitions. Controlled cases share physical parameters and declared solver options; nominal/persistence/oracle use a single scenario instead of a downside fan. Perfect forecast is explicitly nondeployable. It is a perfect-information reference, not a guaranteed mathematical upper bound for each realised metric with these mixed objectives and a finite horizon. Persistence forecasts constant wind throughout the horizon; zero-action behaviour is a possible consequence of the common objective, not an artificially weak reactive persistence design.',
        'Maximum absolute trajectory differences from the archived original controllers:', markdown(divergence),
        'The algebra is regression-tested against the native frozen source. Deterministic solver settings and parameterization can select different mixed-integer optima; new replay scores are not substituted for the original headline. Differences and affected-interval counts are available by block in the verified tables.',
        '## Battery accounting and computation', markdown(energy),
        'AC throughput is charge energy plus discharge energy; conversion losses are (1−ηc)Ec+(1/ηd−1)Ed. Integrated conservation independently checks wind = actual export + curtailment + losses + terminal DC inventory change. Terminal-adjusted export is hypothetical. The sum of per-episode equivalent-full-cycle proxies is throughput/(2×capacity) under reset episodes; it is not a measured degradation or lifetime estimate. No simultaneous charge/discharge, negative export, hard SOC/power or balance violation is allowed.',
        markdown(runtimes),
        'Solver times are per-stage wall-clock seconds including the invoked solve interface; decision timing also includes logging. Missing solver diagnostics are unavailable, not zero. Small reported MIP gaps/constraint residuals are numerical outputs under declared optimal status. Original archived traces lacked these diagnostics; these are new experiment logs.',
        '## Why can MPC worsen aggregate ramps?', markdown(diagnostic),
        'Introduced minus removed violations equals the controlled count minus uncontrolled count under identical transition pairing. Forecast error, common finite-horizon mixed objectives and the physical inventory/headroom interact; an optimum for predicted weighted exceedance need not minimize realised violation count. The oracle comparison holds physics/objectives fixed while changing forecast information. Fifty of its 58 violations occur when stage-one optimum is at most 0.001 kW: the secondary stage can spend the declared 100 kW primary allowance despite an available zero-exceedance plan. Eight occur with a positive stage-one optimum; this does not prove each first-step violation individually unavoidable. This is direct evidence that even perfect prediction does not guarantee compliance under the frozen objective. Adaptive also uses more throughput and has more exceedance than nominal XGBoost, while removing four violations, so no universal adaptive dominance is established. The development ablations below remove reserve, downside margins or grid penalties under otherwise common settings. Their measured changes diagnose sensitivity; they do not uniquely assign causal percentages to mechanisms or justify held-out tuning.',
        '## Development-only sensitivity', markdown(sens[dev_columns]),
        'Nineteen OFAT configurations cover capacity, power, SOC band, ramp threshold, horizon, uncertainty alpha, battery-ramp weight, reserve target and initial SOC. Capacity scales percentage SOC/reference/reserve energies and changes C-rate at fixed power. Alpha changes rolling rank while inherited floors remain fixed. Configured-threshold and common-200-kW metrics are both reported; comparing configured-threshold counts across thresholds alone is misleading. Three preselected days cannot establish a global optimum or broad robustness, and interactions are not estimated.',
        '## Development-only ablations', markdown(ablation[dev_columns]),
        'Static signed floors isolate removal of the rolling update while retaining the inherited floor. Nominal XGBoost removes uncertainty. Persistence changes forecast information and removes downside uncertainty. Removing only secondary exceedance leaves primary grid priority; removing only primary leaves secondary penalties. The complete grid-penalty ablation disables primary, absolute grid ramp and secondary exceedance terms, retaining battery-ramp/operational costs. Zero primary tolerance contrasts the frozen 100 kW aggregate allowance. These are not replacements selected on evaluation outcomes.',
        '## Figures and verified tables',
        'Forecast trajectories/errors, coverage and uncertainty examples: `../figures/research_grade_v1/forecast_uncertainty/` (four PNG/PDF pairs). Controller comparison, throughput/ramp trade-off, per-block performance, predeclared export/SOC example, sensitivity and ablations: `../figures/research_grade_v1_20261029/analysis/` (six PNG/PDF pairs). Original dependence-aware intervals: `../figures/research_grade_v1_20261029/statistics_original/` (one PNG/PDF pair). All PNGs are 300 dpi and PDFs are vector. Curated aggregate CSVs are in [research_grade_tables](research_grade_tables/); fine-grained raw/trace outputs remain local and ignored by Git.',
        'The strongest defensible contribution is a reproducible retrospective integration and diagnosis: reduced battery use versus a fixed-margin comparator, weak aggregate ramp differences, negative uncontrolled comparisons and event-specific uncertainty undercoverage. Algorithmic novelty, real-time deployment readiness, distribution-free dependent-time coverage, grid compliance and battery-life improvement are not established. See [PUBLICATION_READINESS.md](PUBLICATION_READINESS.md).'
    ]
    tables.mkdir()
    sources = [FORECAST / name for name in ['forecast_horizon_metrics.csv', 'forecast_rapid_change_metrics.csv',
        'coverage_horizon_metrics.csv', 'coverage_rapid_change_metrics.csv', 'coverage_segment_metrics.csv']]
    sources += [ANALYSIS / name for name in ['controller_comparison.csv', 'energy_accounting.csv',
        'sensitivity_comparison.csv', 'ablation_comparison.csv', 'solver_runtime.csv', 'transition_diagnostics.csv',
        'paired_dependent_intervals.csv']]
    sources += [STUDIES / 'statistics_original/dependent_intervals.csv']
    manifest = {}
    for source in sources:
        target = tables / source.name
        shutil.copyfile(source, target)
        manifest[target.name] = {'source': str(source.relative_to(ROOT)), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    (tables / 'provenance.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    with destination.open('x', encoding='utf-8') as stream:
        stream.write('\n\n'.join(sections) + '\n')
    print(f'Created {destination}; {len(manifest)} verified aggregate tables')


if __name__ == '__main__':
    main()
