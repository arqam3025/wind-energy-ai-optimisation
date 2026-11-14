# Stage 3.3 confirmatory evaluation protocol

**Status:** DRAFT for review. It becomes binding once frozen: its SHA-256 is recorded in
`publication_v2/stage33/confirmatory.py` (`PROTOCOL_SHA256`) and committed. After
freezing, any change to this file makes the runner refuse to start.

**Study role:** SYNTHETIC_CONFIRMATORY_HELD_OUT_SEEDS. This is a prospective evaluation
on simulator seeds that were never used during development. It tests whether the
development findings generalise to **new realisations of the same synthetic generator**.
It does **not** test generalisation to real wind farms, other generators or real data.
No real data, fitted model or data admission is involved.

## 1. Background and development history

Design decisions were made on development seeds 1000–1005 only (seeds 1000–1099 are reserved
for development) and are recorded in `docs/STAGE33_DEVELOPMENT_NOTES.md` (rounds 1–3), including
rejected hypotheses. The design is closed. The development results themselves are
**not** part of the confirmatory evidence.

## 2. Objectives

To test, on held-out seeds, whether scenario-based stochastic MPC with a forecast-skill safety switch:
1. reduces grid ramp exceedance compared with no battery when forecasts are skilful;
2. uses less battery throughput than the Stage 3.1 adaptive MPC, without materially worse
   ramp exceedance; and
3. does not materially increase ramp exceedance compared with no battery when forecasts lack skill.

## 3. Simulation design (fixed)

| Item | Value |
|---|---|
| Wind generator | `stochastic` profile (`STOCHASTIC_WIND_V1`): seeded AR(1) wind speed with random fronts, generic 2 MW cubic power curve |
| Volatility levels | 0.7, 1.0, 1.5 |
| Held-out seeds | 700000–700049 (50 seeds; disjoint from development seeds 1000–1099) |
| Episode | 64 warm-up origins + 48 scored 10-minute intervals (8 h) + 5-interval scoring tail |
| Battery | 2 MWh, ±1 MW, SOC 40–90%, initial 65%, 95% efficiency each way (Stage 3.1 `BatteryConfig`) |
| Ramp reference | 200 kW per 10-minute interval (Stage 3.1 `MPCConfig`) |
| Uncertainty | rolling conformal intervals, alpha = 0.1, window 48, Stage 2 `calibrate` |
| Scenario unit | (seed, volatility), giving n = 150 paired scenarios per forecast condition |

**Forecast conditions** (9):
- **Skilful:** `oracle25`, `oracle50`, `oracle100`. These are privileged benchmarks: the announced
  recipe plus random-walk error with step σ = 25/50/100 kW. They cannot be achieved by a causal forecaster.
- **Skill gradient (secondary only):** `oracle150`, `oracle200`.
- **Without skill (causal, past data only):** `persistence`, `mean_reversion`, `skill_combo`, `damped_trend`.

**Controllers** (14, every one on every scenario, with identical inputs per scenario):
- Stage 3.1: `uncontrolled`, `deterministic`, `fixed_margin`, `adaptive`, `heuristic`.
- Stage 3.3: **`stochastic_skill` (PRIMARY: skill switch 0.10)** and `stochastic` (no switch).
- Sensitivity: `stochastic_skill00`, `stochastic_skill05`, `stochastic_skill20`.
- Ablations: `stochastic_increments`, `stochastic_no_gate`, `stochastic_terminal`, `point_band_gate`.

All configurations are exactly those in `publication_v2/stage33/experiment.py` at the frozen commit.

## 4. Outcomes

- **Primary outcome:** total ramp exceedance per episode (kW), the sum over scored intervals of
  max(0, |Δgrid| − 200).
- **Key secondary outcome:** total battery throughput per episode (kWh, charge + discharge).
- **Other secondary outcomes:** number of ramp violations, maximum ramp, conversion loss, SOC range,
  safety fallbacks, optimisation failures, mean computation time, forecast MAE per horizon,
  empirical marginal and joint (all six horizons) interval coverage, and released skill score.
- **Physical invariants** (must be zero, otherwise the episode errors and the run fails): SOC
  violations, power-limit violations, simultaneous charge and discharge, and energy-accounting residual.

## 5. Primary hypotheses and tests

Let P = `stochastic_skill`. Within each forecast condition, d_i is the paired difference over the
n = 150 scenarios. The non-inferiority margin for a condition is **m = 5% of the mean uncontrolled
exceedance per scenario in that condition**.

