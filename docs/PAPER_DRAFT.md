# How good must a wind forecast be? Skill-gated stochastic MPC for wind–battery ramp control with conformal uncertainty

*Manuscript draft. Sections 1–2 and 5–6 are written; Sections 3–4 are completed from the frozen
confirmatory run (`docs/STAGE33_CONFIRMATORY_RESULTS.md`). `[CITE: …]` marks places that need a
reference: fill these from your own literature search. No reference has been invented.*

## Abstract (to finalise after results)

Battery energy storage can smooth the short-term ramps of wind generation, but the controller acts
on forecasts that may be wrong, and unnecessary cycling costs throughput and efficiency. We study
when forecast-driven ramp control pays off. We combine (i) split-conformal prediction intervals at
six horizons (10–60 min), (ii) a scenario-based stochastic model predictive controller (MPC) that
minimises the expected ramp-threshold exceedance as a mixed-integer linear program, and (iii) a
forecast-skill safety switch that keeps the battery idle unless verified, released residuals show
skill over persistence. In a pre-registered evaluation on held-out simulator seeds
(n = 150 paired scenarios per condition, 14 controllers, 9 forecast conditions), we find
**[RESULTS: H1, H2, H3 summary]**. A forecast-quality break-even exists near persistence-level
error, and marginal conformal coverage (≈0.9) does not translate into joint six-horizon coverage
(≈0.7–0.8). All code, protocol, development history and checksummed results are released.

## 1. Introduction (outline with key claims)

1. Wind variability and grid ramp-rate requirements; storage as a smoothing resource.
   [CITE: grid-code ramp-rate limits for wind/PV plants] [CITE: battery-based ramp-rate control reviews]
2. MPC is the standard framework for forecast-based storage dispatch.
   [CITE: MPC for wind–storage smoothing] [CITE: stochastic/robust MPC for renewables]
3. Forecasts are uncertain. Conformal prediction gives distribution-free marginal coverage
   under exchangeability, with known limitations for time series and multi-step horizons.
   [CITE: split conformal prediction] [CITE: conformal prediction for time series / adaptive conformal]
   [CITE: multi-horizon or joint conformal regions]
4. **Gap:** studies typically report the benefit of a controller given a forecast. They rarely ask
   (a) how much forecast skill is needed before control helps at all, and (b) how to avoid harm when
   that skill is absent. They also rarely pre-register their evaluations.
5. **Contributions:**
   - C1: a scenario-based stochastic MPC that turns horizon-wise conformal intervals into ramp
     scenarios and minimises expected exceedance exactly as a MILP;
   - C2: a causal forecast-skill safety switch computed from the verified calibration ledger;
   - C3: a forecast-quality break-even analysis that maps forecast error to control value;
   - C4: a pre-registered, checksummed evaluation protocol with full disclosure of the development
     history, including rejected hypotheses and negative results.

## 2. Methods

### 2.1 System model

Time is discretised into Δt = 10 min intervals. At interval t the wind farm produces the interval-mean
power P_w,t ≥ 0 (kW). The battery (capacity E_max = 2 MWh, power limits P̄_c = P̄_d = 1 MW, SOC window
40–90%, one-way efficiencies η_c = η_d = 0.95) evolves as

  E_{t+1} = E_t + η_c P_{c,t} Δt − P_{d,t} Δt / η_d,

with binary mode variables preventing simultaneous charging and discharging. The grid exchange is
P_g,t = P_w,t + P_{d,t} − P_{c,t}. The ramp is r_t = P_g,t − P_g,t−1, and the per-interval
exceedance is e_t = max(0, |r_t| − R), with R = 200 kW per 10 min. Battery and turbine parameters
are simulation assumptions, not those of a specific installation.

### 2.2 Synthetic wind generator

