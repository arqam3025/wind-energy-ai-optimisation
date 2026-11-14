# Stage 3.3 development notes: scenario-based stochastic MPC

**Study role:** SYNTHETIC_DEVELOPMENT. These results informed design decisions and
are **not** confirmatory evidence. No real data, fitted model or data admission is involved.

## Provenance

| Item | Value |
|---|---|
| Code commit | `669231d` (clean tree) |
| Command | `python -B -m publication_v2.stage33.experiment --seeds 1000 1001 1002 1003 1004 1005 --out publication_v2/stage33/runs/dev_ablation_v2.json` |
| Analysis | `python -B -m publication_v2.stage33.analysis publication_v2/stage33/runs/dev_ablation_v2.json` |
| Environment | Python 3.12.5, NumPy 2.5.4, SciPy 1.18.1 (HiGHS) |
| Scenarios | `stochastic` profile, volatility 1.0, 24 scored intervals, rolling conformal (alpha = 0.1) |
| Development seeds used | 1000–1005 (Stage 3.2 exploration also used 1000–1005) |
| Determinism | a re-run from the clean commit reproduced the earlier run exactly (excluding wall-clock time) |

Seeds 1000–1099 are reserved for development. Held-out seeds will be drawn
outside this range and run once, under a frozen protocol, after design is complete.

## Controllers

Stage 3.1 (unchanged): `uncontrolled`, `deterministic`, `fixed_margin`, `adaptive`, `heuristic`.

Stage 3.3 `stochastic` minimises the sample-average expected ramp exceedance over 5
Gaussian-shaped, comonotone scenarios scaled from the marginal conformal intervals,
with an SOC operating band (50–80%) and a do-no-harm gate (10 kW). Ablations:
`stochastic_no_gate` (gate off), `stochastic_terminal` (Stage 3.1 terminal SOC target
instead of band), `point_band_gate` (point forecast only).

## Results (totals over 6 scenarios; exceedance kW / throughput kWh)

| Forecast (MAE30) | Uncontrolled | Deterministic | Fixed margin | Adaptive (3.1) | **Stochastic (3.3)** |
|---|---|---|---|---|---|
| Perfect (0) | 2641 / 0 | 0 / 441 | 0 / 4976 | 0 / 441 | **0 / 430** |
| Oracle σ=25 (32) | 2641 / 0 | 143 / 574 | 0 / 4999 | 0 / 1750 | **15 / 730** |
| Oracle σ=50 (63) | 2641 / 0 | 216 / 787 | 4 / 5041 | 2 / 3464 | **13 / 1284** |
| Oracle σ=75 (95) | 2641 / 0 | 227 / 1036 | 51 / 5142 | 51 / 3737 | **6 / 2371** |
| Oracle σ=100 (126) | 2641 / 0 | 429 / 1510 | 298 / 5433 | 346 / 5159 | **327 / 3535** |
| Damped trend (316) | 2641 / 0 | 2683 / 177 | 4298 / 3243 | 4077 / 3259 | 4384 / 1996 |
| Persistence (234) | 2641 / 0 | 2641 / 0 | 2641 / 0 | 2671 / 538 | **2641 / 0** |

Empirical conformal coverage: marginal 0.91–0.92 (nominal 0.90); joint all-six-horizon 0.74–0.81.

## Development findings

1. **Lower throughput at similar ramp performance.** With a skilful forecast, stochastic MPC
   matched Stage 3.1 adaptive MPC's ramp exceedance (within a few kW) using 31–63% less
   throughput (σ=25: 730 vs 1750 kWh; σ=50: 1284 vs 3464; σ=75: 2371 vs 3737 with lower
   exceedance, 6 vs 51 kW). Against fixed-margin MPC, throughput fell 35–85%.
2. **The scenarios do the work.** With scenarios removed (`point_band_gate`), exceedance
   rose 33–72 kW per scenario for σ = 25–75 (bootstrap CIs exclude 0).
3. **The SOC band helps at higher forecast error.** Replacing the terminal target with the band
   cut throughput by 30–185 kWh per scenario for σ ≥ 50 at equal or lower exceedance.
4. **The gate is nearly inert.** Its effect on throughput was at most 12 kWh per scenario and it
   never changed exceedance. Keep it only as a safety mechanism, not as a contribution.
5. **No controller fixes a biased forecast (negative finding).** With the damped-trend forecast
   (MAE above persistence), every forecast-driven MPC increased exceedance over no battery;
   stochastic MPC by 290 kW per scenario [75, 616]. The value of control depends on forecast
   skill at predicting ramps, not on uncertainty handling alone.
6. **A persistence forecast gives no value, and stochastic MPC correctly stays idle**
   (adaptive MPC used 538 kWh for a slight increase in exceedance).
7. **Marginal coverage does not mean joint coverage:** about 92% marginal but about 80% joint.

## Round 2: causal forecasters and ramp-dependence model (commit `13070b1`)

Same seeds (1000–1005). Run: `--seeds 1000 1001 1002 1003 1004 1005 --out .../dev_full_v3.json`.