| ID | Conditions | Hypothesis (alternative) | Test |
|---|---|---|---|
| H1 | oracle25, oracle50, oracle100 | exceedance(P) < exceedance(uncontrolled) | one-sided Wilcoxon signed-rank on d_i |
| H2a | oracle25, oracle50, oracle100 | throughput(P) < throughput(adaptive) | one-sided Wilcoxon on d_i |
| H2b | oracle25, oracle50, oracle100 | exceedance(P) − exceedance(adaptive) < m (non-inferiority) | one-sided Wilcoxon on d_i − m |
| H3 | persistence, mean_reversion, skill_combo, damped_trend | exceedance(P) − exceedance(uncontrolled) < m (no material harm) | one-sided Wilcoxon on d_i − m |

There are **13 primary tests**, Holm-adjusted together at a family-wise α = 0.05 (one-sided). A
hypothesis for a condition is supported if its Holm-adjusted p < 0.05. For each test the report
gives the mean paired difference with a seeded percentile-bootstrap 95% CI (10,000 resamples,
seed 20261114), the median difference, and the number of scenarios where P was better.
H2 is interpreted as an efficiency claim only where both H2a and H2b are supported.

Implementation: `publication_v2/stage33/confirmatory_analysis.py`
(`primary_tests`, `holm`), unit-tested in `tests/test_confirmatory.py`.

## 6. Secondary and exploratory analyses (descriptive, no multiplicity claims)

1. All controllers × all conditions, per volatility level and pooled (totals, paired contrasts
   with bootstrap CIs; `analysis.py`).
2. **Break-even curve:** exceedance reduction against no battery as a function of forecast skill
   (oracle σ = 25…200; MAE30 and released skill score), for P, `stochastic` and Stage 3.1 controllers.
3. **Throughput–exceedance trade-off** per controller.
4. **Ablations:** switch (P vs `stochastic`), sensitivity of the switch threshold (0/0.05/0.10/0.20),
   the do-no-harm gate, SOC band vs terminal target, scenarios vs point forecast, and comonotone vs
   independent increments.
5. Interaction with volatility.
6. Conformal coverage diagnostics: marginal per horizon vs joint six-horizon coverage.
7. Computation time.

## 7. Execution and integrity rules

1. Freeze: compute this file's SHA-256, set `PROTOCOL_SHA256`, and commit (the frozen commit).
2. Run once from the frozen commit with a clean tree:
   `python -B -m publication_v2.stage33.confirmatory --out publication_v2/stage33/runs/confirmatory_v1`
   The runner refuses if the protocol hash differs, tracked files are modified, or a completed run
   exists. Results are checkpointed per condition. An interrupted run resumes only from the same
   commit and protocol (computation is deterministic) and must be reported.
3. Analyse: `python -B -m publication_v2.stage33.confirmatory_analysis publication_v2/stage33/runs/confirmatory_v1 --out <dir>`.
   The loader verifies the SHA-256 of every result file.
4. No change to code, configurations, seeds, outcomes, margins or tests after the run. All primary
   results are reported, whatever the outcome. Any deviation (crash, resume, environment change,
   bug discovered afterwards) is documented in a deviations section of the results report,
   together with its impact.
5. If a bug affecting results is found after the run, the original results are preserved
   unchanged, the fix is committed separately, and any re-run is labelled a corrected re-analysis,
   not a replacement.

## 8. Known limitations (stated in advance)

- Synthetic generator only; confirmation is across seeds, not across data-generating processes.
- The skilful conditions are privileged oracles; the causal forecasters available have little
  skill against this generator.
- Oracle errors are generated as random walks, which favours the independent-increments
  ablation by construction.
- The Gaussian scenario shape and the comonotone dependence are modelling assumptions.
- Conformal intervals give marginal coverage only, which is not a joint-trajectory guarantee.
- The battery and turbine parameters are simulation assumptions, not a specific installation.
- The development seeds and the held-out seeds come from the same generator, so model
  misspecification relative to real wind is untested.

## 9. Planned compute

18,900 episodes (9 × 3 × 50 × 14), an estimated 5–7 hours on 15 worker processes (the pipeline
rehearsal ran 1,134 episodes in 24 minutes).

## 10. Pipeline rehearsal (before freezing)

The complete pipeline (runner, checksummed result files, verified loading, the 13 primary tests
and the report) was rehearsed on **development** seeds 1006–1008 (`--rehearsal-seeds`, study
role PIPELINE_REHEARSAL_DEVELOPMENT_SEEDS, n = 9 per condition). It confirmed that the software
executes as specified. Its numbers are development evidence, not confirmatory evidence.
