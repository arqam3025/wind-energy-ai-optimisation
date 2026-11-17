# Stage 5 confirmatory protocol: second-site test on Penmanshiel (sealed 2023–2024)

**Status: DRAFT, not frozen.** It becomes binding only when its SHA-256 is written into
`publication_v2/stage5/confirmatory.py` (`PROTOCOL_SHA256`) and committed; that commit is the
frozen commit. The sealed years have been downloaded and MD5-verified but not read.

## 1. Purpose

To test, at a second wind farm whose test data has never been seen, two things:

- whether the **graded forecast-skill switch** (designed in Stage 5 on Kelmarsh development
  data) keeps the binary switch's ramp reduction with less battery use;
- whether the proposed approach transfers to a new site without re-tuning.

Design choices were informed by Kelmarsh, including its sealed results, and by Penmanshiel
development data (2018–2021) and one validation check on 2022. That is the purpose of a
second-site confirmation, and it is stated here.

## 2. Data

| Item | Value |
|---|---|
| Source | Penmanshiel wind farm SCADA, Zenodo DOI 10.5281/zenodo.16807304, CC-BY-4.0 (`docs/DATA_ADMISSION_PENMANSHIEL.md`) |
| Unit | Turbine WT11 (Senvion MM82, 2.05 MW); WT12–WT15 used only as forecast inputs |
| Training | 2018–2021 |
| Test | **2023–2024 (sealed)**, opened only by the frozen runner |
| Rules | As in Stage 4: UTC, label + 10 min = availability, y = max(0, P), no imputation, cumulative-export de-duplication (keep the most complete row version; refuse on conflict); rows absent from a file are missing |

## 3. Pipeline (fixed; identical to Stage 4 except the added controllers)

- **Forecasters:** fitted once on 2018–2021 with the Stage 2 LightGBM defaults (seed 20261101).
  - `lightgbm_spatial`: the Stage 2 features plus the Stage 4 neighbour features, using the four
    neighbours WT12–WT15;
  - `lightgbm`: the Stage 2 features only;
  - `persistence`;
  - `perfect` (privileged upper bound).
- **Uncertainty and skill:** rolling split-conformal (48 released residuals per horizon,
  α = 0.1, at least 30 samples, targets strictly before the decision). The released skill score
  versus persistence uses the same pairs.
- **Controllers** (unchanged code and configurations):
  - uncontrolled, heuristic, adaptive MPC, stochastic MPC;
  - **P** = `stochastic_skill`: binary switch at 0.10 (Stage 3.3);
  - **G** = `graded_mpc`: stochastic MPC with all planned flows scaled by
    w = clip(skill / 0.30, 0, 1) (Stage 5);
  - `lowpass_fast`: low-pass filter, α = 0.5, SOC feedback 1/6 per step, reference SOC 65%;
  - `graded_lowpass`: the filter scaled by the same weight.
- **Battery and scoring:** 2 MWh, ±1 MW, SOC 40–90% (initial 65%), η = 0.95. Ramp reference
  200 kW per 10 minutes; Stage 3.1 exceedance metric.
- **Episodes:** every eligible 8-hour block of 2023–2024 starting at 00:00/08:00/16:00 UTC, with
  the evaluation series starting on 2023-01-01. One paired episode set for all forecasts and
  controllers.

## 4. Primary hypotheses (Holm across all six; one-sided; α = 0.05)

U is the mean uncontrolled exceedance per episode in the test set.

| ID | Forecast | Claim | Contrast | Margin |
|---|---|---|---|---|
| S1 | lightgbm_spatial | G reduces ramp exceedance versus no battery | exceedance(G) − exceedance(uncontrolled) < 0 | 0 |
| S2 | lightgbm_spatial | G uses less throughput than P | throughput(G) − throughput(P) < 0 | 0 |
| S3 | lightgbm_spatial | G's exceedance is non-inferior to P's | exceedance(G) − exceedance(P) < m | m = 0.01 U |
| S4 | lightgbm_spatial | G uses less throughput than adaptive MPC | throughput(G) − throughput(adaptive) < 0 | 0 |
| S5 | persistence | G does no material harm without skill | exceedance(G) − exceedance(uncontrolled) < m | m = 0.05 U |
| S6 | lightgbm | G does no material harm with a weak forecast | exceedance(G) − exceedance(uncontrolled) < m | m = 0.05 U |

**Inference:** as in Stage 4.
- The unit is the ISO week: paired episode differences are averaged within each week.
- The test is a one-sided Wilcoxon signed-rank test on the weekly means minus the margin.
- 95% CIs come from a week-block bootstrap (4,000 resamples, seed 20261117).
- Code: `publication_v2/stage5/analysis.py`.

All results are reported, whatever the outcome. S2 and S3 together form the "same benefit, less
battery" claim, which is interpreted only if both are supported. S5 is nearly guaranteed by
design, because the weight is 0 whenever skill ≤ 0.

## 5. Secondary analyses (descriptive; no multiplicity claims)

1. All controllers × forecasts: change versus no battery (week-block CI), throughput, reduction per
   100 kWh, and the fraction of decisions idled by the binary switch.
2. **Replication of Stage 4 R1–R4 for P** at Penmanshiel, with the same contrasts and margins.
3. **Low-pass filter comparisons:** `lowpass_fast` and `graded_lowpass` versus G and P.
4. Perfect-forecast headroom, and forecast skill (MAE per horizon, skill versus persistence, ramp
   correlation).
5. **Economic view:** break-even ramp penalty (`publication_v2/stage5/economics.py`; central,
   low and high assumptions).
6. Safety and accounting checks.
7. Comparison with Penmanshiel 2021 (development) and 2022 (validation).

## 6. Execution and integrity

1. **Freeze:** compute this file's SHA-256, set `PROTOCOL_SHA256`, and commit.
2. **Run once** from a clean checkout of the frozen commit:
   `python -B -m publication_v2.stage5.confirmatory --out publication_v2/stage5/runs/pen_sealed_v1`.
3. **Loader failures:** if the loader fails on the sealed files, the run stops before any outcome.
   - Only a structural check (row counts and comparisons, no values) is allowed for diagnosis.
   - A fix is allowed only if it reproduces 2021 and 2022 bit for bit.
   - Everything is logged as a deviation.
4. **No changes after the run:** no change to code, rules, models, controllers, margins or tests.
   Every output is SHA-256-recorded.

## 7. Pre-freeze validation (2022)

Run once with `site_experiment.py --stage validation` and analysed with the same code. It exists to
find defects, not to select designs; any change after it must be a documented defect fix.

## 8. Known limitations (stated in advance)

- Two sites from one operator and region (UK), with one turbine as the control unit at each.
- SCADA-only forecasts.
- A 10-minute dispatch layer.
- The graded-switch end points (0, 0.30) and the controller settings come from simulation and
  Kelmarsh; they are not tuned for Penmanshiel.
