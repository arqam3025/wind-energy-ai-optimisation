# Stage 4 confirmatory results: real data, Kelmarsh sealed test 2023–2024

**Study role:** REAL_DATA_CONFIRMATORY_SEALED_TEST. This is one site with turbine 1 as the control
unit and SCADA-only forecasts (see Limitations).

| Item | Value |
|---|---|
| Protocol | `docs/STAGE4_CONFIRMATORY_PROTOCOL.md`, SHA-256 `d8337ad97bfd55fdffd368002fc8ffe61a94afb5ccdcc5e9ea1b1b771d84bda7`, frozen at `e772ef0` (tag `stage4-protocol-frozen`) |
| Code that produced the results | `ae6f85e` (loader defect fix after the freeze; deviation D1), clean tree verified by the runner |
| Data | Kelmarsh SCADA, Zenodo 10.5281/zenodo.16807551 (CC-BY-4.0); training 2018–2021, test 2023–2024 |
| Design | 2,048 paired 8-hour episodes (105 ISO weeks) × 4 forecasts × 7 controllers |
| Inference | Weekly units; one-sided Wilcoxon on weekly means; week-block bootstrap 95% CIs; Holm across R1–R4 |
| Run | 2026-11-17, 14:24–15:33 UTC, exit 0; all outputs SHA-256-recorded (`COMPLETED.json`) |
| Artefacts | `publication_v2/stage4/results/sealed_v3/`; figure `docs/figures_stage4_real_data/fig6_real_data.*` |

P denotes the proposed controller: stochastic MPC with the skill switch, threshold 0.10, unchanged
from simulation. U is the mean uncontrolled exceedance, 958.2 kW per episode.

## 1. Primary hypotheses: all four supported

| Test | Forecast | Claim | Mean difference [95% CI] | p (Holm) | Result |
|---|---|---|---|---|---|
| R1 | LightGBM + neighbours | P reduces exceedance vs no battery | −30.6 kW [−39.7, −21.9] (−3.2%) | 1.5e−10 | supported |
| R2 | LightGBM + neighbours | P uses less throughput than adaptive MPC | −429 kWh [−458, −399] | 8.8e−19 | supported |
| R3 | Persistence | no material harm (margin 47.9 kW = 5% U) | 0.0 kW [0.0, 0.0] | 2.4e−24 | supported |
| R4 | LightGBM (Stage 2 features) | no material harm (margin 47.9 kW) | −3.2 kW [−9.1, +2.7] | 1.5e−18 | supported |

As stated in the protocol, R3 is nearly guaranteed by design: the switch idles whenever released
skill does not exceed 0.10, which is always the case with persistence.

## 2. All controllers (mean per episode; change vs no battery with week-block 95% CI)

| Forecast | Controller | Change in exceedance | Throughput (kWh) | Reduction per MWh (kW) | Switch idle |
|---|---|---|---|---|---|
| Neighbours | Fixed-margin MPC | −8.3% [−9.2, −7.3] | 745 | 107 | — |
| Neighbours | Adaptive MPC | −7.4% [−8.3, −6.4] | 587 | 121 | — |
| Neighbours | Stochastic MPC | −5.1% [−6.0, −4.3] | 234 | 210 | — |
| Neighbours | **P** | **−3.2% [−4.0, −2.4]** | **158** | **194** | 46% |
| LightGBM | Fixed-margin MPC | −3.5% [−4.4, −2.6] | 707 | 47 | — |
| LightGBM | Adaptive MPC | −2.7% [−3.6, −1.7] | 557 | 46 | — |
| LightGBM | Stochastic MPC | −1.7% [−2.3, −1.0] | 202 | 79 | — |
| LightGBM | P | −0.3% [−0.9, +0.3] | 118 | 27 | 54% |
| Persistence | Stochastic MPC | **+0.2% [+0.1, +0.4] (harm)** | 51 | — | — |
| Persistence | P | 0.0% | 0 | — | 100% |
| Perfect (privileged) | P | −99.8% [−99.9, −99.8] | 149 | 6,408 | 1% |

