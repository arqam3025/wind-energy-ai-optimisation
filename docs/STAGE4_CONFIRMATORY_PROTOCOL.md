# Stage 4 confirmatory protocol: real-data test on Kelmarsh (sealed 2023–2024)

**Status: FROZEN on 2026-11-17, approved by the study author.** It is binding from the commit that writes its SHA-256 into
`publication_v2/stage4/confirmatory.py` (`PROTOCOL_SHA256`); that commit is the frozen
commit. The sealed years have not been extracted, read or summarised.

## 1. Purpose

To test, on real wind-turbine data never seen during design, whether the Stage 3.3 findings hold:

- the skill-gated stochastic MPC (P) reduces ramp exceedance when the forecast has skill;
- P does so with less battery throughput than adaptive MPC;
- P does no material harm when the forecast lacks skill.

## 2. Data

| Item | Value |
|---|---|
| Source | Kelmarsh wind farm SCADA, Zenodo DOI 10.5281/zenodo.16807551, CC-BY-4.0 (`docs/DATA_ADMISSION_KELMARSH.md`) |
| Unit | Turbine 1 (Senvion MM92, 2.05 MW); turbines 2–6 used only as forecast inputs |
| Training | 2018–2021 (development) |
| Test | **2023–2024 (sealed)**, files MD5-verified, opened only by the frozen runner |
| Signal | `Power (kW)` 10-minute mean, y = max(0, P); UTC; row label = interval start; value available at label + 10 min |
| Missing data | No imputation. An episode is eligible only if every realised value, feature and calibration window it needs exists; ineligible episodes are counted and reported |

2022 (validation) is used once, before the freeze, as a check of the complete pipeline (Section 8).
It is not part of the test.

## 3. Pipeline (fixed)

- **Forecasters**, fitted once on 2018–2021 with the Stage 2 LightGBM default hyperparameters,
  deterministic, seed 20261101:
  - `lightgbm_spatial`: the Stage 2 14-feature contract plus causal neighbour-turbine features
    (selected in development round 2 on an inner split);
  - `lightgbm`: the Stage 2 14-feature contract only.
- **Baselines and reference:** `persistence` as the causal baseline, and `perfect` as a privileged
  upper bound that uses realised future values (it is not a deployable forecaster).
- **Uncertainty:** rolling split-conformal, last 48 released absolute residuals per horizon,
  finite-sample rank, α = 0.1, at least 30 samples, calibration targets strictly before the
  decision. The released skill score versus persistence uses the same pairs.
- **Controllers:** unchanged Stage 3.1/3.3 code and configurations: uncontrolled, heuristic,
  deterministic, fixed-margin, adaptive, stochastic, and **P = `stochastic_skill`** (switch
  threshold 0.10, prespecified in Stage 3.3, not re-tuned on real data).
- **Battery and scoring:** 2 MWh, ±1 MW, SOC 40–90% (initial 65%), η = 0.95. Ramp reference
  200 kW per 10 minutes. Exceedance is scored with the Stage 3.1 metric.
- **Episodes:** every eligible 8-hour block of 2023–2024 starting at 00:00/08:00/16:00 UTC. The
  evaluation series starts on 2023-01-01, so every calibration window is out of sample. The same
  episode set is used for all forecasts and controllers.

## 4. Hypotheses (primary; Holm correction across all four; one-sided; α = 0.05)

U is the mean uncontrolled exceedance per episode in the test set.

| ID | Forecast | Claim | Contrast | Margin |
|---|---|---|---|---|
| R1 | lightgbm_spatial | P reduces ramp exceedance versus no battery | exceedance(P) − exceedance(uncontrolled) < 0 | 0 |
| R2 | lightgbm_spatial | P uses less throughput than adaptive MPC | throughput(P) − throughput(adaptive) < 0 | 0 |
| R3 | persistence | P does no material harm without forecast skill | exceedance(P) − exceedance(uncontrolled) < m | m = 0.05 U |
| R4 | lightgbm | P does no material harm with a weakly skilful forecast | exceedance(P) − exceedance(uncontrolled) < m | m = 0.05 U |

**Inference.** Consecutive episodes are serially dependent, so the unit is the ISO week.
- Paired episode differences are averaged within each week.
- The test is a one-sided Wilcoxon signed-rank test on the weekly means minus the margin.
- 95% CIs come from a week-block bootstrap (4,000 resamples, seed 20261117).
- Code: `publication_v2/stage4/analysis.py`.

All four results are reported, whatever the outcome.

## 5. Secondary and descriptive analyses (no multiplicity claims)

1. All controllers × forecasts: exceedance, change versus no battery (week-block CI), throughput,
   reduction per MWh, ramp violations, fraction of decisions idled by the switch.
2. The perfect-forecast headroom versus the real forecasts (value of forecast information).
3. Forecast skill on the test years: MAE per horizon, pooled MSE skill versus persistence, ramp
   correlation.
4. Comparison with the development (2021) and validation (2022) results.
5. Safety and accounting: SOC, power and simultaneous charge/discharge violations, energy residual,
   solver failures.

## 6. Interpretation rules

- **R1** supported: real-data benefit is confirmed. Its size is judged against the
  perfect-forecast headroom (secondary 2), not claimed as large.
- **R2** supported together with R1: the efficiency finding is confirmed on real data.
- **R3** and **R4** supported: the safety switch is confirmed on real data. Note that R3 is nearly
  guaranteed by design, because the switch idles when the skill score is not above 0.10.
- A failed hypothesis is reported as a failure, with its estimate and CI, and discussed.

## 7. Execution and integrity

1. **Freeze.** Compute this file's SHA-256, set `PROTOCOL_SHA256` in `confirmatory.py`, and commit.
2. **Run once** from a clean checkout of the frozen commit:
   `python -B -m publication_v2.stage4.confirmatory --out publication_v2/stage4/runs/sealed_v1`.
   - The runner refuses if the hash differs, the tree is modified, or a completed run exists.
   - The sealed years can be opened only through this runner.
3. **Interruptions.** A resume is allowed only from the same commit and protocol; it is logged in
   `DEVIATIONS.md`.
4. **No changes after the run.** No change to code, data rules, forecasters, controllers, margins
   or tests. Every result file is SHA-256-recorded in `COMPLETED.json`.

## 8. Pre-freeze validation check (2022)

The complete pipeline (fit 2018–2021, closed loop on 2022) is run once with
`experiment.py --stage validation`, and the same analysis is applied. The check exists to find
defects, not to select designs. Any change made after it must be a documented defect fix. Its
results are reported alongside the test.

## 9. Known limitations (stated in advance)

- One site and one turbine as the primary unit, with SCADA-only forecasts.
- The 10-minute decision structure models a dispatch-scheduling layer, not second-scale
  ramp-rate control.
- The switch threshold and controller settings come from simulation and are not tuned for this site.
