# Stage 3.3 confirmatory results (held-out seeds)

**Study role:** SYNTHETIC_CONFIRMATORY_HELD_OUT_SEEDS. The evidence is synthetic: it confirms the
findings across unseen seeds of one simulator, not on real wind farms (see Limitations).

| Item | Value |
|---|---|
| Protocol | `docs/STAGE33_CONFIRMATORY_PROTOCOL.md`, SHA-256 `bed65ff8d1c82b282068237071338599d33e80bb6d8e02addb4a832177c72cec` |
| Frozen code | commit `c59a2c1`, tag `stage33-protocol-frozen` (clean tree, verified by the runner) |
| Seeds | 700000–700049 (never used in development), × volatility {0.7, 1.0, 1.5} = 150 paired scenarios per condition |
| Design | 9 forecast conditions × 14 controllers × 150 scenarios = 18,900 episodes of 48 ten-minute steps |
| Environment | Python 3.12.5, NumPy 2.5.4, SciPy 1.18.1 (HiGHS MILP) |
| Run | started 2026-11-14 18:08, completed 2026-11-16 22:55, exit 0 |
| Integrity | every condition file SHA-256-checked by the loader (`COMPLETED.json`) |
| Deviations | D1 restart and resume; D2 standby pauses (timing only). See below |
| Artefacts | `publication_v2/stage33/results/confirmatory_v1/` (report, tests, secondary analyses, run records); figures in `docs/figures_stage33_confirmatory/` |

P denotes the proposed controller: stochastic MPC with the forecast-skill safety switch (threshold
0.10), as prespecified. U is the mean uncontrolled exceedance per scenario, 1,484 kW.

## 1. Primary hypotheses: all 13 supported

The tests are one-sided paired Wilcoxon tests with Holm correction across all 13 tests,
α = 0.05, n = 150 each. Differences are P minus the comparator, per scenario, with seeded bootstrap
95% CIs. Margins: H2b 10% of U = 148.4 kW; H3 5% of U = 74.2 kW.

| Test | Forecast (MAE30) | Claim | Mean diff [95% CI] | p (Holm) | Result |
|---|---|---|---|---|---|
| H1 | oracle σ25 (35 kW) | P reduces exceedance vs no battery | −1470.5 kW [−1720.7, −1240.8] | 6.5e−24 | supported |
| H1 | oracle σ50 (69 kW) | 〃 | −1450.6 kW [−1699.1, −1221.9] | 7.9e−24 | supported |
| H1 | oracle σ100 (137 kW) | 〃 | −1286.1 kW [−1530.9, −1061.3] | 1.0e−22 | supported |
| H2a | oracle σ25 | P uses less throughput than adaptive MPC | −286.1 kWh [−311.4, −261.3] | 1.5e−25 | supported |
| H2a | oracle σ50 | 〃 | −561.1 kWh [−592.2, −529.2] | 1.9e−25 | supported |
| H2a | oracle σ100 | 〃 | −393.0 kWh [−458.2, −329.8] | 4.4e−20 | supported |
| H2b | oracle σ25 | P exceedance non-inferior to adaptive (margin 148.4) | +8.1 kW [−0.7, +14.4] | 6.5e−26 | supported |
| H2b | oracle σ50 | 〃 | +23.0 kW [+15.1, +32.4] | 2.0e−24 | supported |
| H2b | oracle σ100 | 〃 | +44.3 kW [+19.8, +69.6] | 4.1e−14 | supported |
| H3 | persistence (215 kW) | no material harm vs no battery (margin 74.2) | +0.0 kW [0.0, 0.0] | 1.1e−33 | supported |
| H3 | mean reversion (237 kW) | 〃 | +37.8 kW [+17.6, +59.5] | 1.0e−10 | supported |
| H3 | skill combination (221 kW) | 〃 | +4.2 kW [−0.2, +11.6] | 7.1e−31 | supported |
| H3 | damped trend (297 kW) | 〃 | +0.6 kW [0.0, +1.8] | 1.7e−33 | supported |

Because both H2a and H2b hold in all three skilful conditions, the prespecified efficiency claim
(H2) is supported.

**Secondary: H2b at the originally drafted 5% margin (74.2 kW, unadjusted).** It is supported at
all three levels: p = 2.2e−25 (σ25), 2.0e−21 (σ50) and 3.5e−5 (σ100). So the 10% margin chosen
before freezing does not change the conclusion. At σ100 the upper CI bound, +69.6 kW, comes close
to the 5% margin.