Wind speed follows a seeded AR(1) process around a regime mean, with random "fronts" that redraw the
mean uniformly from [5, 13] m/s (probability 0.04 × volatility per interval):
v_t = μ_t + 0.85 (v_{t−1} − μ_t) + 0.6 · volatility · ε_t, with ε_t ~ N(0, 1). Power follows a
generic cubic curve (cut-in 3 m/s, rated 12 m/s, rated power 2 MW). One continuous realisation spans
the calibration warm-up and the scored period, so calibration residuals and scored errors come from
the same dynamics without sharing any data point. Volatility ∈ {0.7, 1.0, 1.5}.

### 2.3 Forecasters

All forecasters issue six interval-mean predictions (10–60 min) at each decision time.
- **Causal (past data only):** persistence; damped trend (damping 0.7); online mean reversion
  (local mean and lag-1 coefficient estimated over the last 4 h of released data); and a per-horizon
  inverse-MSE combination of the three. Every value they read is checked against a declared support
  window of released data and audited by the adapter.
- **Privileged oracles (benchmarks):** the true future interval means plus a Gaussian random-walk
  error across horizons with step σ ∈ {25, 50, 100, 150, 200} kW. These benchmarks place forecast
  skill on a controlled axis; they cannot be achieved by a causal forecaster.

### 2.4 Conformal intervals

For each horizon h, a rolling split-conformal interval uses the absolute residuals of the most
recent 48 released forecasts whose targets precede the decision time. The half-width is the
⌈(n+1)(1−α)⌉-th order statistic, with α = 0.1. Coverage is marginal per horizon; no joint
coverage over the six horizons is claimed. [CITE: split conformal; finite-sample quantile]

### 2.5 Fail-closed forecast–control interface

Each forecast packet carries identities, clocks, feature support and the full calibration ledger.
An adapter accepts a packet only if: every timestamp is causally consistent; every feature was
released before the decision; the conformal result replays exactly from the supplied ledger; and the
identities match a trusted registry. Rejected or missing packets cause zero-dispatch fallback; nothing
is repaired or imputed. A counterfactual test confirms the absence of leakage: changing future
outcomes leaves every earlier decision unchanged.

### 2.6 Scenario-based stochastic MPC (proposed, C1)

At each decision the controller solves, over H = 6 steps,

  min  w_r · (1/(H R)) Σ_k p_k Σ_t s_{k,t}  +  w_q · (Δt/E_use) Σ_t (P_{c,t} + P_{d,t})
       +  w_b · (1/(H E_use)) Σ_t (ℓ_t + u_t)

  s.t. s_{k,t} ≥ ±(R̃_{k,t} + Δn_t) − R,  s_{k,t} ≥ 0,
       ℓ_t ≥ E_low − E_t,  u_t ≥ E_t − E_high,  ℓ_t, u_t ≥ 0, together with the battery dynamics,
       power limits and mode constraints,

where n_t = P_{d,t} − P_{c,t}, Δn_t = n_t − n_{t−1} (n_{−1} = 0), and R̃_{k,t} is the uncontrolled
ramp in scenario k. The scenarios use five Gaussian quantile nodes (equal weights) scaled so that the
conformal interval edge maps to the normal (1−α/2) quantile. The cross-horizon dependence is
comonotone: R̃_{k,t} = W_{k,t} − W_{k,t−1}. Because expected total exceedance is a sum of per-step
expectations, only each step's marginal ramp distribution enters the objective. The weights are
w_r = 1, w_q = 0.05 and w_b = 0.05; the SOC band is 50–80%. A do-no-harm gate applies zero dispatch
unless the optimised plan improves on the zero-dispatch plan's expected cost by at least the
equivalent of 10 kW of exceedance. The problem is solved with HiGHS [CITE: HiGHS]. Every incumbent
is checked against bounds, constraints, integrality, the MIP gap and an objective recomputed
independently from the physical quantities. Only the first move is applied (receding horizon).

### 2.7 Forecast-skill safety switch (C2)

From the verified calibration ledger, the adapter computes
SS = 1 − Σ (ŷ − y)² / Σ (y_origin − y)², pooled over horizons, where y_origin is the released value
at the forecast origin (the persistence prediction). The proposed controller dispatches only if
SS > 0.10 (fixed before evaluation); otherwise the battery stays idle. SS uses released data only.

