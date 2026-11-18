# Stage 4 real-data results

Episodes: 1048 (paired across all forecasts and controllers). Inference unit: ISO week; Wilcoxon on weekly means; CIs from a week-block bootstrap.

## Primary tests (Holm, one-sided, alpha 0.05)

| Test | Forecast | Contrast | Margin | Mean diff [95% CI] | weeks | p (Holm) | Supported |
|---|---|---|---|---|---|---|---|
| R1 | lightgbm_spatial | stochastic_skill - uncontrolled (ramp) | 0.0 | -24.9 [-40.0, -11.2] | 53 | 8.00e-04 | yes |
| R2 | lightgbm_spatial | stochastic_skill - adaptive (throughput) | 0.0 | -418.0 [-462.8, -373.8] | 53 | 3.58e-10 | yes |
| R3 | persistence | stochastic_skill - uncontrolled (ramp) | 48.0 | +0.0 [+0.0, +0.0] | 53 | 6.67e-13 | yes |
| R4 | lightgbm | stochastic_skill - uncontrolled (ramp) | 48.0 | -6.6 [-16.6, +2.7] | 53 | 4.72e-10 | yes |

## All controllers

| Forecast | Controller | Exceedance kW/ep | Change vs none [95% CI] | Throughput kWh/ep | kW per MWh | Idle (switch) | Safety viol. | Solver failures |
|---|---|---|---|---|---|---|---|---|
| persistence | uncontrolled | 960.1 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| persistence | heuristic | 960.1 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| persistence | deterministic | 960.1 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| persistence | fixed_margin | 960.1 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| persistence | adaptive | 960.3 | +0.0% [-0.2, +0.3] | 185 | -1 | 0.00 | 0 | 263 |
| persistence | stochastic | 959.2 | -0.1% [-0.4, +0.1] | 47 | 20 | 0.00 | 0 | 3 |
| persistence | stochastic_skill | 960.1 | +0.0% [+0.0, +0.0] | 0 |  | 1.00 | 0 | 0 |
| lightgbm | uncontrolled | 960.1 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| lightgbm | heuristic | 957.0 | -0.3% [-0.6, -0.1] | 3 | 1207 | 0.00 | 0 | 0 |
| lightgbm | deterministic | 957.0 | -0.3% [-0.8, +0.0] | 4 | 733 | 0.00 | 0 | 0 |
| lightgbm | fixed_margin | 918.1 | -4.4% [-5.7, -3.0] | 716 | 59 | 0.00 | 0 | 3 |
| lightgbm | adaptive | 925.1 | -3.6% [-5.0, -2.2] | 551 | 64 | 0.00 | 0 | 30 |
| lightgbm | stochastic | 939.3 | -2.2% [-3.1, -1.1] | 199 | 105 | 0.00 | 0 | 7 |
| lightgbm | stochastic_skill | 953.5 | -0.7% [-1.6, +0.3] | 115 | 57 | 0.56 | 0 | 7 |
| lightgbm_spatial | uncontrolled | 960.1 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| lightgbm_spatial | heuristic | 958.7 | -0.2% [-0.3, +0.0] | 3 | 459 | 0.00 | 0 | 0 |
| lightgbm_spatial | deterministic | 960.1 | -0.0% [-0.3, +0.3] | 6 | 15 | 0.00 | 0 | 0 |
| lightgbm_spatial | fixed_margin | 883.2 | -8.0% [-9.5, -6.4] | 740 | 104 | 0.00 | 0 | 2 |
| lightgbm_spatial | adaptive | 891.0 | -7.2% [-8.8, -5.6] | 562 | 123 | 0.00 | 0 | 17 |
| lightgbm_spatial | stochastic | 910.9 | -5.1% [-6.4, -3.8] | 239 | 206 | 0.00 | 0 | 7 |
| lightgbm_spatial | stochastic_skill | 935.2 | -2.6% [-3.9, -1.2] | 144 | 173 | 0.48 | 0 | 7 |
| perfect | uncontrolled | 960.1 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| perfect | heuristic | 16.9 | -98.2% [-99.0, -97.4] | 176 | 5364 | 0.00 | 0 | 0 |
| perfect | deterministic | 0.3 | -100.0% [-100.0, -99.9] | 161 | 5964 | 0.00 | 0 | 2 |
| perfect | fixed_margin | 0.2 | -100.0% [-100.0, -99.9] | 1066 | 900 | 0.00 | 0 | 5 |
| perfect | adaptive | 0.3 | -100.0% [-100.0, -99.9] | 161 | 5964 | 0.00 | 0 | 2 |
| perfect | stochastic | 1.1 | -99.9% [-99.9, -99.8] | 152 | 6304 | 0.00 | 0 | 2 |
| perfect | stochastic_skill | 1.2 | -99.9% [-99.9, -99.8] | 152 | 6304 | 0.02 | 0 | 2 |

## Forecast skill on the evaluation period (secondary)

| Forecast | Decisions | MAE 10â€¦60 min (kW) | Skill vs persistence | Ramp correlation |
|---|---|---|---|---|
| persistence | 51486 | 94 127 146 160 172 182 | +0.000 | +0.00 |
| lightgbm | 51486 | 95 126 145 159 170 180 | +0.128 | +0.24 |
| lightgbm_spatial | 51486 | 92 124 143 157 169 179 | +0.145 | +0.26 |
| perfect | 51486 | 0 0 0 0 0 0 | +1.000 | +1.00 |
