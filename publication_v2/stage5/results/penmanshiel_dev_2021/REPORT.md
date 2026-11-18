# Penmanshiel development 2021

Episodes: 1034 (paired). Inference unit: ISO week; Wilcoxon on weekly means; CIs from a week-block bootstrap; Holm across all primary tests.

## Primary tests

| Test | Forecast | Claim | Margin | Mean diff [95% CI] | weeks | p (Holm) | Supported |
|---|---|---|---|---|---|---|---|
| S1 | lightgbm_spatial | G reduces ramp exceedance vs no battery | 0.0 | -32.7 [-43.9, -22.7] | 53 | 2.41e-09 | yes |
| S2 | lightgbm_spatial | G uses less throughput than the binary-switch controller P | 0.0 | -69.0 [-83.9, -54.6] | 53 | 5.92e-10 | yes |
| S3 | lightgbm_spatial | G exceedance non-inferior to P (margin 1% of U) | 9.0 | -3.1 [-7.6, +1.1] | 53 | 2.64e-07 | yes |
| S4 | lightgbm_spatial | G uses less throughput than adaptive MPC | 0.0 | -420.7 [-480.7, -363.5] | 53 | 5.92e-10 | yes |
| S5 | persistence | no material harm without skill (margin 5% of U) | 45.0 | +0.0 [+0.0, +0.0] | 53 | 1.00e-12 | yes |
| S6 | lightgbm | no material harm with a weak forecast (margin 5% of U) | 45.0 | -12.8 [-21.4, -5.9] | 53 | 5.92e-10 | yes |

## All controllers

| Forecast | Controller | Change vs none [95% CI] | Throughput kWh/ep | Reduction per 100 kWh | Idle/scaled | Safety viol. |
|---|---|---|---|---|---|---|
| persistence | heuristic | +0.00% [+0.00, +0.00] | 0 | 0.00% | 0.00 | 0 |
| persistence | adaptive | -0.13% [-0.43, +0.14] | 175 | 0.08% | 0.00 | 0 |
| persistence | stochastic | +0.04% [-0.26, +0.35] | 59 | -0.07% | 0.00 | 0 |
| persistence | stochastic_skill | +0.00% [+0.00, +0.00] | 0 | 0.00% | 1.00 | 0 |
| persistence | graded_mpc | +0.00% [+0.00, +0.00] | 0 | 0.00% | 0.00 | 0 |
| persistence | lowpass_fast | +0.00% [+0.00, +0.00] | 0 | 0.00% | 0.00 | 0 |
| persistence | graded_lowpass | +0.00% [+0.00, +0.00] | 0 | 0.00% | 0.00 | 0 |
| lightgbm | heuristic | -1.42% [-2.78, -0.39] | 5 | 30.95% | 0.00 | 0 |
| lightgbm | adaptive | -3.13% [-4.32, -1.93] | 449 | 0.70% | 0.00 | 0 |
| lightgbm | stochastic | -2.57% [-3.92, -1.32] | 171 | 1.50% | 0.00 | 0 |
| lightgbm | stochastic_skill | -1.06% [-2.08, +0.04] | 92 | 1.16% | 0.67 | 0 |
| lightgbm | graded_mpc | -1.43% [-2.18, -0.73] | 43 | 3.33% | 0.00 | 0 |
| lightgbm | lowpass_fast | -2.25% [-3.18, -1.44] | 98 | 2.29% | 0.00 | 0 |
| lightgbm | graded_lowpass | -1.25% [-1.70, -0.83] | 30 | 4.14% | 0.00 | 0 |
| lightgbm_spatial | heuristic | -0.85% [-1.71, -0.17] | 7 | 12.93% | 0.00 | 0 |
| lightgbm_spatial | adaptive | -7.03% [-8.20, -5.88] | 498 | 1.41% | 0.00 | 0 |
| lightgbm_spatial | stochastic | -5.20% [-6.27, -4.15] | 224 | 2.33% | 0.00 | 0 |
| lightgbm_spatial | stochastic_skill | -3.29% [-4.17, -2.42] | 146 | 2.25% | 0.55 | 0 |
| lightgbm_spatial | graded_mpc | -3.63% [-4.35, -2.96] | 77 | 4.70% | 0.00 | 0 |
| lightgbm_spatial | lowpass_fast | -5.81% [-6.71, -5.03] | 132 | 4.41% | 0.00 | 0 |
| lightgbm_spatial | graded_lowpass | -3.65% [-4.30, -3.09] | 55 | 6.68% | 0.00 | 0 |
| perfect | heuristic | -97.44% [-98.53, -96.13] | 173 | 56.24% | 0.00 | 0 |
| perfect | adaptive | -99.87% [-100.00, -99.70] | 159 | 62.98% | 0.00 | 0 |
| perfect | stochastic | -99.80% [-99.93, -99.64] | 149 | 66.94% | 0.00 | 0 |
| perfect | stochastic_skill | -99.60% [-99.90, -99.17] | 148 | 67.11% | 0.04 | 0 |
| perfect | graded_mpc | -99.60% [-99.90, -99.17] | 148 | 67.11% | 0.00 | 0 |
| perfect | lowpass_fast | -78.92% [-81.36, -76.45] | 393 | 20.09% | 0.00 | 0 |
| perfect | graded_lowpass | -78.84% [-81.27, -76.35] | 392 | 20.09% | 0.00 | 0 |

## Forecast skill on the evaluation period (secondary)

| Forecast | Decisions | MAE 10â€¦60 min (kW) | Skill vs persistence | Ramp correlation |
|---|---|---|---|---|
| persistence | 50820 | 83 114 131 144 156 166 | +0.000 | +0.00 |
| lightgbm | 50820 | 85 117 136 150 163 174 | +0.112 | +0.26 |
| lightgbm_spatial | 50820 | 83 115 133 147 160 171 | +0.142 | +0.29 |
| perfect | 50820 | 0 0 0 0 0 0 | +1.000 | +1.00 |
