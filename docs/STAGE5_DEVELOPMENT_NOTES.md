# Stage 5 development notes: improvements after the Stage 4 sealed test (exploratory)

**Study role: EXPLORATORY_DEVELOPMENT.** The Stage 4 sealed test (Kelmarsh 2023–2024) has been
used, so nothing here is re-tested on it as confirmatory evidence. Week 1 used Kelmarsh
development data only:
- the 2021 closed loop, with the identical 1,027 paired episodes of the Stage 4 development round 3
  (forecasters fitted on 2018–2021 data before 2021);
- for forecaster selection, an inner split (fit 2018–2019, score 2020).

The one exception is the economic view, which is also applied post hoc to the sealed results as a
descriptive analysis. It contains no test, and it is labelled as post hoc wherever it is reported.

Code: `publication_v2/stage5/`:
- `filters.py`: low-pass baseline;
- `switches.py`: graded and gated switches;
- `economics.py`: break-even analysis;
- `experiment.py`: runner on the same Stage 4 episodes.

The Stage 4 runner gained an optional `decider` hook. Default behaviour is unchanged, and the
Stage 4 tests pass.

## Week 1 results (2021 development; neighbour-turbine LightGBM unless stated)

Change in ramp exceedance versus no battery, with week-block 95% CI:

| Controller | Change | Throughput (kWh/episode) | Reduction per 100 kWh |
|---|---|---|---|
| Fixed-margin MPC | −8.65% [−10.13, −7.14] | 705 | 1.23% |
| Adaptive MPC | −7.57% [−8.98, −6.06] | 490 | 1.55% |
| Stochastic MPC | −5.42% [−6.61, −4.19] | 186 | 2.91% |
| P = stochastic + binary switch (0.10) | −3.08% [−4.41, −1.73] | 116 | 2.65% |
| Stochastic + binary switch (0.0) | −4.61% [−5.85, −3.35] | 155 | 2.98% |
| **Low-pass filter (α = 0.5) + SOC feedback, on the forecast** | −5.43% [−6.40, −4.39] | 128 | 4.26% |
| Low-pass filter (α = 0.25) | −5.73% [−7.32, −4.02] | 267 | 2.15% |
| Low-pass filter behind the binary switch | −3.81% [−4.72, −2.90] | 78 | 4.86% |
| **Graded switch + stochastic MPC** | −3.23% [−4.09, −2.39] | 56 | 5.81% |
| **Graded switch + low-pass filter** | −3.29% [−3.97, −2.64] | 51 | 6.44% |

With persistence, every new variant does nothing (0.0%, 0 kWh). With the Stage 2 LightGBM, the
graded variants give −1.1% to −1.4% at 36 kWh.

### Findings

1. **The industry baseline (#5) is strong once it has a forecast.** A low-pass filter with SOC
   feedback, driven by the next-interval forecast, matches the stochastic MPC's reduction
   (−5.4%) with 31% less throughput.
   - In this 10-minute dispatch layer, a forecast-free filter (persistence estimate) never acts.
     It can only react after a ramp has already been delivered.
   - This must be reported: the efficiency advantage of stochastic MPC holds against margin-based
     MPC, **not** against a forecast-driven low-pass filter.
2. **The graded switch (#2) halves battery use at equal benefit.** With a weight that rises
   linearly from skill 0 (idle) to skill 0.30 (full action), fixed a priori, both the MPC and the
   filter keep the binary switch's reduction (about −3.2%) with 51–56 kWh instead of 116 kWh.
   That is about twice the efficiency, and there is still no harm with persistence.
3. **The forecaster (#1) plateaus at a skill of about 0.15.** Inner split, fit 2018–2019, score 2020:

| Candidate | Skill | MAE30 | Ramp correlation |
|---|---|---|---|
| Neighbours, default LightGBM (Stage 4) | +0.140 | 145 | +0.25 |
| Neighbours, larger LightGBM | +0.147 | 143 | +0.23 |
| + extended history (longer lags, rolling ranges, wind variability, time of day) | +0.144 | 145 | +0.25 |
| + extended history, larger LightGBM | **+0.151** | 143 | +0.24 |
| Change targets (y(t+h) − y(t)) instead of levels | +0.124 to +0.149 | 143–145 | +0.23 to +0.24 |

   Feature and model engineering on SCADA alone adds about 0.01 skill and no ramp information.
   This supports the paper's message that a different information source (NWP, lidar, upstream
   measurements) is needed [CITE].

### Economic view (#6), post hoc on the Stage 4 sealed results

There is no market price for ramp exceedance, so the analysis reports the **break-even penalty**:
battery cost (degradation plus conversion losses) per kW of exceedance avoided. Central
assumptions are capex €300/kWh, 6,000 cycles, 80% DoD and €60/MWh. The low and high scenarios are
in `economics.py` and need sources [CITE].

| Neighbour forecast | Exceedance avoided (kW/episode) | Annual battery cost (€) | Break-even €/kW (low / central / high) |
|---|---|---|---|
| Fixed-margin MPC | 79.5 | 27,984 | 0.13 / 0.32 / 0.71 |
| Adaptive MPC | 71.0 | 22,054 | 0.11 / 0.28 / 0.62 |
| Stochastic MPC | 49.3 | 8,811 | 0.07 / 0.16 / 0.36 |
| P (binary switch) | 30.6 | 5,924 | 0.07 / 0.18 / 0.39 |
| Perfect forecast + P | 956.7 | 5,616 | 0.00 / 0.01 / 0.01 |

The stochastic controllers are about 40% cheaper per kW avoided than margin-based MPC. With a
perfect forecast the cost per kW avoided falls about 20-fold, which again places the value in
the forecast.

## Implications for the next confirmatory study (week 2: a new site)

- **Candidate primary controller:** graded switch + stochastic MPC. Its competitor is the graded
  switch + low-pass filter. The threshold parameters stay fixed (0 and 0.30).
- **Required comparator:** the forecast-driven low-pass filter.
- **Forecaster:** keep the Stage 4 design (Stage 2 features plus neighbour features, default
  LightGBM). The extended model adds only about 0.01 skill and would add site-specific tuning.
