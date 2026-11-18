# Stage 5 sealed second-site test: Penmanshiel 2023–2024

Episodes: 2067 (paired). Inference unit: ISO week; Wilcoxon on weekly means; CIs from a week-block bootstrap; Holm across all primary tests.

## Primary tests

| Test | Forecast | Claim | Margin | Mean diff [95% CI] | weeks | p (Holm) | Supported |
|---|---|---|---|---|---|---|---|
| S1 | lightgbm_spatial | G reduces ramp exceedance vs no battery | 0.0 | -38.1 [-49.7, -28.5] | 106 | 1.36e-17 | yes |
| S2 | lightgbm_spatial | G uses less throughput than the binary-switch controller P | 0.0 | -82.2 [-92.1, -72.5] | 106 | 9.98e-19 | yes |
| S3 | lightgbm_spatial | G exceedance non-inferior to P (margin 1% of U) | 10.4 | -4.2 [-9.5, +0.8] | 106 | 3.71e-07 | yes |
| S4 | lightgbm_spatial | G uses less throughput than adaptive MPC | 0.0 | -483.9 [-519.6, -446.7] | 106 | 9.98e-19 | yes |
| S5 | persistence | no material harm without skill (margin 5% of U) | 52.1 | +0.0 [+0.0, +0.0] | 106 | 2.21e-24 | yes |
| S6 | lightgbm | no material harm with a weak forecast (margin 5% of U) | 52.1 | -13.3 [-23.1, -5.4] | 106 | 9.98e-19 | yes |

## All controllers

| Forecast | Controller | Change vs none [95% CI] | Throughput kWh/ep | Reduction per 100 kWh | Idle (binary switch) | Safety viol. |
|---|---|---|---|---|---|---|
| persistence | heuristic | +0.00% [+0.00, +0.00] | 0 | 0.00% | 0.00 | 0 |
| persistence | adaptive | +0.02% [-0.15, +0.22] | 198 | -0.01% | 0.00 | 0 |
| persistence | stochastic | +0.03% [-0.30, +0.34] | 65 | -0.05% | 0.00 | 0 |
| persistence | stochastic_skill | +0.00% [+0.00, +0.00] | 0 | 0.00% | 1.00 | 0 |
| persistence | graded_mpc | +0.00% [+0.00, +0.00] | 0 | 0.00% | 0.00 | 0 |
| persistence | lowpass_fast | +0.00% [+0.00, +0.00] | 0 | 0.00% | 0.00 | 0 |
| persistence | graded_lowpass | +0.00% [+0.00, +0.00] | 0 | 0.00% | 0.00 | 0 |
| lightgbm | heuristic | -1.32% [-2.31, -0.43] | 8 | 16.38% | 0.00 | 0 |
| lightgbm | adaptive | -2.95% [-4.02, -1.90] | 510 | 0.58% | 0.00 | 0 |
| lightgbm | stochastic | -1.91% [-3.01, -0.86] | 185 | 1.03% | 0.00 | 0 |
| lightgbm | stochastic_skill | -0.68% [-1.66, +0.22] | 99 | 0.69% | 0.63 | 0 |
| lightgbm | graded_mpc | -1.27% [-2.09, -0.54] | 47 | 2.72% | 0.00 | 0 |
| lightgbm | lowpass_fast | -2.08% [-2.98, -1.25] | 114 | 1.82% | 0.00 | 0 |
| lightgbm | graded_lowpass | -1.34% [-1.95, -0.80] | 38 | 3.53% | 0.00 | 0 |
| lightgbm_spatial | heuristic | -1.31% [-2.16, -0.50] | 10 | 13.68% | 0.00 | 0 |
| lightgbm_spatial | adaptive | -7.01% [-7.87, -6.11] | 574 | 1.22% | 0.00 | 0 |
| lightgbm_spatial | stochastic | -5.24% [-6.08, -4.44] | 261 | 2.01% | 0.00 | 0 |
| lightgbm_spatial | stochastic_skill | -3.26% [-4.13, -2.46] | 173 | 1.88% | 0.52 | 0 |
| lightgbm_spatial | graded_mpc | -3.66% [-4.45, -2.95] | 91 | 4.04% | 0.00 | 0 |
| lightgbm_spatial | lowpass_fast | -5.48% [-6.24, -4.71] | 151 | 3.63% | 0.00 | 0 |
| lightgbm_spatial | graded_lowpass | -3.44% [-3.98, -2.93] | 65 | 5.29% | 0.00 | 0 |
| perfect | heuristic | -97.25% [-98.31, -96.17] | 204 | 47.58% | 0.00 | 0 |
| perfect | adaptive | -99.75% [-99.90, -99.57] | 187 | 53.43% | 0.00 | 0 |
| perfect | stochastic | -99.63% [-99.80, -99.45] | 175 | 57.01% | 0.00 | 0 |
| perfect | stochastic_skill | -99.39% [-99.68, -99.03] | 174 | 57.25% | 0.02 | 0 |
| perfect | graded_mpc | -99.39% [-99.68, -99.03] | 174 | 57.25% | 0.00 | 0 |
| perfect | lowpass_fast | -77.94% [-79.77, -76.16] | 441 | 17.66% | 0.00 | 0 |
| perfect | graded_lowpass | -77.91% [-79.74, -76.13] | 441 | 17.68% | 0.00 | 0 |

## Forecast skill on the evaluation period (secondary)

| Forecast | Decisions | MAE 10â€¦60 min (kW) | Skill vs persistence | Ramp correlation |
|---|---|---|---|---|
| persistence | 102181 | 93 127 148 163 176 187 | +0.000 | +0.00 |
| lightgbm | 102181 | 95 130 150 166 180 191 | +0.116 | +0.23 |
| lightgbm_spatial | 102181 | 93 128 148 164 177 189 | +0.148 | +0.27 |
| perfect | 102181 | 0 0 0 0 0 0 | +1.000 | +1.00 |
