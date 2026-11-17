# Stage 3.3 confirmatory: descriptive secondary analyses

Descriptive only (protocol Section 6, items 5 and 7); no tests. Inputs verified by SHA-256.

## Volatility interaction: mean exceedance per scenario (kW)

| Forecast | Volatility | uncontrolled | deterministic | adaptive | stochastic | stochastic_skill |
|---|---|---|---|---|---|---|
| oracle25 | 0.7 | 527 | 35 | 0 | 7 | 10 |
| oracle25 | 1.0 | 1188 | 62 | 2 | 10 | 10 |
| oracle25 | 1.5 | 2737 | 116 | 13 | 20 | 20 |
| oracle50 | 0.7 | 527 | 69 | 6 | 17 | 30 |
| oracle50 | 1.0 | 1188 | 129 | 11 | 26 | 26 |
| oracle50 | 1.5 | 2737 | 213 | 14 | 44 | 44 |
| oracle100 | 0.7 | 527 | 184 | 131 | 133 | 198 |
| oracle100 | 1.0 | 1188 | 326 | 155 | 179 | 177 |
| oracle100 | 1.5 | 2737 | 436 | 174 | 218 | 218 |
| oracle150 | 0.7 | 527 | 436 | 596 | 635 | 537 |
| oracle150 | 1.0 | 1188 | 612 | 627 | 681 | 726 |
| oracle150 | 1.5 | 2737 | 770 | 663 | 748 | 831 |
| oracle200 | 0.7 | 527 | 996 | 1320 | 1135 | 550 |
| oracle200 | 1.0 | 1188 | 1237 | 1344 | 1209 | 1182 |
| oracle200 | 1.5 | 2737 | 1342 | 1451 | 1382 | 1611 |
| persistence | 0.7 | 527 | 527 | 527 | 528 | 527 |
| persistence | 1.0 | 1188 | 1188 | 1190 | 1195 | 1188 |
| persistence | 1.5 | 2737 | 2737 | 2749 | 2770 | 2737 |
| mean_reversion | 0.7 | 527 | 546 | 637 | 586 | 541 |
| mean_reversion | 1.0 | 1188 | 1199 | 1348 | 1296 | 1218 |
| mean_reversion | 1.5 | 2737 | 2880 | 3050 | 3037 | 2807 |
| skill_combo | 0.7 | 527 | 527 | 550 | 540 | 527 |
| skill_combo | 1.0 | 1188 | 1188 | 1263 | 1215 | 1188 |
| skill_combo | 1.5 | 2737 | 2736 | 2882 | 2843 | 2750 |
| damped_trend | 0.7 | 527 | 582 | 867 | 797 | 527 |
| damped_trend | 1.0 | 1188 | 1352 | 1748 | 1712 | 1189 |
| damped_trend | 1.5 | 2737 | 3281 | 3484 | 3632 | 2737 |

## Skill switch: fraction of decisions gated to idle

| Variant | oracle25 | oracle50 | oracle100 | oracle150 | oracle200 | persistence | mean_reversion | skill_combo | damped_trend |
|---|---|---|---|---|---|---|---|---|---|
| stochastic_skill | 0.00 | 0.02 | 0.12 | 0.35 | 0.63 | 1.00 | 0.87 | 0.95 | 0.99 |
| stochastic_skill00 | 0.00 | 0.01 | 0.11 | 0.30 | 0.58 | 1.00 | 0.69 | 0.56 | 0.97 |
| stochastic_skill05 | 0.00 | 0.02 | 0.11 | 0.33 | 0.60 | 1.00 | 0.79 | 0.80 | 0.98 |
| stochastic_skill20 | 0.00 | 0.02 | 0.13 | 0.42 | 0.70 | 1.00 | 0.96 | 1.00 | 1.00 |

## Computation time per decision (ms)

Wall-clock time per decision, averaged within each episode. Mean and max are inflated by operating-system standby during the run (deviation D2); use the median and p95.

| Controller | median | p95 | mean | max |
|---|---|---|---|---|
| uncontrolled | 0.0 | 0.1 | 0.0 | 1.2 |
| deterministic | 12.7 | 34.3 | 1284.2 | 1358041.4 |
| fixed_margin | 17.7 | 44.2 | 22.3 | 114.3 |
| adaptive | 19.1 | 49.1 | 282.8 | 349809.7 |
| heuristic | 0.1 | 0.3 | 0.1 | 1.6 |
| stochastic | 16.0 | 45.1 | 185.5 | 223009.2 |
| stochastic_no_gate | 15.8 | 44.1 | 20.0 | 98.7 |
| stochastic_terminal | 16.7 | 45.6 | 288.7 | 361224.0 |
| point_band_gate | 10.9 | 29.1 | 14.1 | 114.2 |
| stochastic_increments | 17.4 | 49.2 | 22.3 | 164.7 |
| stochastic_skill | 1.0 | 31.8 | 267.9 | 349800.1 |
| stochastic_skill00 | 9.8 | 33.5 | 10.5 | 67.7 |
| stochastic_skill05 | 6.1 | 33.7 | 9.6 | 68.1 |
| stochastic_skill20 | 0.5 | 27.1 | 8.0 | 65.4 |

## Safety and accounting totals (all scenarios)

| Controller | soc_constraint_violations | power_constraint_violations | simultaneous_charge_discharge_events | grid_limit_violations | optimisation_failures | adapter_rejections | max energy residual (kWh) |
|---|---|---|---|---|---|---|---|
| uncontrolled | 0 | 0 | 0 | 0 | 0 | 0 | 0.00e+00 |
| deterministic | 0 | 0 | 0 | 0 | 10 | 0 | 3.60e-12 |
| fixed_margin | 0 | 0 | 0 | 0 | 7 | 0 | 3.79e-12 |
| adaptive | 0 | 0 | 0 | 0 | 37 | 0 | 3.72e-12 |
| heuristic | 0 | 0 | 0 | 0 | 0 | 0 | 4.06e-12 |
| stochastic | 0 | 0 | 0 | 0 | 80 | 0 | 3.21e-12 |
| stochastic_no_gate | 0 | 0 | 0 | 0 | 69 | 0 | 3.21e-12 |
| stochastic_terminal | 0 | 0 | 0 | 0 | 24 | 0 | 3.96e-12 |
| point_band_gate | 0 | 0 | 0 | 0 | 10 | 0 | 3.12e-12 |
| stochastic_increments | 0 | 0 | 0 | 0 | 54 | 0 | 3.81e-12 |
| stochastic_skill | 0 | 0 | 0 | 0 | 26 | 0 | 3.21e-12 |
| stochastic_skill00 | 0 | 0 | 0 | 0 | 31 | 0 | 3.21e-12 |
| stochastic_skill05 | 0 | 0 | 0 | 0 | 31 | 0 | 3.21e-12 |
| stochastic_skill20 | 0 | 0 | 0 | 0 | 23 | 0 | 3.21e-12 |
