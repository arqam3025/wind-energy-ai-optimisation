# Economic view: Kelmarsh sealed test 2023-2024 (post-hoc)

Post-hoc descriptive. Break-even = battery cost / exceedance avoided (EUR per kW of ramp exceedance). Lower is more cost-effective; "—" means no exceedance is avoided.

| Assumption | Capex (EUR/kWh) | Cycle life | DoD | Energy (EUR/MWh) | Degradation (EUR/kWh throughput) |
|---|---|---|---|---|---|
| low cost | 150 | 8000 | 0.8 | 40 | 0.0117 |
| central | 300 | 6000 | 0.8 | 60 | 0.0312 |
| high cost | 450 | 4000 | 0.8 | 100 | 0.0703 |

| Forecast | Controller | Exceedance avoided (kW/episode) | Throughput (kWh) | Cost, central (EUR/episode) | Annual cost, central (EUR) | Break-even (EUR/kW), low / central / high |
|---|---|---|---|---|---|---|
| lightgbm | adaptive | 25.6 | 557 | 19.13 | 20,951 | 0.30 / 0.75 / 1.64 |
| lightgbm | deterministic | 1.3 | 2 | 0.08 | 87 | 0.02 / 0.06 / 0.13 |
| lightgbm | fixed_margin | 33.6 | 707 | 24.26 | 26,559 | 0.29 / 0.72 / 1.59 |
| lightgbm | heuristic | 1.1 | 2 | 0.06 | 61 | 0.02 / 0.05 / 0.11 |
| lightgbm | stochastic | 15.9 | 202 | 6.92 | 7,574 | 0.17 / 0.44 / 0.96 |
| lightgbm | stochastic_skill | 3.2 | 118 | 4.04 | 4,418 | 0.50 / 1.26 / 2.76 |
| lightgbm_spatial | adaptive | 71.0 | 587 | 20.14 | 22,054 | 0.11 / 0.28 / 0.62 |
| lightgbm_spatial | deterministic | 0.4 | 3 | 0.11 | 121 | 0.12 / 0.30 / 0.65 |
| lightgbm_spatial | fixed_margin | 79.5 | 745 | 25.56 | 27,984 | 0.13 / 0.32 / 0.71 |
| lightgbm_spatial | heuristic | 1.8 | 2 | 0.08 | 87 | 0.02 / 0.04 / 0.10 |
| lightgbm_spatial | stochastic | 49.3 | 234 | 8.05 | 8,811 | 0.07 / 0.16 / 0.36 |
| lightgbm_spatial | stochastic_skill | 30.6 | 158 | 5.41 | 5,924 | 0.07 / 0.18 / 0.39 |
| perfect | adaptive | 957.7 | 158 | 5.42 | 5,938 | 0.00 / 0.01 / 0.01 |
| perfect | stochastic | 956.7 | 149 | 5.13 | 5,616 | 0.00 / 0.01 / 0.01 |
| perfect | stochastic_skill | 956.7 | 149 | 5.13 | 5,616 | 0.00 / 0.01 / 0.01 |
| persistence | adaptive | 0.2 | 195 | 6.70 | 7,332 | 13.19 / 32.92 / 72.36 |
| persistence | deterministic | 0.0 | 0 | 0.00 | 0 | — / — / — |
| persistence | fixed_margin | 0.0 | 0 | 0.00 | 0 | — / — / — |
| persistence | heuristic | 0.0 | 0 | 0.00 | 0 | — / — / — |
| persistence | stochastic | -2.1 | 51 | 1.76 | 1,930 | — / — / — |
| persistence | stochastic_skill | 0.0 | 0 | 0.00 | 0 | — / — / — |
