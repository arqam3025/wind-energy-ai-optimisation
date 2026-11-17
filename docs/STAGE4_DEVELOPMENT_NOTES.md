# Stage 4 development notes: Kelmarsh real data

**Study role:** REAL_DATA_DEVELOPMENT (2018–2021 only). The validation year (2022) and the sealed
test years (2023–2024) have not been opened.

## Round 0: data facts (2026-11-14)

Source files: turbine 1 (`Turbine_Data_Kelmarsh_1_*`), read directly from the verified archives.

| Year | Rows | First → last timestamp | Irregular steps | Power missing | Power range (kW) | Mean (kW) | Downtime/curtailment rows | Ramps > 200 kW | 95th-percentile ramp (kW) |
|---|---|---|---|---|---|---|---|---|---|
| 2018 | 52,560 | 00:00 Jan 1 → 23:50 Dec 31 | 0 | 3.4% | −16 … 2080 | 602 | 4.3% | 12.7% | 327 |
| 2019 | 52,560 | same | 0 | 0.2% | −18 … 2081 | 604 | 1.0% | 13.6% | 334 |
| 2020 | 52,704 | same | 0 | 0.9% | −16 … 2079 | 716 | 1.9% | 14.1% | 341 |
| 2021 | 52,560 | same | 0 | 1.0% | −17 … 2076 | 554 | 3.1% | 11.6% | 312 |

Answers to the open questions in `DATA_ADMISSION_KELMARSH.md`:

1. **Timezone: UTC**, stated in each file header ("Time zone: UTC").
2. **Interval labelling: start of interval.** This is inferred, because each yearly file is
   declared as `[YYYY-01-01 00:00, YYYY+1-01-01 00:00)` and runs 00:00 → 23:50. The label t
   therefore denotes the mean over [t, t+10 min), and that value becomes available at t + 10 min
   at the earliest. The Stage 2/3 convention (target time = end of interval) maps as
   target_time = label + 10 min.
3. **Signal:** `Power (kW)`, the 10-minute mean active power. Small negative values are auxiliary
   consumption; the target is y = max(0, P), consistent with `docs/METHODS.md`.
4. **Flags:** `Lost Production to Downtime and Curtailment Total (kWh)` and the per-cause columns
   are present for exclusion rules.
5. **Scale:** each turbine is a Senvion MM92 rated at 2.05 MW (static metadata), essentially the
   2 MW turbine of the synthetic generator. The single-turbine study therefore keeps the battery
   (2 MWh, ±1 MW) and the ramp reference (200 kW per 10 min) unchanged, with no rescaling. This
   decision is to be confirmed in the Stage 4 protocol.

Observation: the real ramp frequency (12–14% of intervals above 200 kW) is of the same order as
in the synthetic generator, so ramp control is a meaningful task on real data.

## Round 1: real-data pipeline and first closed loop (2026-11-17)

Code: `publication_v2/stage4/` (`kelmarsh.py`, `features.py`, `closed_loop.py`, `experiment.py`).

- **Timing.** Rows are re-indexed to the interval end (label + 10 min). At a decision d, the
  features use values ending at or before d. Conformal and skill residuals use targets ending
  strictly before d, which the Stage 3.1 validator requires.
- **Forecaster.** The Stage 2 14-feature contract and the Stage 2 LightGBM defaults, both fixed
  before Kelmarsh was opened. It is fitted on 2018–2020 and applied to 2021.
- **Uncertainty.** Rolling split-conformal intervals: the last 48 released absolute residuals per
  horizon, finite-sample rank, α = 0.1, at least 30 samples. The released skill score versus
  persistence uses the same pairs.
- **Episodes.** 8-hour blocks of 2021 starting at 00:00, 08:00 and 16:00 UTC. 1,069 of 1,095 are
  eligible; the rest have missing data and are skipped, never imputed. The series starts on
  2021-01-01, so every calibration window is out of sample.
- **Bug found and fixed before any result was used.** pandas 3 stores timestamps in microseconds,
  and reading them back as nanoseconds put the times in 1970. A year guard now refuses such a
  series.

Forecast skill on 2021 (MAE in kW per horizon; skill = pooled MSE skill vs persistence):

