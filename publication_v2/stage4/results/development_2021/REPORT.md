# Stage 4 real-data results

Episodes: 1027 (paired across all forecasts and controllers). Inference unit: ISO week; Wilcoxon on weekly means; CIs from a week-block bootstrap.

## Primary tests (Holm, one-sided, alpha 0.05)

| Test | Forecast | Contrast | Margin | Mean diff [95% CI] | weeks | p (Holm) | Supported |
|---|---|---|---|---|---|---|---|
| R1 | lightgbm_spatial | stochastic_skill - uncontrolled (ramp) | 0.0 | -23.3 [-35.8, -12.1] | 53 | 5.27e-04 | yes |
| R2 | lightgbm_spatial | stochastic_skill - adaptive (throughput) | 0.0 | -374.1 [-419.5, -331.7] | 53 | 3.58e-10 | yes |
| R3 | persistence | stochastic_skill - uncontrolled (ramp) | 37.8 | +0.0 [+0.0, +0.0] | 53 | 6.67e-13 | yes |
| R4 | lightgbm | stochastic_skill - uncontrolled (ramp) | 37.8 | -6.1 [-12.8, +0.5] | 53 | 5.91e-10 | yes |

## All controllers

| Forecast | Controller | Exceedance kW/ep | Change vs none [95% CI] | Throughput kWh/ep | kW per MWh | Idle (switch) | Safety viol. | Solver failures |
|---|---|---|---|---|---|---|---|---|
| persistence | uncontrolled | 756.8 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| persistence | heuristic | 756.8 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| persistence | deterministic | 756.8 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| persistence | fixed_margin | 756.8 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| persistence | adaptive | 756.5 | -0.0% [-0.2, +0.2] | 157 | 2 | 0.00 | 0 | 133 |
| persistence | stochastic | 757.3 | +0.1% [-0.2, +0.3] | 29 | -18 | 0.00 | 0 | 3 |
| persistence | stochastic_skill | 756.8 | +0.0% [+0.0, +0.0] | 0 |  | 1.00 | 0 | 0 |
| lightgbm | uncontrolled | 756.8 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| lightgbm | heuristic | 756.1 | -0.1% [-0.3, +0.1] | 1 | 727 | 0.00 | 0 | 0 |
| lightgbm | deterministic | 756.7 | -0.0% [-0.2, +0.2] | 2 | 50 | 0.00 | 0 | 0 |
| lightgbm | fixed_margin | 728.1 | -3.8% [-5.0, -2.5] | 657 | 44 | 0.00 | 0 | 6 |
| lightgbm | adaptive | 736.6 | -2.7% [-3.9, -1.4] | 455 | 44 | 0.00 | 0 | 28 |
| lightgbm | stochastic | 739.3 | -2.3% [-3.2, -1.4] | 160 | 110 | 0.00 | 0 | 4 |
| lightgbm | stochastic_skill | 750.7 | -0.8% [-1.6, +0.1] | 90 | 68 | 0.59 | 0 | 1 |
| lightgbm_spatial | uncontrolled | 756.8 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| lightgbm_spatial | heuristic | 754.6 | -0.3% [-0.4, -0.1] | 1 | 1557 | 0.00 | 0 | 0 |
| lightgbm_spatial | deterministic | 755.7 | -0.1% [-0.4, +0.1] | 2 | 638 | 0.00 | 0 | 0 |
| lightgbm_spatial | fixed_margin | 691.3 | -8.7% [-10.1, -7.1] | 705 | 93 | 0.00 | 0 | 1 |
| lightgbm_spatial | adaptive | 699.5 | -7.6% [-9.0, -6.1] | 490 | 117 | 0.00 | 0 | 27 |
| lightgbm_spatial | stochastic | 715.8 | -5.4% [-6.6, -4.2] | 186 | 220 | 0.00 | 0 | 1 |
| lightgbm_spatial | stochastic_skill | 733.5 | -3.1% [-4.4, -1.7] | 116 | 201 | 0.52 | 0 | 3 |
| perfect | uncontrolled | 756.8 | +0.0% [+0.0, +0.0] | 0 |  | 0.00 | 0 | 0 |
| perfect | heuristic | 3.2 | -99.6% [-99.8, -99.3] | 137 | 5504 | 0.00 | 0 | 0 |
| perfect | deterministic | 0.1 | -100.0% [-100.0, -100.0] | 122 | 6215 | 0.00 | 0 | 4 |
| perfect | fixed_margin | 0.2 | -100.0% [-100.0, -99.9] | 942 | 803 | 0.00 | 0 | 2 |
| perfect | adaptive | 0.1 | -100.0% [-100.0, -100.0] | 122 | 6215 | 0.00 | 0 | 4 |
| perfect | stochastic | 1.1 | -99.9% [-99.9, -99.8] | 116 | 6530 | 0.00 | 0 | 3 |
| perfect | stochastic_skill | 3.7 | -99.5% [-99.8, -99.1] | 115 | 6540 | 0.02 | 0 | 3 |

## Forecast skill on the evaluation period (secondary)

| Forecast | Decisions | MAE 10â€¦60 min (kW) | Skill vs persistence | Ramp correlation |
|---|---|---|---|---|
| persistence | 50728 | 84 112 128 140 150 159 | +0.000 | +0.00 |
| lightgbm | 50728 | 85 113 129 142 152 161 | +0.110 | +0.22 |
| lightgbm_spatial | 50728 | 83 111 128 140 151 159 | +0.130 | +0.24 |
| perfect | 50728 | 0 0 0 0 0 0 | +1.000 | +1.00 |
