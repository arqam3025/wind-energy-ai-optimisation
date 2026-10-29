# Research-grade experimental results — 29 October 2026

All results below were computed from actual local observations and saved predictors. No model was fitted, no frozen artifact was replaced, and no new preferred controller was selected. These are **retrospective exploratory** comparisons: prior evaluation inspection and development-target overlap prevent an untouched-test claim. Original frozen scores and new instrumented replay scores are distinguished throughout. See the [audit](RESEARCH_AUDIT.md), [methodology](methodology.md), [reproduction commands](RESEARCH_GRADE_REPRODUCIBILITY.md) and [limitations](RESEARCH_LIMITATIONS.md).

## Executed scope

| study | completed_jobs | expected_jobs | failed_jobs | wall_seconds | max_physical_energy_residual_kwh |
| --- | --- | --- | --- | --- | --- |
| pilot | 6 | 6 | 0 | 25.403 | 0.000 |
| benchmark | 294 | 294 | 0 | 358.074 | 0.000 |
| sensitivity | 57 | 57 | 0 | 105.620 | 0.000 |
| ablations | 27 | 27 | 0 | 39.991 | 0.000 |

The expanded comparison contains 294 case/block jobs: six cases × 49 episodes × 144 ten-minute transitions (7,056 transitions per case). Block 6 is development and excluded. Sensitivities contain 57 jobs, nineteen configurations × development blocks 2/10/18; ablations contain 27 jobs, nine configurations × those blocks. All episodes are full 24 hours. Pilot timing on development block 2 determined practicality before sensitivity outcomes. Timing measures this machine/workload, not a deployment guarantee.

## Forecasting

| horizon_minutes | baseline | mae_kw | rmse_kw |
| --- | --- | --- | --- |
| 10 | xgboost | 128.388 | 227.070 |
| 10 | persistence | 120.122 | 227.234 |
| 10 | local_linear | 169.955 | 323.687 |
| 20 | xgboost | 184.849 | 313.187 |
| 20 | persistence | 169.411 | 313.811 |
| 20 | local_linear | 295.427 | 545.903 |
| 30 | xgboost | 222.971 | 367.173 |
| 30 | persistence | 203.445 | 372.805 |
| 30 | local_linear | 408.329 | 747.573 |
| 40 | xgboost | 248.113 | 403.508 |
| 40 | persistence | 228.966 | 415.037 |
| 40 | local_linear | 504.768 | 921.109 |
| 50 | xgboost | 275.550 | 440.551 |
| 50 | persistence | 251.946 | 453.165 |
| 50 | local_linear | 598.241 | 1,092.204 |
| 60 | xgboost | 299.455 | 472.869 |
| 60 | persistence | 270.685 | 485.127 |
| 60 | local_linear | 684.174 | 1,254.952 |

Errors are kW, paired on the same 7,056 origins at each horizon. Persistence has lower overall MAE at all six horizons; XGBoost has slightly lower RMSE at all six. During outcome-defined rapid target ramps (>200.001 kW per ten minutes), XGBoost has lower MAE: 400.411 versus 416.526 kW at 10 minutes and 528.906 versus 571.371 kW at 60 minutes. This offline stratum does not provide a deployable event detector. The parameter-free local linear baseline performs worse and reaches 17,510.265 kW without a verified rated-power cap; it is a diagnostic extrapolator, not a recommended operational predictor.

All fourteen features across 50,125 rows and all six source-target joins were reconstructed without mismatches. Six frozen model predictions agree within 0.001 kW. Raw signed feature power versus clipped nonnegative forecast/control power is an explicit convention. These checks validate current artifact alignment, not undisclosed historical tuning or measurement latency.

## Uncertainty and causal eligibility

