# How good must a wind forecast be? Skill-gated stochastic MPC for wind–battery ramp control with conformal uncertainty

*Manuscript draft. Sections 3–4 report the frozen confirmatory run
(`docs/STAGE33_CONFIRMATORY_RESULTS.md`); every number there is traceable to checksummed result files. `[CITE: …]` marks places that need a
reference: fill these from your own literature search. No reference has been invented.*

## Abstract

Battery energy storage can smooth the short-term ramps of wind generation, but the controller acts
on forecasts that may be wrong, and unnecessary cycling costs throughput and efficiency. We study
when forecast-driven ramp control pays off. We combine (i) split-conformal prediction intervals at
six horizons (10–60 min), (ii) a scenario-based stochastic model predictive controller (MPC) that
minimises the expected ramp-threshold exceedance as a mixed-integer linear program, and (iii) a
forecast-skill safety switch that keeps the battery idle unless verified, released residuals show
skill over persistence. In a pre-registered evaluation on held-out simulator seeds
(n = 150 paired scenarios per condition, 14 controllers, 9 forecast conditions), we find
that all 13 Holm-adjusted primary hypotheses hold. With skilful forecasts, the skill-gated
controller removes 87–99% of ramp-threshold exceedance relative to no battery. It is non-inferior
to a strong adaptive-margin MPC (excess ≤ 3% of the uncontrolled level) while using 25–50% less
battery throughput. With causal forecasts that lack ramp skill, unswitched MPC increases exceedance
by up to 38%; the safety switch keeps the harm within a 5% margin in all four such conditions.
Control value depends on ramp skill rather than MAE, and below a forecast-quality threshold a
simple rule-based controller performs best. Marginal conformal coverage holds (0.90–0.91), but
joint six-horizon coverage does not (0.74–0.78). All code, protocol, development history and checksummed results are released.

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

## 3. Results

The confirmatory run used 50 held-out seeds × 3 volatility levels (n = 150 paired scenarios per
condition), 9 forecast conditions and 14 controllers: 18,900 episodes from the frozen commit. Two
operational deviations occurred, an operating-system restart followed by a resume (D1) and standby
pauses (D2). Neither affects any outcome (Section 6). U denotes the mean uncontrolled exceedance,
1,484 kW per scenario.

### 3.1 Primary hypotheses

All 13 primary tests are supported after Holm correction (Table 1).

**Table 1.** Primary tests, proposed controller P minus comparator. One-sided paired Wilcoxon,
Holm-adjusted, n = 150. 95% CIs are seeded percentile bootstraps.

| Test | Forecast | Mean difference [95% CI] | p (Holm) |
|---|---|---|---|
| H1: exceedance < no battery | oracle σ25 / σ50 / σ100 | −1470.5 [−1720.7, −1240.8] / −1450.6 [−1699.1, −1221.9] / −1286.1 [−1530.9, −1061.3] kW | ≤ 1.0e−22 |
| H2a: throughput < adaptive MPC | σ25 / σ50 / σ100 | −286.1 [−311.4, −261.3] / −561.1 [−592.2, −529.2] / −393.0 [−458.2, −329.8] kWh | ≤ 4.4e−20 |
| H2b: exceedance non-inferior to adaptive (m = 148.4 kW) | σ25 / σ50 / σ100 | +8.1 [−0.7, +14.4] / +23.0 [+15.1, +32.4] / +44.3 [+19.8, +69.6] kW | ≤ 4.1e−14 |
| H3: no material harm vs no battery (m = 74.2 kW) | persistence / mean reversion / skill combination / damped trend | +0.0 / +37.8 [+17.6, +59.5] / +4.2 [−0.2, +11.6] / +0.6 [0.0, +1.8] kW | ≤ 1.0e−10 |

H2b is also supported at the originally drafted 5% margin. This analysis is secondary and
unadjusted: p ≤ 3.5e−5, although at σ100 the upper confidence bound (+69.6 kW) approaches that
margin (74.2 kW). Non-inferiority is not equivalence. Adaptive MPC retains a small but detectable
exceedance advantage at σ50 and σ100, at most 3% of U.

### 3.2 Break-even forecast quality

Figure 1 plots the change in exceedance against forecast error.
- **MAE30 ≤ 137 kW:** the MPC controllers remove 87–99% of exceedance (deterministic MPC: 79–95%).
- **Above that:** the benefit decays quickly. P gives −53% at MAE30 = 201 kW and −25% at 263 kW.
- **Causal forecasters with comparable MAE (215–297 kW) but no ramp skill:** the unswitched MPCs
  increase exceedance (Section 3.4).

Forecast MAE alone is therefore a poor predictor of control value.

### 3.3 Efficiency

Figure 2 plots throughput against exceedance. With skilful forecasts, P matches adaptive MPC's
exceedance to within 8–44 kW while using 44%, 50% and 25% less throughput at σ25, σ50 and σ100. The
fixed-margin MPC achieves similar exceedance with 1.4–4.2 times P's throughput. Deterministic and
heuristic controllers use little throughput but leave 4–9 times more exceedance than P at σ25–σ50.

### 3.4 No harm without forecast skill

Figure 3 compares the controllers under the four unskilled forecasters.
- **Without the switch:** forecast-driven MPC is harmful. Under the damped-trend forecaster,
  stochastic MPC adds +563 kW [+460, +674] per scenario (+38% of U) and adaptive MPC adds +549 kW.
- **With the switch:** P is idle in 87–100% of decisions under these forecasts, and its harm is
  0–38 kW, inside the 5% margin.
- **Remaining harm:** the largest residual (mean reversion, +37.8 kW) arises in the 13% of decisions
  in which that forecaster's released residuals briefly indicate skill.