| Forecaster | MAE 10…60 min | MAE30 | Skill | Ramp correlation (true \|ramp\| > 200 kW) |
|---|---|---|---|---|
| Persistence | 84 112 129 141 151 160 | 129 | 0 | 0 |
| LightGBM (Stage 2 features) | 85 113 130 142 152 161 | 130 | +0.111 | +0.22 |
| XGBoost (Stage 2 features) | 85 113 130 142 153 161 | 130 | +0.111 | +0.22 |

Closed loop on 2021 (1,069 episodes; mean per episode; exceedance in kW, throughput in kWh):

| Forecast | No battery | Fixed margin | Adaptive | Stochastic | Stochastic + switch (P) | Switch idle |
|---|---|---|---|---|---|---|
| Persistence | 762.8 / 0 | 762.8 / 0 | 762.4 / 157 | 763.5 / 30 | 762.8 / 0 | 100% |
| LightGBM | 762.8 / 0 | 735.0 / 659 | 743.2 / 458 | 747.4 / 162 | 758.2 / 92 | 59% |
| Perfect (privileged) | 762.8 / 0 | 0.2 / 947 | 0.1 / 123 | 1.0 / 117 | 3.6 / 116 | 3% |

**Finding.** The battery and controllers could remove essentially all ramp exceedance; the perfect
forecast shows this headroom. With real SCADA-only forecasts, the reduction is only 1–4%. The
forecast, not the controller, is the bottleneck. Real forecasts have MAE similar to the simulator's
"skilful" oracle σ100 (MAE30 ≈ 130 kW) but almost no ramp skill. This confirms the Stage 3.3
finding that MAE does not predict control value. The switch behaves as designed: it is fully idle
with persistence, and with LightGBM (skill ≈ 0.11, near the 0.10 threshold) it is idle in 59% of
decisions.

## Round 2: forecaster improvement on an inner split (no 2021 data used for selection)

To select a forecaster, models were fitted on 2018–2019 and compared on 2020. The comparison used
pooled skill, per-horizon skill, MAE30 and ramp correlation.

| Candidate | Skill | Per-horizon skill | MAE30 | Ramp correlation |
|---|---|---|---|---|
| Stage 2 features, default LightGBM | +0.114 | .06 .10 .11 .12 .13 .13 | 148 | +0.22 |
| **+ 5 neighbour turbines, default LightGBM** | **+0.141** | .12 .13 .14 .14 .15 .15 | 145 | +0.25 |
| Stage 2 features, larger LightGBM (400 trees, 63 leaves) | +0.111 | .06 .09 .10 .12 .12 .13 | 147 | +0.15 |
| + neighbours, larger LightGBM | +0.139 | .14 .13 .13 .14 .14 .14 | 144 | +0.19 |
| Farm-average target (per-turbine kW), Stage 2 features | +0.076 | .03 .05 .07 .08 .08 .09 | 125 | +0.23 |
| Farm-average target + per-turbine changes | +0.077 | .04 .06 .07 .08 .08 .09 | 125 | +0.23 |

**Decisions.**

1. **Forecaster.** `lightgbm_spatial` = default Stage 2 LightGBM hyperparameters plus causal
   neighbour-turbine features: power, wind and their 10/30-minute changes for turbines 2–6,
   farm-total power changes, turbine-1 wind direction (sin/cos) and the 60-minute standard
   deviation of turbine-1 power. It gives the best skill and ramp correlation; the larger model
   adds nothing. The Stage 2 forecaster stays as a comparator.
2. **Control level.** Turbine 1 stays the primary unit, as planned in round 0.
   - The farm-average series (per-turbine kW, equivalent to scaling the battery and the ramp limit
     by 6) has fewer threshold ramps (8.2% vs 13.7% of intervals) but lower forecast skill.
   - It is kept as a secondary sensitivity because grid-code limits apply at the point of
     connection.
3. **Physical limit (to report).** At 10–60 minutes, SCADA-only forecasts of a single turbine or
   a small farm carry little ramp information; skill is about 0.08–0.14 versus persistence.
   Upstream measurements, NWP or lidar would be needed for substantially better ramp forecasts
   [CITE].