Deterministic MPC and the heuristic barely act with real forecasts (changes of −0.2% to 0.0%,
throughput at most 3 kWh).

## 3. Forecast skill on 2023–2024 (100,971 decisions)

| Forecast | MAE 10…60 min (kW) | Skill vs persistence | Ramp correlation (true \|ramp\| > 200 kW) |
|---|---|---|---|
| Persistence | 97 130 150 164 175 185 | 0 | 0 |
| LightGBM (Stage 2 features) | 97 129 148 161 173 182 | +0.123 | +0.22 |
| LightGBM + neighbours | 94 126 145 159 170 180 | +0.146 | +0.25 |

## 4. Consistency across periods (P with the neighbour forecaster)

| Period | Role | Episodes | Change in exceedance | Throughput | R1–R4 |
|---|---|---|---|---|---|
| 2021 | development | 1,027 | −3.1% [−4.4, −1.7] | 116 kWh | all supported |
| 2022 | pre-freeze validation | 1,048 | −2.6% [−3.9, −1.2] | 144 kWh | all supported |
| **2023–2024** | **sealed test** | **2,048** | **−3.2% [−4.0, −2.4]** | **158 kWh** | **all supported** |

## 5. Safety and integrity

- **Safety:** no SOC, power or simultaneous charge/discharge violations in any of 57,344 episodes.
  Every solver failure was handled by the safe fallback; P had 17 across all forecasts.
- **Deviation D1** (full record in `results/sealed_v3/DEVIATIONS.md`): the 2023–2024 files turned
  out to be cumulative exports with partially blank duplicate copies of each row. Two runs from
  the frozen code (`e772ef0`, then the first fix `ff939f8`) **stopped at data loading, before
  any outcome was computed.**
  - **Inspection:** the author approved a structural inspection, limited to timestamps and row
    counts/comparisons with no values viewed. It established that the copies differ only by
    value → NaN.
  - **Fix:** the corrected loader (`ae6f85e`) keeps the most complete version of each row and
    refuses on any conflict.
  - **Verification:** it reproduces the 2021 and 2022 series, forecasts and training hash bit for
    bit.
  - **Unchanged:** the protocol, hypotheses, models, controllers and analysis.

## 6. What the real-data evidence shows

1. **The controller works on real data, but forecast quality limits the benefit.** P gives a
   small, statistically robust reduction (−3.2%), consistent across three independent years.
   With a perfect forecast, the same controller and battery remove 99.8%.
2. **The efficiency result transfers from simulation.** P uses 73% less throughput than adaptive
   MPC. The stochastic controllers achieve the highest reduction per MWh, about 1.6–2 times that
   of adaptive or fixed-margin MPC.
3. **The safety switch matters on real data.** Unswitched stochastic MPC causes a small but
   detectable harm with persistence forecasts (+0.2%). P prevents it and does no harm with the
   weaker LightGBM forecaster.
4. **The switch costs benefit at intermediate skill.** With skill ≈ 0.15, near the 0.10 threshold,
   the switch idles 46% of decisions, so P achieves about 60% of the unswitched controller's
   reduction at 68% of its throughput. The same trade-off appeared in simulation.
5. **SCADA-only forecasts carry little ramp information at 10–60 minutes** (skill 0.12–0.15, ramp
   correlation about 0.25). This is the main obstacle to larger real-world gains.

## Limitations

- One wind farm, with one turbine as the control unit. The farm-level aggregate was examined in
  development only.
- Forecasts use SCADA only, with no NWP, lidar or upstream measurements.
- The 10-minute decision structure represents a dispatch-scheduling layer, not second-scale
  ramp-rate control.
- The controller settings and switch threshold come from simulation and were not tuned for the site.