**Honest reading of H2b.** Non-inferiority is not equivalence. Adaptive MPC has a statistically
detectable advantage in exceedance at σ50 and σ100: the CIs exclude zero. In absolute terms it is
small (≤ 3% of U), and P buys it back with 25–50% less battery throughput.

## 2. Descriptive results (mean per scenario, pooled over volatility)

| Forecast | No battery | Deterministic | Adaptive (3.1) | Stochastic (no switch) | **P** | Heuristic |
|---|---|---|---|---|---|---|
| oracle σ25 | 1484 / 0 | 71 / 301 | 5 / 654 | 12 / 368 | **13 / 368** | 113 / 337 |
| oracle σ50 | 1484 / 0 | 137 / 356 | 10 / 1133 | 29 / 574 | **33 / 572** | 200 / 359 |
| oracle σ100 | 1484 / 0 | 315 / 528 | 154 / 1589 | 177 / 1295 | **198 / 1196** | 375 / 441 |
| oracle σ150 | 1484 / 0 | 606 / 770 | 629 / 1824 | 688 / 1917 | **698 / 1311** | 586 / 591 |
| oracle σ200 | 1484 / 0 | 1192 / 1113 | 1372 / 1979 | 1242 / 1843 | **1115 / 707** | 978 / 797 |
| persistence | 1484 / 0 | 1484 / 0 | 1489 / 234 | 1498 / 88 | **1484 / 0** | 1484 / 0 |
| mean reversion | 1484 / 0 | 1541 / 103 | 1678 / 1129 | 1640 / 702 | **1522 / 104** | 1516 / 67 |
| skill combination | 1484 / 0 | 1483 / 0 | 1565 / 760 | 1533 / 240 | **1488 / 4** | 1484 / 0 |
| damped trend | 1484 / 0 | 1738 / 162 | 2033 / 1130 | 2047 / 808 | **1485 / 3** | 1690 / 107 |

Each entry is exceedance (kW) / throughput (kWh). Exceedance is the sum of ramp excess above
200 kW per 10 min over 48 steps.

### 2.1 Break-even forecast quality (Figure 1)

The MPC controllers remove 87–99% of exceedance when MAE30 ≤ 137 kW (deterministic MPC: 79–95%). The benefit
falls steeply after that: P gives −53% at MAE30 ≈ 201 kW and −25% at 263 kW. With causal forecasts
of similar MAE (215–297 kW) but **no ramp skill**, the unswitched MPCs make exceedance worse than no
battery. MAE alone therefore does not predict control value; what matters is whether the forecast
anticipates ramps.

### 2.2 Efficiency (Figure 2)

With skilful forecasts, P sits on the efficient frontier. It matches adaptive MPC's exceedance to
within 8–44 kW at 44% (σ25), 50% (σ50) and 25% (σ100) less throughput. The fixed-margin MPC
reaches similar exceedance but uses 1,555–1,676 kWh per episode, 1.4–4.2 times as much as P.

### 2.3 No harm without skill (Figure 3)

Without the switch, MPC with unskilled forecasts is harmful. With the damped-trend forecaster,
stochastic MPC adds +563 kW [+460, +674] per scenario (+38% of U) and adaptive MPC adds +549 kW.
The switch keeps P idle in 87–100% of decisions under these forecasts, which reduces the harm to
0–38 kW, all within the 5% margin. The residual harm under mean reversion (+37.8 kW) comes from the
13% of decisions in which that forecaster briefly appears skilful.

### 2.4 Cost of the switch with skilful forecasts (Figure 4; secondary)

The switch rarely fires with good forecasts (it gates 0%, 2% and 12% of decisions at σ25/50/100).
Its cost is small but detectable: the unswitched stochastic MPC has 8.8 kW lower exceedance
[CI −15.4, −2.9] (pooled over σ25–100) at +33.9 kWh [+18.3, +51.2] more throughput. At σ200 the switch helps
(1115 vs 1242 kW) because it idles in 63% of decisions. Results are insensitive to the threshold
between 0 and 0.20 under skilful forecasts. Under unskilled forecasts, the threshold matters: the
gated fraction under skill combination is 0.56 at threshold 0 and 1.00 at 0.20.

### 2.5 Other ablations (Figure 4; secondary)

- **Point forecast only** (band and gate, no scenarios): +90.7 kW [+76.4, +105.4] more exceedance than P at 378 kWh
  less throughput. This is the largest effect, which shows that the scenarios are the active
  ingredient.
- **Independent-increments scenarios:** −25.0 kW [−33.9, −16.3] exceedance at +28.3 kWh. This variant does a little
  better on skilful forecasts. It was set aside before the held-out run on development evidence, so
  it is reported as a candidate for future work, not adopted post hoc.
