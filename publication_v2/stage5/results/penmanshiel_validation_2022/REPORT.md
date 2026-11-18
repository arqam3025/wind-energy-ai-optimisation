# Penmanshiel validation 2022 (pre-freeze check)

Episodes: 968 (paired). Inference unit: ISO week; Wilcoxon on weekly means; CIs from a week-block bootstrap; Holm across all primary tests.

## Primary tests

| Test | Forecast | Claim | Margin | Mean diff [95% CI] | weeks | p (Holm) | Supported |
|---|---|---|---|---|---|---|---|
| S1 | lightgbm_spatial | G reduces ramp exceedance vs no battery | 0.0 | -37.3 [-50.8, -25.3] | 50 | 2.69e-08 | yes |
| S2 | lightgbm_spatial | G uses less throughput than the binary-switch controller P | 0.0 | -89.5 [-105.8, -74.5] | 50 | 1.51e-09 | yes |
| S3 | lightgbm_spatial | G exceedance non-inferior to P (margin 1% of U) | 11.7 | -1.2 [-7.5, +5.4] | 50 | 5.11e-05 | yes |
| S4 | lightgbm_spatial | G uses less throughput than adaptive MPC | 0.0 | -520.1 [-577.2, -460.1] | 50 | 5.33e-15 | yes |
| S5 | persistence | no material harm without skill (margin 5% of U) | 58.5 | +0.0 [+0.0, +0.0] | 50 | 3.84e-12 | yes |
| S6 | lightgbm | no material harm with a weak forecast (margin 5% of U) | 58.5 | -12.8 [-21.2, -6.2] | 50 | 1.51e-09 | yes |

## All controllers

| Forecast | Controller | Change vs none [95% CI] | Throughput kWh/ep | Reduction per 100 kWh | Idle (binary switch) | Safety viol. |
|---|---|---|---|---|---|---|
| persistence | heuristic | +0.00% [+0.00, +0.00] | 0 | 0.00% | 0.00 | 0 |
| persistence | adaptive | +0.13% [-0.14, +0.41] | 220 | -0.06% | 0.00 | 0 |
| persistence | stochastic | +0.27% [+0.01, +0.53] | 78 | -0.35% | 0.00 | 0 |
| persistence | stochastic_skill | +0.00% [+0.00, +0.00] | 0 | 0.00% | 1.00 | 0 |
| persistence | graded_mpc | +0.00% [+0.00, +0.00] | 0 | 0.00% | 0.00 | 0 |
| persistence | lowpass_fast | +0.00% [+0.00, +0.00] | 0 | 0.00% | 0.00 | 0 |
| persistence | graded_lowpass | +0.00% [+0.00, +0.00] | 0 | 0.00% | 0.00 | 0 |
| lightgbm | heuristic | -0.69% [-1.62, +0.14] | 7 | 10.41% | 0.00 | 0 |
| lightgbm | adaptive | -2.40% [-3.27, -1.46] | 560 | 0.43% | 0.00 | 0 |
| lightgbm | stochastic | -1.50% [-2.43, -0.57] | 213 | 0.71% | 0.00 | 0 |
| lightgbm | stochastic_skill | -0.71% [-1.51, +0.04] | 117 | 0.61% | 0.60 | 0 |
| lightgbm | graded_mpc | -1.09% [-1.67, -0.58] | 53 | 2.06% | 0.00 | 0 |
| lightgbm | lowpass_fast | -1.60% [-2.23, -0.92] | 120 | 1.34% | 0.00 | 0 |
| lightgbm | graded_lowpass | -1.12% [-1.53, -0.74] | 41 | 2.75% | 0.00 | 0 |
| lightgbm_spatial | heuristic | -0.31% [-1.28, +0.50] | 11 | 2.98% | 0.00 | 0 |
| lightgbm_spatial | adaptive | -6.34% [-7.55, -5.01] | 617 | 1.03% | 0.00 | 0 |
| lightgbm_spatial | stochastic | -4.59% [-5.71, -3.47] | 283 | 1.62% | 0.00 | 0 |
| lightgbm_spatial | stochastic_skill | -3.08% [-4.16, -1.95] | 186 | 1.66% | 0.51 | 0 |
| lightgbm_spatial | graded_mpc | -3.19% [-4.02, -2.37] | 97 | 3.30% | 0.00 | 0 |
| lightgbm_spatial | lowpass_fast | -5.24% [-6.10, -4.37] | 155 | 3.38% | 0.00 | 0 |
| lightgbm_spatial | graded_lowpass | -3.38% [-3.97, -2.77] | 65 | 5.17% | 0.00 | 0 |
| perfect | heuristic | -97.68% [-99.04, -96.04] | 229 | 42.60% | 0.00 | 0 |
| perfect | adaptive | -99.91% [-100.00, -99.74] | 208 | 48.05% | 0.00 | 0 |
| perfect | stochastic | -99.83% [-99.94, -99.62] | 195 | 51.16% | 0.00 | 0 |
| perfect | stochastic_skill | -99.56% [-99.87, -99.14] | 195 | 51.16% | 0.02 | 0 |
| perfect | graded_mpc | -99.56% [-99.87, -99.14] | 195 | 51.16% | 0.00 | 0 |
| perfect | lowpass_fast | -78.72% [-81.11, -76.27] | 477 | 16.50% | 0.00 | 0 |
| perfect | graded_lowpass | -78.55% [-80.99, -76.08] | 476 | 16.49% | 0.00 | 0 |

## Forecast skill on the evaluation period (secondary)

| Forecast | Decisions | MAE 10â€¦60 min (kW) | Skill vs persistence | Ramp correlation |
|---|---|---|---|---|
| persistence | 47665 | 99 137 159 175 189 201 | +0.000 | +0.00 |
| lightgbm | 47665 | 101 139 161 177 192 203 | +0.118 | +0.24 |
| lightgbm_spatial | 47665 | 99 137 159 176 190 202 | +0.143 | +0.27 |
| perfect | 47665 | 0 0 0 0 0 0 | +1.000 | +1.00 |