**Causal forecasters** (30-minute MAE in kW; persistence 234): damped trend 316, mean reversion 234
(285 vs 302 at 60 minutes), skill combination 237. In the `stochastic` simulator, weather fronts are
unpredictable jumps, so forecasters using past data only gain little over persistence.

| Forecast | Uncontrolled | Deterministic | Adaptive (3.1) | Stochastic | Stochastic (increments) |
|---|---|---|---|---|---|
| Oracle σ=100 | 2641 / 0 | 429 / 1510 | 346 / 5159 | 327 / 3535 | 137 / 3843 |
| Oracle σ=150 (MAE30 186) | 2641 / 0 | 901 / 2346 | 1276 / 6059 | 1112 / 6359 | 1026 / 6311 |
| Oracle σ=200 (MAE30 244) | 2641 / 0 | 2109 / 3438 | 3437 / 6578 | 2727 / 6019 | 2798 / 6181 |
| Mean reversion | 2641 / 0 | 2558 / 14 | 3417 / 3639 | 3009 / 1490 | 3064 / 1740 |
| Skill combination | 2641 / 0 | 2641 / 0 | 2868 / 2420 | 2641 / 27 | 2747 / 116 |

8. **Break-even forecast skill.** The benefit over no battery disappears between a 30-minute MAE of
   186 kW (−269 kW per scenario) and 244 kW (no benefit), which is about persistence-level error.
   At high oracle error, the simpler deterministic and heuristic controllers beat stochastic MPC
   on exceedance.
9. **The hypothesis was rejected.** Comonotone scenarios were suspected of causing harm with causal
   forecasts. Independent increments did not reduce that harm (mean reversion +71 vs +61 kW per
   scenario; persistence +23 vs 0). Its gain under oracle forecasts is partly by construction,
   because oracle errors are generated as a random walk.
10. **Pre-held-out decision:** `stochastic` (comonotone) remains the primary controller;
    `stochastic_increments` is a secondary analysis.
11. With mean reversion, stochastic MPC harms less than adaptive MPC (+61 vs +129 kW per scenario)
    but does not avoid harm. Deterministic MPC barely acts (14 kWh) and helps slightly.

## Round 3: forecast-skill safety switch (commit `c7595d0`)

The adapter derives SS = 1 − SSE(forecast) / SSE(persistence), pooled over horizons, from the
verified released residual ledgers. `stochastic_skill` dispatches only if SS > 0.10. This
threshold was fixed **before** the run; 0, 0.05 and 0.20 are reported as sensitivity analyses.
Mean released SS: perfect 1.00, oracle σ=25/50/75/100/150/200: 0.95/0.82/0.62/0.37/−0.29/−1.13;
damped trend −0.81; persistence 0.00; mean reversion −0.03; skill combination +0.04.

| Forecast | Uncontrolled | Stochastic | Stochastic + switch (0.10) | Switch 0.20 |
|---|---|---|---|---|
| Oracle σ=25 | 2641 / 0 | 15 / 730 | 15 / 730 | 15 / 730 |
| Oracle σ=75 | 2641 / 0 | 6 / 2371 | 6 / 2371 | 6 / 2371 |
| Oracle σ=100 | 2641 / 0 | 327 / 3535 | 533 / 3377 | 662 / 3253 |
| Oracle σ=150 | 2641 / 0 | 1112 / 6359 | 1518 / 4417 | 1521 / 3346 |
| Oracle σ=200 | 2641 / 0 | 2727 / 6019 | 2308 / 1089 | 2308 / 1089 |
| Damped trend | 2641 / 0 | 4384 / 1996 | **2641 / 0** | 2641 / 0 |
| Mean reversion | 2641 / 0 | 3009 / 1490 | 2866 / 370 | **2641 / 0** |
| Persistence / skill combination | 2641 / 0 | 2641 / 0–27 | 2641 / 0 | 2641 / 0 |

12. **The switch removes the largest harm** (damped trend: +290 kW per scenario → 0) and turns
    oracle σ=200 from no benefit into a benefit over no battery (2308 vs 2641 kW, with 82% less
    throughput). With mean reversion it reduces harm by 37% at 0.10 and removes it at 0.20.
13. **The cost:** at intermediate skill (oracle σ=100–150) the switch closes in some windows that
    were in fact useful (exceedance 327→533 and 1112→1518 kW, still far below no battery's
    2641). Pooled level-MSE skill is dominated by long-horizon errors, so it is a
    **conservative** proxy for value to control.
14. **Pre-held-out decision:** the primary controller for the confirmatory evaluation is
    `stochastic_skill` (threshold 0.10, prespecified), with `stochastic` (no switch) as the
    key secondary comparison and the thresholds 0, 0.05 and 0.20 as sensitivity analyses.
    No further design changes before the frozen protocol.

## Limitations

6 scenarios per cell, so the smallest attainable two-sided Wilcoxon p is 0.031: these are
descriptive results. The scenario shape (Gaussian) and the dependence across horizons
(comonotone) are assumptions. The oracle forecasts are privileged benchmarks that a
causal forecaster cannot achieve. Everything here is synthetic.