### 3.5 Ablations

Figure 4 shows each variant minus P, pooled over the three skilful conditions.
- **Scenarios versus point forecast:** removing the scenarios (point forecast with band and gate)
  costs +90.7 kW [+76.4, +105.4] of exceedance. This is the largest effect.
- **Cost of the switch with good forecasts:** without the switch, exceedance is lower by
  8.8 kW [2.9, 15.4] and throughput is higher by 33.9 kWh.
- **Switch threshold:** the results are insensitive to thresholds between 0 and 0.20 under skilful
  forecasts. Under unskilled forecasts the threshold matters: the fraction of decisions gated under
  the skill-combination forecaster rises from 0.56 at threshold 0 to 1.00 at 0.20.
- **Do-no-harm gate:** it costs 11.6 kW and saves 43.6 kWh.
- **SOC band versus terminal target:** a terminal SOC target gives no clear exceedance change
  [−12.0, +4.0] at +170 kWh of throughput.
- **Independent-increments scenarios:** these reduce exceedance by 25.0 kW [16.3, 33.9] at +28 kWh.
  The comonotone structure was fixed as primary on development data, so this variant is reported as
  a promising alternative, not adopted after the fact.

### 3.6 Degraded forecasts and volatility

At σ150 and σ200 the rule-based heuristic achieves the lowest exceedance of all controllers (586
and 978 kW, against 698 and 1,115 kW for P). In this regime the ranking of the MPCs depends on
volatility. P is best at σ200 with low volatility but worse than deterministic and adaptive MPC at
higher volatility. With σ ≤ 50 the ranking is consistent across volatility levels.

### 3.7 Uncertainty quantification and operational checks

**Coverage (Figure 5).** Marginal coverage of the rolling split-conformal intervals is 0.90–0.91 in
every condition (nominal 0.90). Joint coverage of all six horizons is 0.74–0.78.

**Safety and accounting.** Across all 18,900 episodes:
- no SOC, power, simultaneous charge/discharge or grid-limit violations occurred;
- the energy-accounting residual stayed below 4e−12 kWh;
- every solver failure was caught by the safe fallback (P: 26 in 64,800 decisions).

**Computation time.** The median and 95th-percentile solve times per decision are 1.0 and 32 ms for
P and 16 and 45 ms for unswitched stochastic MPC. Both are far below the 10-minute control
interval.

## 4. Discussion

**When does forecast-driven storage control pay?** The confirmatory results support a simple
operational rule. Optimise the battery against forecasts only when there is verified, recent
evidence that the forecast beats persistence, and otherwise do nothing or use a simple rule. Above
the break-even quality, scenario-based stochastic MPC gives almost all of the achievable ramp
reduction at substantially lower cycling than margin-based MPC. Below it, every forecast-driven
optimiser we tested is either marginal or harmful. A heuristic is then the better choice. The
contribution of the switch is to make this rule automatic and auditable: its decision is computed
only from released residuals, so it is causal by construction.

**Cost of the switch.** The switch is a hedge. With good forecasts it costs about 9 kW of exceedance
per scenario (under 1% of U), because the pooled skill estimate occasionally falls below the
threshold early in an episode. Without skill it prevents harm of up to 38% of U. Its value is
asymmetric because the downside of acting on a misleading forecast (amplifying ramps) is much
larger than the upside of acting on a marginally skilful one.

**Why MAE is not enough.** Forecasters with similar MAE produced opposite control outcomes. The
oracle forecasts carry information about future ramps, whereas the causal forecasters in this
simulator do not: their errors are largest exactly when ramps occur. The pooled level-MSE skill
score used by the switch is therefore conservative. It detects the absence of skill reliably, but
it does not measure ramp skill directly. A ramp-specific skill score is a natural refinement
[CITE: ramp forecasting evaluation].

**Uncertainty quantification.** Marginally valid intervals are not enough for multi-step control.
The 12–16-point gap between marginal and joint coverage means that a controller treating the six
intervals as a joint uncertainty set is systematically under-hedged. The scenario controller
mitigates this partly by optimising expected exceedance rather than worst-case bounds. Joint or
trajectory-level conformal methods would be a principled next step [CITE: multi-horizon /
conformal time-series methods].

**Practical meaning of the margins.** The 10% (H2b) and 5% (H3) margins correspond to about 148
and 74 kW of summed ramp excess per 8-hour episode. That is small relative to the 1,484 kW
uncontrolled level, and well below a single large ramp event. H2b also holds at 5%, so the
efficiency conclusion does not rest on the margin change disclosed in the protocol.

**Relation to prior work.** Battery-based ramp-rate control and MPC for wind–storage systems are
established [CITE: wind–BESS ramp control; MPC for storage]. Conformal prediction for energy
forecasting is growing [CITE]. To our knowledge, the combination evaluated here has not been
tested under a pre-registered, held-out protocol: a causal forecast-skill switch in front of
stochastic MPC, assessed with explicit no-harm hypotheses. This claim must be checked against
the literature before submission [CITE: closest related work].

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

**Deviations from the protocol.** The confirmatory run was interrupted once by an operating-system
restart (D1). It was resumed with the identical command from a clean checkout of the frozen commit,
and the runner verified the protocol hash and the commit. Completed conditions were kept and no
results were inspected before the resume. Operating-system standby also suspended the run several
times (D2). Outcomes are unaffected because the computation is deterministic, but the wall-clock
timing of a few decisions is inflated, so computation time is reported only as the median and 95th
percentile. The full deviation log is released with the results
(`publication_v2/stage33/results/confirmatory_v1/DEVIATIONS.md`).
