# Stage 5 results: sealed second-site test on Penmanshiel (2023–2024)

**Status:** confirmatory, run once under the frozen protocol `docs/STAGE5_CONFIRMATORY_PROTOCOL.md`
(SHA-256 `509885b8…0e4aab`, frozen commit `1fa4b9c`, tag `stage5-protocol-frozen`, pushed before the run).

| Item | Value |
|---|---|
| Run | from a clean detached checkout of `1fa4b9c`; started 2026-11-17 22:58:59 UTC, completed 2026-11-18 00:02:32 UTC |
| Deviations | **none**. The loader opened the sealed 2023 and 2024 files without error (0 absent rows for WT11–WT15); no resume |
| Integrity | the SHA-256 of every output in `COMPLETED.json` was re-checked after the run, and all match |
| Data | WT11 target, WT12–WT15 forecast inputs; forecasters fitted on 2018–2021 (205,698 rows; 204,112 for the spatial model) |
| Episodes | 2,067 paired 8-hour episodes in 106 ISO weeks, same set for every forecast and controller |
| Run record | `publication_v2/stage5/results/penmanshiel_sealed/run_record/` (report, tests, skill, prepare, STARTED, COMPLETED) |

G = `graded_mpc` (stochastic MPC with every planned flow scaled by w = clip(skill / 0.30, 0, 1)).
P = `stochastic_skill` (stochastic MPC behind the binary switch at skill 0.10; the Stage 4 controller).
U = mean uncontrolled exceedance per episode = 1,041.5 kW.

## 1. Primary hypotheses (Holm across six, one-sided, α = 0.05)

| Test | Forecast | Claim | Margin (kW) | Mean difference [95% CI] | p (Holm) | Result |
|---|---|---|---|---|---|---|
| S1 | spatial LightGBM | G reduces exceedance vs no battery | 0 | −38.1 kW [−49.7, −28.5] | 1.4e−17 | **supported** |
| S2 | spatial LightGBM | G uses less throughput than P | 0 | −82.2 kWh [−92.1, −72.5] | 1.0e−18 | **supported** |
| S3 | spatial LightGBM | G exceedance non-inferior to P | 10.4 | −4.2 kW [−9.5, +0.8] | 3.7e−07 | **supported** |
| S4 | spatial LightGBM | G uses less throughput than adaptive MPC | 0 | −483.9 kWh [−519.6, −446.7] | 1.0e−18 | **supported** |
| S5 | persistence | G does no material harm without skill | 52.1 | +0.0 kW [0.0, 0.0] | 2.2e−24 | **supported** |
| S6 | Stage 2 LightGBM | G does no material harm with a weak forecast | 52.1 | −13.3 kW [−23.1, −5.4] | 1.0e−18 | **supported** |

All six primary hypotheses are supported. Because S2 and S3 both hold, the pre-registered claim
"same benefit, less battery" is supported at the second site. G reduced ramp exceedance by
3.66% using 91 kWh per episode; P reduced it by 3.26% using 173 kWh. That is 47% less battery
throughput for at least the same reduction.

S5 was nearly guaranteed by design (protocol §4): with persistence the released skill is 0, so the
weight is 0 and G never acts. S5 confirms that the implementation behaves as specified; it is not
evidence of a learned safety property.

## 2. Secondary analyses (descriptive; protocol §5)

### 2.1 All controllers (change in exceedance vs no battery, week-block 95% CI)

| Controller | Spatial LightGBM | Throughput (kWh/ep) | Reduction per 100 kWh | Stage 2 LightGBM | Perfect (bound) |
|---|---|---|---|---|---|
| Heuristic | −1.31% [−2.16, −0.50] | 10 | 13.7% | −1.32% | −97.25% |
| Adaptive MPC | **−7.01%** [−7.87, −6.11] | 574 | 1.22% | −2.95% | −99.75% |
| Stochastic MPC | −5.24% [−6.08, −4.44] | 261 | 2.01% | −1.91% | −99.63% |
| P (binary switch) | −3.26% [−4.13, −2.46] | 173 | 1.88% | −0.68% [−1.66, +0.22] | −99.39% |
| **G (graded switch)** | −3.66% [−4.45, −2.95] | 91 | 4.04% | −1.27% | −99.39% |
| Low-pass filter (α = 0.5) | −5.48% [−6.24, −4.71] | 151 | 3.63% | −2.08% | −77.94% |
| Graded low-pass filter | −3.44% [−3.98, −2.93] | 65 | **5.29%** | −1.34% | −77.91% |

With persistence, every skill-aware controller and the filter do nothing (0.00%, 0 kWh).
Adaptive MPC (+0.02%, 198 kWh) and stochastic MPC (+0.03%, 65 kWh) spend energy for no benefit.
There were no safety violations in any run. The binary switch idled 52% of decisions with the
spatial forecast and 63% with the Stage 2 forecast.

### 2.2 Replication of Stage 4 R1–R4 for P (same contrasts and margins as Kelmarsh)