- **No do-no-harm gate:** −11.6 kW [−18.4, −5.6] at +43.6 kWh. Under unskilled forecasts the gate's role is taken
  over by the switch.
- **Terminal SOC target instead of the band:** no clear exceedance change, −3.9 kW [−12.0, +4.0], at +170.3 kWh.
  The band is more efficient.

### 2.6 A simple heuristic wins when forecasts are poor (honest negative)

At σ150 and σ200 the rule-based heuristic has the lowest exceedance of all controllers (586 and
978 kW versus P's 698 and 1115 kW). It also has lower throughput than adaptive MPC. Forecast-driven
optimisation is therefore only worth it above a forecast-quality threshold. In this degraded
regime the MPC ranking is mixed. At σ150, P has the highest exceedance of the MPCs (698 kW versus
606–688 kW) but the lowest throughput. At σ200, P has the lowest exceedance of the MPCs, because
the switch idles it in 63% of decisions.

### 2.7 Volatility (secondary, `SECONDARY.md`)

Absolute exceedance scales with volatility for every controller.
- **σ25 and σ50:** the ranking of controllers is consistent across the three volatility levels.
- **σ100 and above:** the ranking depends on volatility.
  - σ100, volatility 0.7: adaptive MPC (131 kW) is clearly better than P (198 kW).
  - σ150 at volatilities 1.0 and 1.5, and σ200 at volatility 1.5: P is worse than deterministic and
    adaptive MPC (for example 1,611 kW versus 1,342 and 1,382 kW at σ200, volatility 1.5).
  - σ200, volatility 0.7: P is far better (550 kW versus 996–1,320 kW).
- **Unskilled forecasts:** P stays within a few kW of no battery at every volatility level, except
  under mean reversion (+14 to +70 kW).

### 2.8 Conformal uncertainty (Figure 5)

Marginal coverage per horizon averages 0.90–0.91 against the nominal 0.90 in every condition.
Joint coverage of all six horizons is only 0.74–0.78. Marginal validity does not give a valid
trajectory-level guarantee, so a controller that treats the six intervals as a joint set is
under-hedged.

### 2.9 Safety, accounting and computation (secondary)

Across all 18,900 episodes, the safety and accounting checks came out clean:
- **Constraint violations:** zero SOC, power, simultaneous charge/discharge and grid-limit
  violations.
- **Energy balance:** the energy-accounting residual is at most 4e−12 kWh.
- **Adapter rejections:** none.
- **Solver failures:** each one was caught and replaced by the safe fallback. P had 26 such
  failures in 64,800 decisions (0.04%).

Computation time per decision, wall-clock, is reported as the median and p95 because of D2:

| Controller | Median (ms) | p95 (ms) |
|---|---|---|
| Stochastic MPC | 16 | 45 |
| P | 1.0 (idle when gated) | 32 |
| Adaptive MPC | 19 | 49 |

All are far below the 10-minute control interval.

## 3. Deviations (full text in `results/confirmatory_v1/DEVIATIONS.md`)

- **D1:** Windows Update restarted the computer during `oracle150` (2026-11-15, 00:03–00:09). The
  three completed conditions were kept. The run resumed from a clean checkout of the frozen commit,
  and the runner verified the protocol hash and commit. No results were inspected before the
  resume. Impact: none.
- **D2:** operating-system standby suspended the workers several times. Outcomes are unaffected
  because the computation is deterministic. Wall-clock timing is inflated for a few decisions, so
  timing is reported only as the median and p95.
- **Post-run additions (not deviations from the analysis):**
  - `confirmatory_secondary.py` computes the protocol's descriptive items 5 and 7, plus the
    switch-activation and safety tables. It was written after the run and contains no tests.
  - Figure-layout fixes (legend position) were made after the run. They do not change any number.

## 4. What the confirmatory evidence supports

1. With skilful forecasts (MAE30 ≤ ~140 kW in this simulator), skill-gated stochastic MPC removes
   87–99% of ramp exceedance. It is non-inferior to the strongest Stage 3.1 controller while using
   25–50% less battery throughput.
2. The forecast-skill safety switch prevents the large harm that forecast-driven MPC causes when the
   forecasts lack ramp skill, at a small, measurable cost when forecasts are good.
3. The value of a forecast for control depends on ramp skill, not on MAE alone. Below a
   forecast-quality threshold, a simple rule-based controller is preferable.
4. Marginal conformal coverage holds, but joint multi-horizon coverage does not.

It does **not** show performance on real wind farms. Stage 4 (Kelmarsh SCADA, sealed test years
2023–2024) is designed to test that.