| horizon_minutes | method | coverage | positive_generation_coverage | mean_nominal_minus_lower_kw | mean_prediction_set_width_kw |
| --- | --- | --- | --- | --- | --- |
| 10 | fixed_absolute_lower | 0.964 | 0.954 | 293.643 | inf |
| 10 | adaptive_signed_lower | 0.960 | 0.948 | 274.490 | inf |
| 10 | fixed_absolute_two_sided | 0.921 | 0.899 | 293.643 | 693.657 |
| 20 | fixed_absolute_lower | 0.962 | 0.952 | 388.997 | inf |
| 20 | adaptive_signed_lower | 0.961 | 0.950 | 376.169 | inf |
| 20 | fixed_absolute_two_sided | 0.915 | 0.891 | 388.997 | 925.117 |
| 30 | fixed_absolute_lower | 0.962 | 0.952 | 439.506 | inf |
| 30 | adaptive_signed_lower | 0.960 | 0.949 | 425.948 | inf |
| 30 | fixed_absolute_two_sided | 0.908 | 0.883 | 439.506 | 1,047.868 |
| 40 | fixed_absolute_lower | 0.964 | 0.954 | 484.137 | inf |
| 40 | adaptive_signed_lower | 0.959 | 0.949 | 465.728 | inf |
| 40 | fixed_absolute_two_sided | 0.912 | 0.888 | 484.137 | 1,158.106 |
| 50 | fixed_absolute_lower | 0.961 | 0.952 | 520.311 | inf |
| 50 | adaptive_signed_lower | 0.960 | 0.950 | 508.703 | inf |
| 50 | fixed_absolute_two_sided | 0.909 | 0.885 | 520.311 | 1,248.268 |
| 60 | fixed_absolute_lower | 0.963 | 0.954 | 559.796 | inf |
| 60 | adaptive_signed_lower | 0.960 | 0.950 | 540.108 | inf |
| 60 | fixed_absolute_two_sided | 0.911 | 0.887 | 559.796 | 1,346.409 |

Coverage columns are fractions. The lower-only prediction set is [L,+∞); its width is infinite. The finite nominal-minus-lower offset is reported separately. The fixed absolute two-sided interval is a distinct finite-width construction; its overall coverage is 90.816–92.149%, compared with 88.259–89.888% when actual generation is positive. Zero-generation observations affect aggregate coverage.

Adaptive overall lower-bound coverage is 95.918–96.103%, but rapid-event coverage is only 80.683% at 10 minutes and 89.891% at 60 minutes (fixed lower: 82.867% and 90.505%). Floors bind 86.971% of all horizon margins; fallback is inactive. All 42,336 reconstructed adaptive margins match frozen logs exactly and all included targets are strictly before decisions. The 90% reference is descriptive; temporal dependence, distribution shift, floors and retrospective inspection preclude guaranteed or simultaneous coverage claims.

The first development episode has 21 affected horizon/decision cells across six decisions and 56 repeated unavailable-label/decision pairs. A separate target-purged projection excludes six origins, retaining 4,478. Horizon-specific boundary purging leaves margins h1–h5 unchanged and changes h6 by only +0.215140 kW; no material impact on historical selection is established. New development studies use later blocks 2/10/18 and retain the existing calibration. Five scored block-7 h1 target times overlap the six-horizon development block-6 target set (15 cross-horizon pairs); this is documented rather than silently deleting observations.

## Original frozen comparison: unchanged

| controller | throughput_kwh | ramp_exceedance_kw | ramp_violations |
| --- | --- | --- | --- |
| adaptive_one_sided | 25,598.677 | 323,638.526 | 1486 |
| fixed | 35,486.898 | 326,158.296 | 1502 |

Adaptive versus fixed: **27.8644% lower AC battery throughput, 0.7726% lower summed ramp exceedance and 16 fewer violations**. Modelled conversion loss is 27.9249% lower. Both MPC controllers have more violations and more summed exceedance than uncontrolled wind (1,465 violations; 317,210.288 kW exceedance). Reduction relative to fixed must not be described as established aggregate grid improvement over wind alone. Maximum-ramp performance is a separate metric.

Adaptive actual export is 0.987701 MWh lower than fixed. Hypothetical terminal-adjusted export is 0.551229 MWh higher. These answer different questions: the latter assumes inventory restoration and does not simulate its power, duration or subsequent grid effects.

## Dependence-aware uncertainty for the original comparison

| metric | block_length_days | estimate | lower_approx95 | upper_approx95 |
| --- | --- | --- | --- | --- |
| throughput_kwh | 2 | -27.864 | -38.392 | -17.291 |
| ramp_exceedance_kw | 2 | -0.773 | -1.855 | 0.285 |
| ramp_violations | 2 | -1.065 | -2.918 | 0.756 |
| throughput_kwh | 3 | -27.864 | -37.308 | -18.137 |
| ramp_exceedance_kw | 3 | -0.773 | -1.810 | 0.264 |
| ramp_violations | 3 | -1.065 | -2.856 | 0.621 |
| throughput_kwh | 7 | -27.864 | -33.166 | -22.684 |
| ramp_exceedance_kw | 7 | -0.773 | -1.604 | 0.136 |
| ramp_violations | 7 | -1.065 | -2.261 | 0.188 |

