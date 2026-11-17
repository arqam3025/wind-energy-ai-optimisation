# Stage 4 real-data results

Episodes: 2048 (paired across all forecasts and controllers). Inference unit: ISO week; Wilcoxon on weekly means; CIs from a week-block bootstrap.

## Primary tests (Holm, one-sided, alpha 0.05)

| Test | Forecast | Contrast | Margin | Mean diff [95% CI] | weeks | p (Holm) | Supported |
|---|---|---|---|---|---|---|---|
| R1 | lightgbm_spatial | stochastic_skill - uncontrolled (ramp) | 0.0 | -30.6 [-39.7, -21.9] | 105 | 1.51e-10 | yes |
| R2 | lightgbm_spatial | stochastic_skill - adaptive (throughput) | 0.0 | -429.1 [-457.5, -399.2] | 105 | 8.75e-19 | yes |
| R3 | persistence | stochastic_skill - uncontrolled (ramp) | 47.9 | +0.0 [+0.0, +0.0] | 105 | 2.44e-24 | yes |
| R4 | lightgbm | stochastic_skill - uncontrolled (ramp) | 47.9 | -3.2 [-9.1, +2.7] | 105 | 1.54e-18 | yes |

## All controllers

| Forecast | Controller | Exceedance kW/ep | Change vs none [95% CI] | Throughput kWh/ep | kW per MWh | Idle (switch) | Safety viol. | Solver failures |
|---|---|---|---|---|---|---|---|---|
| persistence | uncontrolled | 958.2 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| persistence | heuristic | 958.2 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| persistence | deterministic | 958.2 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| persistence | fixed_margin | 958.2 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| persistence | adaptive | 958.0 | -0.0% [-0.2, +0.1] | 195 | 1 | 0.00 | 0 | 352 |
| persistence | stochastic | 960.3 | +0.2% [+0.1, +0.4] | 51 | -40 | 0.00 | 0 | 9 |
| persistence | stochastic_skill | 958.2 | +0.0% [+0.0, +0.0] | 0 |  | 1.00 | 0 | 0 |
| lightgbm | uncontrolled | 958.2 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| lightgbm | heuristic | 957.1 | -0.1% [-0.2, -0.0] | 2 | 698 | 0.00 | 0 | 0 |
| lightgbm | deterministic | 956.9 | -0.1% [-0.3, -0.0] | 2 | 581 | 0.00 | 0 | 1 |
| lightgbm | fixed_margin | 924.6 | -3.5% [-4.4, -2.6] | 707 | 47 | 0.00 | 0 | 4 |
| lightgbm | adaptive | 932.6 | -2.7% [-3.6, -1.7] | 557 | 46 | 0.00 | 0 | 37 |
| lightgbm | stochastic | 942.3 | -1.7% [-2.3, -1.0] | 202 | 79 | 0.00 | 0 | 4 |
| lightgbm | stochastic_skill | 955.0 | -0.3% [-0.9, +0.3] | 118 | 27 | 0.54 | 0 | 4 |
| lightgbm_spatial | uncontrolled | 958.2 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| lightgbm_spatial | heuristic | 956.4 | -0.2% [-0.3, -0.1] | 2 | 786 | 0.00 | 0 | 0 |
| lightgbm_spatial | deterministic | 957.8 | -0.0% [-0.2, +0.1] | 3 | 116 | 0.00 | 0 | 1 |
| lightgbm_spatial | fixed_margin | 878.7 | -8.3% [-9.2, -7.3] | 745 | 107 | 0.00 | 0 | 5 |
| lightgbm_spatial | adaptive | 887.3 | -7.4% [-8.3, -6.4] | 587 | 121 | 0.00 | 0 | 62 |
| lightgbm_spatial | stochastic | 908.9 | -5.1% [-6.0, -4.3] | 234 | 210 | 0.00 | 0 | 4 |
| lightgbm_spatial | stochastic_skill | 927.6 | -3.2% [-4.0, -2.4] | 158 | 194 | 0.46 | 0 | 3 |
| perfect | uncontrolled | 958.2 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| perfect | heuristic | 8.9 | -99.1% [-99.5, -98.6] | 175 | 5435 | 0.00 | 0 | 0 |
| perfect | deterministic | 0.5 | -99.9% [-100.0, -99.9] | 158 | 6061 | 0.00 | 0 | 7 |
| perfect | fixed_margin | 0.8 | -99.9% [-100.0, -99.8] | 1094 | 875 | 0.00 | 0 | 5 |
| perfect | adaptive | 0.5 | -99.9% [-100.0, -99.9] | 158 | 6061 | 0.00 | 0 | 7 |
| perfect | stochastic | 1.5 | -99.8% [-99.9, -99.8] | 149 | 6408 | 0.00 | 0 | 10 |
| perfect | stochastic_skill | 1.5 | -99.8% [-99.9, -99.8] | 149 | 6408 | 0.01 | 0 | 10 |

## Forecast skill on the evaluation period (secondary)

| Forecast | Decisions | MAE 10â€¦60 min (kW) | Skill vs persistence | Ramp correlation |
|---|---|---|---|---|
| persistence | 100971 | 97 130 150 164 175 185 | +0.000 | +0.00 |
| lightgbm | 100971 | 97 129 148 161 173 182 | +0.123 | +0.22 |
| lightgbm_spatial | 100971 | 94 126 145 159 170 180 | +0.146 | +0.25 |
| perfect | 100971 | 0 0 0 0 0 0 | +1.000 | +1.00 |