| Test | Mean difference [95% CI] | p (Holm within family) | Result |
|---|---|---|---|
| R1: P reduces exceedance vs no battery | −33.9 kW [−45.4, −24.0] | 3.7e−10 | replicated |
| R2: P uses less throughput than adaptive | −401.7 kWh [−431.2, −370.4] | 6.0e−19 | replicated |
| R3: no material harm, persistence | 0.0 kW [0.0, 0.0] | 1.5e−24 | replicated |
| R4: no material harm, Stage 2 LightGBM | −7.1 kW [−18.5, +2.2] | 1.0e−17 | replicated |

All four Stage 4 Kelmarsh findings for P replicate at Penmanshiel. The Kelmarsh sealed R1 result
was −30.6 kW (−3.2%); the Penmanshiel result is −33.9 kW (−3.3%).

### 2.3 Low-pass filter and adaptive MPC versus G (post-hoc, spatial forecast)

| Contrast | Mean difference [95% CI] |
|---|---|
| Low-pass filter − G, exceedance | −18.9 kW [−23.9, −13.9] (filter reduces more) |
| Low-pass filter − G, throughput | +60.3 kWh [+52.5, +68.0] (filter uses more) |
| Low-pass filter − P, exceedance | −23.1 kW [−31.0, −15.9] |
| Graded low-pass − G, exceedance | +2.4 kW [−1.5, +6.6] (no clear difference) |
| Graded low-pass − G, throughput | −25.6 kWh [−33.7, −17.9] |
| Adaptive MPC − G, exceedance | −34.9 kW [−43.2, −26.7] (adaptive reduces more) |

These numbers are in `secondary_posthoc.json`. They are not confirmatory.

### 2.4 Forecast skill (evaluation period, 102,181 decisions)

| Forecast | MAE at 10 / 30 / 60 min (kW) | Skill vs persistence | Ramp correlation |
|---|---|---|---|
| Persistence | 93 / 148 / 187 | 0.000 | 0.00 |
| Stage 2 LightGBM | 95 / 150 / 191 | 0.116 | 0.23 |
| Spatial LightGBM | 93 / 148 / 189 | 0.148 | 0.27 |

The plateau of skill near 0.15 found at Kelmarsh repeats here. MAE barely moves, because the skill
score measures how well the forecast predicts *changes* in power, not its overall accuracy.

### 2.5 Economic view (post-hoc; `results/penmanshiel_sealed/ECONOMICS.md`)

Break-even ramp penalty (EUR per kW of exceedance avoided; low / central / high cost assumptions),
spatial forecast:

| Controller | Break-even, low / central / high |
|---|---|
| Graded low-pass filter | 0.03 / 0.06 / 0.14 |
| G (graded switch) | 0.03 / 0.08 / 0.18 |
| Low-pass filter | 0.04 / 0.09 / 0.20 |
| Stochastic MPC | 0.07 / 0.16 / 0.36 |
| P (binary switch) | 0.07 / 0.17 / 0.38 |
| Adaptive MPC | 0.11 / 0.27 / 0.59 |

The cost assumptions need sources in the paper `[CITE: Li-ion capex, cycle life; wholesale price]`.

### 2.6 Comparison across Penmanshiel periods (spatial forecast)

| Period | G change, throughput | P change, throughput |
|---|---|---|
| 2021 development | −3.63%, 77 kWh | −3.29%, 146 kWh |
| 2022 validation | −3.19%, 97 kWh | −3.08%, 186 kWh |
| **2023–2024 sealed** | **−3.66%, 91 kWh** | **−3.26%, 173 kWh** |

The sealed result matches development and validation closely. This does not suggest overfitting
to the earlier years.

## 3. Interpretation (honest reading)

1. **The confirmed contribution is efficiency, not maximum reduction.** The graded switch gives the
   binary switch's reduction (non-inferior, numerically slightly better) with about half the battery
   throughput, at a second site with no re-tuning, and it does nothing when the forecast has no
   skill.
2. **It is not the strongest ramp reducer.** Adaptive MPC (−7.0%, 574 kWh) and a forecast-driven
   low-pass filter (−5.5%, 151 kWh) reduce exceedance more. G's advantage is cost per kW avoided:
   the break-even penalty is about 3.4× lower than adaptive MPC's and 2× lower than P's.
   The graded low-pass filter is equally efficient, which shows that the **graded skill weight**,
   not the MPC, carries the efficiency gain. The filter result was found during Kelmarsh
   development (Week 1) and is replicated here; it should be reported as an important baseline.
3. **The limit is the forecast, not the controller.** With a perfect forecast every MPC removes
   more than 99% of exceedance, while the filters reach only 78%. With real SCADA-only forecasts
   (skill ≈ 0.15), all controllers achieve only single-digit reductions. Better ramp forecasts
   (e.g. NWP or lidar inputs) are the main route to larger gains.
4. **Safety:** there were no SOC or power violations in any of the 66,144 episode runs (2,067 episodes × 4 forecasts × 8 controllers).

## 4. Limitations

These are as stated in advance (protocol §8):
- two sites from one operator in one region;
- one control turbine at each site;
- SCADA-only forecasts;
- a 10-minute dispatch layer;
- graded-switch end points taken from simulation and Kelmarsh.

The low-pass and economic analyses are post-hoc. The economic assumptions are illustrative.