These are approximate 95% relative-change intervals (%) from 10,000 paired non-circular moving-block draws within original calendar segments, lengths 2/3/7 days, recentered basic construction and seed 20261029. Throughput intervals remain below zero under these assumptions; ramp-exceedance and violation intervals include zero at every declared length. This supports a conditional battery-usage direction, not confirmatory superiority or proven battery life. No length was chosen by significance. A five-day segment has zero resampling variation at length seven; four heterogeneous segments are insufficient to validate stationarity/asymptotic coverage. Multiple comparisons remain exploratory.

The fixed-length resampling follows the moving-block principle in [Künsch (1989)](https://doi.org/10.1214/aos/1176347265). It is not an IID-overlapping-forecast analysis and is not the stationary-bootstrap algorithm. Full estimates include mean paired differences, fixed-exposure total differences and ratios of totals; ratios with a zero reference are undefined.

## New common-physics six-case comparison

| controller | ramp_violations | total_ramp_exceedance_kw | mean_grid_ramp_kw | max_grid_ramp_kw | throughput_kwh | conversion_losses_kwh |
| --- | --- | --- | --- | --- | --- | --- |
| adaptive_one_sided | 1486 | 323,638.526 | 123.654 | 2,132.655 | 25,598.593 | 1,312.912 |
| fixed_margin | 1502 | 326,158.296 | 124.344 | 2,174.275 | 35,486.898 | 1,821.593 |
| perfect_forecast_oracle | 58 | 6,040.441 | 37.213 | 912.484 | 126,278.045 | 6,466.993 |
| persistence_nominal | 1465 | 317,210.288 | 120.122 | 2,318.176 | 0.000 | 0.000 |
| uncontrolled | 1465 | 317,210.288 | 120.122 | 2,318.176 | 0.000 | 0.000 |
| xgboost_nominal | 1490 | 321,992.007 | 123.014 | 2,154.877 | 21,168.674 | 1,083.630 |

All cases share observed wind, periods, reset state, boundaries and metric definitions. Controlled cases share physical parameters and declared solver options; nominal/persistence/oracle use a single scenario instead of a downside fan. Perfect forecast is explicitly nondeployable. It is a perfect-information reference, not a guaranteed mathematical upper bound for each realised metric with these mixed objectives and a finite horizon. Persistence forecasts constant wind throughout the horizon; zero-action behaviour is a possible consequence of the common objective, not an artificially weak reactive persistence design.

Maximum absolute trajectory differences from the archived original controllers:

| controller | frozen_max_abs_difference_charge_kw | frozen_max_abs_difference_discharge_kw | frozen_max_abs_difference_grid_export_kw | frozen_max_abs_difference_soc_percent |
| --- | --- | --- | --- | --- |
| adaptive_one_sided | 0.264 | 0.238 | 0.264 | 0.002 |
| fixed_margin | 0.000 | 0.000 | 0.000 | 0.000 |

The algebra is regression-tested against the native frozen source. Deterministic solver settings and parameterization can select different mixed-integer optima; new replay scores are not substituted for the original headline. Differences and affected-interval counts are available by block in the verified tables.

## Battery accounting and computation

| variant | controller | charge_energy_kwh | discharge_energy_kwh | throughput_kwh | conversion_losses_kwh | curtailment_kwh | actual_export_kwh | hypothetical_terminal_adjusted_export_kwh | terminal_inventory_change_kwh | equivalent_full_cycle_proxy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base | adaptive_one_sided | 13,065.437 | 12,533.157 | 25,598.593 | 1,312.912 | 33.385 | 1,800,395.606 | 1,799,572.822 | -780.632 | 6.400 |
| base | fixed_margin | 17,532.433 | 17,954.465 | 35,486.898 | 1,821.593 | 0.000 | 1,801,383.303 | 1,799,021.589 | -2,243.625 | 8.872 |
| base | perfect_forecast_oracle | 68,103.673 | 58,174.372 | 126,278.045 | 6,466.993 | 1,233.388 | 1,789,798.582 | 1,793,087.775 | 3,462.308 | 31.570 |
| base | persistence_nominal | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1,800,961.271 | 1,800,961.271 | 0.000 | 0.000 |
| base | uncontrolled | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1,800,961.271 | 1,800,961.271 | undefined | undefined |
| base | xgboost_nominal | 11,594.157 | 9,574.517 | 21,168.674 | 1,083.630 | 0.000 | 1,798,941.631 | 1,799,830.841 | 936.010 | 5.292 |

AC throughput is charge energy plus discharge energy; conversion losses are (1−ηc)Ec+(1/ηd−1)Ed. Integrated conservation independently checks wind = actual export + curtailment + losses + terminal DC inventory change. Terminal-adjusted export is hypothetical. The sum of per-episode equivalent-full-cycle proxies is throughput/(2×capacity) under reset episodes; it is not a measured degradation or lifetime estimate. No simultaneous charge/discharge, negative export, hard SOC/power or balance violation is allowed.

| controller | stage | decisions | median_seconds | p95_seconds | max_seconds | nonoptimal_decisions | available_mip_gaps | max_reported_mip_gap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| persistence_nominal | stage1 | 7056 | 0.009 | 0.011 | 0.028 | 0 | 7056 | 0.000 |
| persistence_nominal | stage2 | 7056 | 0.009 | 0.011 | 0.321 | 0 | 7056 | 0.000 |
| xgboost_nominal | stage1 | 7056 | 0.010 | 0.012 | 0.322 | 0 | 7056 | 0.000 |
| xgboost_nominal | stage2 | 7056 | 0.019 | 0.029 | 0.068 | 0 | 7056 | 0.000 |
| fixed_margin | stage1 | 7056 | 0.011 | 0.035 | 0.107 | 0 | 7056 | 0.000 |
| fixed_margin | stage2 | 7056 | 0.024 | 0.034 | 0.155 | 0 | 7056 | 0.000 |
| adaptive_one_sided | stage1 | 7056 | 0.010 | 0.014 | 0.036 | 0 | 7056 | 0.000 |
| adaptive_one_sided | stage2 | 7056 | 0.023 | 0.034 | 0.132 | 0 | 7056 | 0.000 |
| perfect_forecast_oracle | stage1 | 7056 | 0.009 | 0.012 | 0.017 | 0 | 7056 | 0.000 |
| perfect_forecast_oracle | stage2 | 7056 | 0.013 | 0.029 | 0.095 | 0 | 7056 | 0.000 |

Solver times are per-stage wall-clock seconds including the invoked solve interface; decision timing also includes logging. Missing solver diagnostics are unavailable, not zero. Small reported MIP gaps/constraint residuals are numerical outputs under declared optimal status. Original archived traces lacked these diagnostics; these are new experiment logs.

## Why can MPC worsen aggregate ramps?

| controller | transitions | introduced_violations | removed_violations | net_additional_violations | ramp_improved_intervals | ramp_worsened_intervals | lower_soc_intervals | upper_soc_intervals | committed_charge_limited_by_wind_intervals | violations_with_near_zero_primary_optimum | violations_with_positive_primary_optimum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| persistence_nominal | 7056 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1465 | 0 |
| xgboost_nominal | 7056 | 116 | 91 | 25 | 1549 | 2343 | 0 | 0 | 69 | 1475 | 15 |
| fixed_margin | 7056 | 166 | 129 | 37 | 1892 | 2981 | 0 | 0 | 152 | 291 | 1211 |
| adaptive_one_sided | 7056 | 134 | 113 | 21 | 1369 | 1928 | 0 | 0 | 85 | 1081 | 405 |
| perfect_forecast_oracle | 7056 | 18 | 1425 | -1407 | 4476 | 1343 | 0 | 1 | 0 | 50 | 8 |

Introduced minus removed violations equals the controlled count minus uncontrolled count under identical transition pairing. Forecast error, common finite-horizon mixed objectives and the physical inventory/headroom interact; an optimum for predicted weighted exceedance need not minimize realised violation count. The oracle comparison holds physics/objectives fixed while changing forecast information. Fifty of its 58 violations occur when stage-one optimum is at most 0.001 kW: the secondary stage can spend the declared 100 kW primary allowance despite an available zero-exceedance plan. Eight occur with a positive stage-one optimum; this does not prove each first-step violation individually unavoidable. This is direct evidence that even perfect prediction does not guarantee compliance under the frozen objective. Adaptive also uses more throughput and has more exceedance than nominal XGBoost, while removing four violations, so no universal adaptive dominance is established. The development ablations below remove reserve, downside margins or grid penalties under otherwise common settings. Their measured changes diagnose sensitivity; they do not uniquely assign causal percentages to mechanisms or justify held-out tuning.

## Development-only sensitivity

| variant | throughput_kwh | ramp_violations | total_ramp_exceedance_kw | reference_200kw_violations | reference_200kw_exceedance_kw |
| --- | --- | --- | --- | --- | --- |
| alpha_0p05 | 4,919.151 | 186 | 42,021.521 | 186 | 42,021.521 |
| alpha_0p2 | 2,920.913 | 181 | 40,801.584 | 181 | 40,801.584 |
| base | 3,422.631 | 184 | 40,813.967 | 184 | 40,813.967 |
| battery_ramp_weight_0p0 | 3,422.631 | 184 | 40,813.967 | 184 | 40,813.967 |
| battery_ramp_weight_1p0 | 3,405.367 | 184 | 40,800.579 | 184 | 40,800.579 |
| capacity_kwh_1000p0 | 2,586.512 | 182 | 40,967.366 | 182 | 40,967.366 |
| capacity_kwh_4000p0 | 4,665.947 | 186 | 40,877.908 | 186 | 40,877.908 |
| horizon_1 | 6,417.827 | 192 | 44,543.832 | 192 | 44,543.832 |
| horizon_3 | 3,491.990 | 184 | 40,297.602 | 184 | 40,297.602 |
| initial_soc_percent_40p0 | 3,900.321 | 183 | 40,802.716 | 183 | 40,802.716 |
| initial_soc_percent_70p0 | 4,644.757 | 188 | 42,412.812 | 188 | 42,412.812 |
| max_power_kw_1500p0 | 3,422.631 | 184 | 40,813.967 | 184 | 40,813.967 |
| max_power_kw_500p0 | 3,521.753 | 186 | 41,516.408 | 186 | 41,516.408 |
| ramp_limit_kw_100p0 | 4,392.659 | 280 | 63,258.936 | 182 | 40,347.055 |
| ramp_limit_kw_400p0 | 2,744.044 | 70 | 16,550.924 | 177 | 39,474.238 |
| reserve_soc_percent_40p0 | 3,167.250 | 189 | 42,565.418 | 189 | 42,565.418 |
| reserve_soc_percent_60p0 | 5,176.540 | 186 | 40,781.850 | 186 | 40,781.850 |
| soc_band_20p0_90p0 | 5,776.155 | 183 | 41,688.085 | 183 | 41,688.085 |
| soc_band_40p0_70p0 | 3,422.631 | 184 | 40,813.967 | 184 | 40,813.967 |

Nineteen OFAT configurations cover capacity, power, SOC band, ramp threshold, horizon, uncertainty alpha, battery-ramp weight, reserve target and initial SOC. Capacity scales percentage SOC/reference/reserve energies and changes C-rate at fixed power. Alpha changes rolling rank while inherited floors remain fixed. Configured-threshold and common-200-kW metrics are both reported; comparing configured-threshold counts across thresholds alone is misleading. Three preselected days cannot establish a global optimum or broad robustness, and interactions are not estimated.

## Development-only ablations

| variant | throughput_kwh | ramp_violations | total_ramp_exceedance_kw | reference_200kw_violations | reference_200kw_exceedance_kw |
| --- | --- | --- | --- | --- | --- |
| adaptive_floors_only | 2,920.913 | 181 | 40,801.584 | 181 | 40,801.584 |
| base | 3,422.631 | 184 | 40,813.967 | 184 | 40,813.967 |
| no_grid_penalties | 0.000 | 175 | 38,194.203 | 175 | 38,194.203 |
| no_primary_stage | 2,010.350 | 184 | 40,506.938 | 184 | 40,506.938 |
| no_reserve_penalty | 3,167.250 | 189 | 42,565.418 | 189 | 42,565.418 |
| no_secondary_exceedance_penalty | 3,900.844 | 190 | 40,613.237 | 190 | 40,613.237 |
| persistence_nominal | 0.000 | 175 | 38,194.203 | 175 | 38,194.203 |
| xgboost_nominal | 2,678.902 | 184 | 40,472.796 | 184 | 40,472.796 |
| zero_primary_tolerance | 3,979.313 | 189 | 42,735.778 | 189 | 42,735.778 |

Static signed floors isolate removal of the rolling update while retaining the inherited floor. Nominal XGBoost removes uncertainty. Persistence changes forecast information and removes downside uncertainty. Removing only secondary exceedance leaves primary grid priority; removing only primary leaves secondary penalties. The complete grid-penalty ablation disables primary, absolute grid ramp and secondary exceedance terms, retaining battery-ramp/operational costs. Zero primary tolerance contrasts the frozen 100 kW aggregate allowance. These are not replacements selected on evaluation outcomes.

On these three development days, static floors alone use 2,920.913 kWh throughput versus 3,422.631 kWh for rolling-plus-floor adaptation, with 181 versus 184 violations and 40,801.584 versus 40,813.967 kW exceedance. Thus this small ablation does not support a benefit from the rolling update. Removing reserve penalty increases exceedance to 42,565.418 kW; zero primary allowance increases it to 42,735.778 kW. Stronger priority on forecast-based exceedance can therefore worsen realised exceedance in this experiment. With all grid penalties disabled, battery actions are zero and outcomes equal uncontrolled wind: 175 violations and 38,194.203 kW exceedance. Capacity and power changes are not monotonic improvements across these days. No setting is selected from these findings.

## Figures and verified tables

Forecast trajectories/errors, coverage and uncertainty examples: `../figures/research_grade_v1/forecast_uncertainty/` (four PNG/PDF pairs). Controller comparison, throughput/ramp trade-off, per-block performance, predeclared export/SOC example, sensitivity and ablations: `../figures/research_grade_v1_20261029/analysis/` (six PNG/PDF pairs). Original dependence-aware intervals: `../figures/research_grade_v1_20261029/statistics_original/` (one PNG/PDF pair). All PNGs are 300 dpi and PDFs are vector. Curated aggregate CSVs are in [research_grade_tables](research_grade_tables/); fine-grained raw/trace outputs remain local and ignored by Git.

The strongest defensible contribution is a reproducible retrospective integration and diagnosis: reduced battery use versus a fixed-margin comparator, weak aggregate ramp differences, negative uncontrolled comparisons and event-specific uncertainty undercoverage. Algorithmic novelty, real-time deployment readiness, distribution-free dependent-time coverage, grid compliance and battery-life improvement are not established. See [PUBLICATION_READINESS.md](PUBLICATION_READINESS.md).

## Verification history

The complete test suite passed 70 tests before the final independent check. All 384 produced traces, including the six pilot cases, pass post-run physical validation: 55,296 transitions, with maximum integrated energy residual below 1.86×10⁻¹¹ kWh. The repeated adaptive baseline on development blocks 2/10/18 is exactly identical across the sensitivity and ablation runs, excluding timing.

The first independent verifier rejected three future oracle plan rows in block 50: planned discharge of 0.000386–0.000392 kW accompanies planned charging of 122.788–140.368 kW at horizons 50/60 minutes. Its product guard compared kW² against a numeric power tolerance. Actual power overlap is below the engine's declared 0.001 kW numerical constraint tolerance, and all executed actions pass. The failed report is preserved at `audits/research_grade_20261029/final_integrity_verification.json`; the corrected planning-only check uses `min(charge,discharge)` in kW and reports the residual explicitly. No result was altered to make validation pass. Small numerical constraint residuals must not be described as exact mathematical feasibility.

Final verification passes in `audits/research_grade_20261029/final_integrity_verification_v2.json`: manifest plus all 59 references match, all 1,024 protected baseline files match, and the three complete studies independently pass 54,432 transition and 429,408 planning-row checks. All **71 tests pass**, including the new scale-aware planning-tolerance regression. The diagnostic and both verification versions are retained.

Pilot provenance is more limited than the full studies: its earlier MPC/experiment/config bytes were reconstructed and authenticated against saved digests, but the earlier forecast-audit module (edited in figure/provenance code during the pilot) was not archived exactly. Pilot physics and completion are verified; complete pilot source identity is not claimed. All three full studies have exact authenticated executed-source snapshots and are unaffected by this limitation.
