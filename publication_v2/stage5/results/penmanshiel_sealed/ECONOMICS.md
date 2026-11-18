# Economic view: Penmanshiel sealed 2023-2024

Post-hoc descriptive. Break-even = battery cost / exceedance avoided (EUR per kW of ramp exceedance). Lower is more cost-effective; "—" means no exceedance is avoided.

| Assumption | Capex (EUR/kWh) | Cycle life | DoD | Energy (EUR/MWh) | Degradation (EUR/kWh throughput) |
|---|---|---|---|---|---|
| low cost | 150 | 8000 | 0.8 | 40 | 0.0117 |
| central | 300 | 6000 | 0.8 | 60 | 0.0312 |
| high cost | 450 | 4000 | 0.8 | 100 | 0.0703 |

| Forecast | Controller | Exceedance avoided (kW/episode) | Throughput (kWh) | Cost, central (EUR/episode) | Annual cost, central (EUR) | Break-even (EUR/kW), low / central / high |
|---|---|---|---|---|---|---|
| lightgbm | adaptive | 30.7 | 510 | 17.49 | 19,154 | 0.23 / 0.57 / 1.25 |
| lightgbm | graded_lowpass | 14.0 | 38 | 1.31 | 1,429 | 0.04 / 0.09 / 0.21 |
| lightgbm | graded_mpc | 13.3 | 47 | 1.61 | 1,759 | 0.05 / 0.12 / 0.27 |
| lightgbm | heuristic | 13.8 | 8 | 0.28 | 304 | 0.01 / 0.02 / 0.04 |
| lightgbm | lowpass_fast | 21.7 | 114 | 3.92 | 4,293 | 0.07 / 0.18 / 0.40 |
| lightgbm | stochastic | 19.9 | 185 | 6.33 | 6,936 | 0.13 / 0.32 / 0.70 |
| lightgbm | stochastic_skill | 7.1 | 99 | 3.41 | 3,731 | 0.19 / 0.48 / 1.05 |
| lightgbm_spatial | adaptive | 73.0 | 574 | 19.72 | 21,590 | 0.11 / 0.27 / 0.59 |
| lightgbm_spatial | graded_lowpass | 35.8 | 65 | 2.23 | 2,443 | 0.03 / 0.06 / 0.14 |
| lightgbm_spatial | graded_mpc | 38.1 | 91 | 3.11 | 3,404 | 0.03 / 0.08 / 0.18 |
| lightgbm_spatial | heuristic | 13.6 | 10 | 0.33 | 359 | 0.01 / 0.02 / 0.05 |
| lightgbm_spatial | lowpass_fast | 57.1 | 151 | 5.18 | 5,672 | 0.04 / 0.09 / 0.20 |
| lightgbm_spatial | stochastic | 54.6 | 261 | 8.97 | 9,819 | 0.07 / 0.16 / 0.36 |
| lightgbm_spatial | stochastic_skill | 33.9 | 173 | 5.93 | 6,493 | 0.07 / 0.17 / 0.38 |
| perfect | adaptive | 1038.8 | 187 | 6.41 | 7,016 | 0.00 / 0.01 / 0.01 |
| perfect | stochastic | 1037.6 | 175 | 6.00 | 6,574 | 0.00 / 0.01 / 0.01 |
| perfect | stochastic_skill | 1035.0 | 174 | 5.96 | 6,530 | 0.00 / 0.01 / 0.01 |
| persistence | adaptive | -0.2 | 198 | 6.79 | 7,433 | — / — / — |
| persistence | graded_lowpass | 0.0 | 0 | 0.00 | 0 | — / — / — |
| persistence | graded_mpc | 0.0 | 0 | 0.00 | 0 | — / — / — |
| persistence | heuristic | 0.0 | 0 | 0.00 | 0 | — / — / — |
| persistence | lowpass_fast | 0.0 | 0 | 0.00 | 0 | — / — / — |
| persistence | stochastic | -0.3 | 65 | 2.24 | 2,452 | — / — / — |
| persistence | stochastic_skill | 0.0 | 0 | 0.00 | 0 | — / — / — |
