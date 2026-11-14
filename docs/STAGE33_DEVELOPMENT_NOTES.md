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

## Limitations

6 scenarios per cell, so the smallest attainable two-sided Wilcoxon p is 0.031: these are
descriptive results. The scenario shape (Gaussian) and the dependence across horizons
(comonotone) are assumptions. The oracle forecasts are privileged benchmarks that a
causal forecaster cannot achieve. Everything here is synthetic.