### 2.8 Comparators and ablations

Stage 3.1 controllers: no battery; deterministic MPC (point forecast); fixed-margin MPC (±200 kW
box); adaptive MPC (conformal box, worst-case per-step penalty); and a one-step ramp-following
heuristic. Ablations: no switch; switch thresholds 0, 0.05 and 0.20; no do-no-harm gate; terminal SOC
target instead of the band; point forecast only; independent-increments dependence
(R̃ spread √(σ_t² − σ_{t−1}²)).

### 2.9 Evaluation protocol and statistics

Design decisions were made on development seeds (1000–1005) and are documented with every round,
including rejected hypotheses (`docs/STAGE33_DEVELOPMENT_NOTES.md`). The confirmatory protocol
(`docs/STAGE33_CONFIRMATORY_PROTOCOL.md`, SHA-256 `bed65ff8…`) was frozen before any held-out seed
was run. Held-out seeds 700000–700049 × 3 volatility levels give n = 150 paired scenarios per
forecast condition. Each episode has 48 scored intervals (8 h). The primary outcome is total ramp
exceedance per episode; the key secondary outcome is battery throughput.

There are 13 primary one-sided Wilcoxon signed-rank tests, Holm-adjusted at a family-wise α = 0.05:
- H1: exceedance below no battery (skilful forecasts);
- H2a: throughput below adaptive MPC;
- H2b: exceedance non-inferior to adaptive MPC, with margin 10% of the mean no-battery exceedance;
  this margin was changed from 5% after a development-seed rehearsal and is disclosed in the
  protocol, with the 5% result reported as a secondary analysis;
- H3: no material harm against no battery (forecasts without skill; margin 5%).

Effect sizes are reported as mean paired differences with seeded percentile-bootstrap 95% CIs.
The runner refuses to start if the protocol hash differs or the tree is modified. Every result file
is checksummed.

## 3. Results (to complete from the confirmatory report)

- 3.1 Primary hypotheses: table from `REPORT.md`.
- 3.2 Break-even: Figure 1 (`fig1_break_even`).
- 3.3 Efficiency: Figure 2 (`fig2_tradeoff`).
- 3.4 No harm without skill: Figure 3 (`fig3_no_harm`).
- 3.5 Ablations: Figure 4 (`fig4_ablation`).
- 3.6 Uncertainty quantification: Figure 5 (`fig5_coverage`).

## 4. Discussion (to complete)

Points to address: the value of the switch versus its cost at intermediate skill; why pooled
level-MSE is a conservative proxy for control value; the implications for forecast development
(ramp skill, not MAE, is what matters); the comparison with deterministic MPC at high error; and the
practical meaning of the margins.

## 5. Limitations

- All evidence is synthetic. Confirmation is across seeds of one generator, not across
  data-generating processes or real wind farms. Real-data validation (for example on SCADA records)
  remains future work and is subject to data-rights review.
- The skilful conditions are privileged oracles. The causal forecasters studied have little skill
  against this generator, whose fronts are unpredictable jumps.
- Oracle errors are random walks, which favours the independent-increments ablation by construction.
- The Gaussian scenario shape and comonotone dependence are assumptions. Conformal guarantees are
  marginal and assume exchangeability, which time series violate.
- The battery, turbine and ramp-limit parameters are illustrative. Battery degradation is
  represented only through throughput.
- The H2b margin was informed by development data (disclosed).

## 6. Reproducibility statement

The code (Python 3.12.5, NumPy 2.5.4, SciPy 1.18.1/HiGHS), the frozen protocol (tag
`stage33-protocol-frozen`), the development notes, a counterfactual leakage test suite
(301 tests) and SHA-256-checksummed results are provided. One command reproduces each stage; the
computation is deterministic, and a re-run from a clean commit reproduced the development results
exactly.
