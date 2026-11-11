# Publication V2 Stage 3.1.1 - MPC scientific correctness and performance audit

Client date: **2026-11-11 (Europe/London)**. Existing isolated branch:
`research/stage31-risk-aware-mpc`; unchanged HEAD/base
`968773d8f2c85dd28ed5bd28ec873a231c2d3db5`.

**Recommendation: READY_TO_COMMIT for the scoped synthetic software changes,
subject to the owner's approval.** This is not a recommendation to deploy,
claim MPC superiority, admit real data or call the study publication-ready.
Two solver/run-verification integrity defects were corrected, and the comparison
cohort guard was strengthened. Default formulation, weights and original results
remain unchanged. The four strict-gap rejections in exploratory diagnostics are
explicitly retained as a limitation, not hidden or tuned away.

**PENDING_REVIEW. BLOCKED_CONFIRMATORY_TEST. No commits or pushes.**
No historical SCADA, saved model or protected historical experiment artifact was
opened, copied or imported in this audit.

## Scope, evidence and preservation

Actual source was inspected: battery, forecast, controller formulation and
postvalidation, causal replay, metrics, comparison guard, runner and tests.
The original two Stage 3.1 synthetic runs contain 60 files each. Before any
correction, their complete inventories and source hashes were checked and the
then-current source was copied byte-for-byte to an ignored audit snapshot.

All new artifacts are separate from the originals:

```text
publication_v2/stage31/runs/audit311_20261111/
  before.json
  source_before/
  archived_original_verification_before.json
  confirmed_defect_reproduction.json
  baseline_equivalence.json
  reproduction_and_formulation_proof.json
  relative_gap_probe.json
  tests/
  diagnostics_a/
  diagnostics_b/
publication_v2/stage31/runs/audit311_corrected_baseline_20261111/
```

Original A/B directories remain unchanged. Each still has its original
fingerprint:

```text
8781051df8db494e99b2c81ebe114425b563e313e8874228d0babc6012379b80
```

The new current verifier intentionally requires schema v2 and rejects legacy v1.
That is a source/schema-version mismatch, not evidence of original-result
corruption. `audit311.verify_archived_originals` separately verifies original
inventories, completion/artifact hashes, original fingerprints and their archived
source snapshot. It does not claim a new independent scientific replication.

## 1. Mathematical findings from code

| Item | Source inspected | Finding |
| --- | --- | --- |
| Energy and efficiencies | `battery.transition`; `_formulate` energy equalities | Correct: E_next = E + eta_c*c*dt - d*dt/eta_d. AC kW times hours produces kWh. |
| Binary exclusion | `controllers._formulate` mode links | Correct: c <= P_c,max*z and d <= P_d,max*(1-z), six binary modes. This is a MILP, not a convex continuous controller. |
| SOC bounds and terminal state | Energy-variable bounds, physical reconstruction | Correct: every predicted E_1,...,E_6 is bounded; initial state validated; terminal target is a soft cost, not a substitute for hard terminal SOC bounds. |
| Grid balance | `battery.grid_export`; replay | Correct: grid = wind + discharge - charge. Negative signed exchange means import; import is allowed by default. |
| Ramp and slack signs | `ramp_metrics`; `_formulate` positive/negative rows | Correct: max(0,abs(grid-current_previous)-200), with nonnegative epigraphs for both signs. |
| Horizon first anchor | t=0 row constants and replay previous-grid update | Correct: the previous realised grid exchange, not a previous wind forecast, anchors each new horizon. |
| Receding horizon | `evaluation.simulate` | Correct: seal forecast-based decision, reveal current synthetic outcome, apply first action only, update energy/realised grid, then replan. |
| Objective coefficients | `_formulate`; physical `_plan` reconstruction | Correct units and coefficient ordering; all five terms dimensionless. Weights are fixed across comparators. |
| Slack interpretation | Objective epigraphs and recomputed physical metrics | Correct for positive weights. Zero-weight epigraphs may be loose but must remain feasible; they cannot be interpreted as optimized physical costs by themselves. |
| Solver acceptance | Previously incomplete; corrected certificate gate | See confirmed defect D1 below. Validating physical controls alone was insufficient to authenticate the entire incumbent/optimality metadata. |
| Fallback | `_fallback`, physical transition and scored actual trace | Zero dispatch preserves an already-valid battery state. It does not repair an invalid initial state or guarantee external grid/ramp limits. Actual consequences remain scored. |

No battery-efficiency, binary-mode, terminal-state, ramp-anchor or slack-sign
error was found. AST comparisons prove that `MPCConfig`, `_formulate`,
`_forecast_arrays`, `_heuristic`, `_plan`, production replay/scoring and original
synthetic generation rules are unchanged by the audit. Corrections concern
validation and evidence handling, not outcome-dependent controller tuning.

### Objective and unintended incentives

With H=6, R=200 kW and usable energy B=1,000 kWh:

```text
J = 1.0  * sum(nominal_exceedance)/(H*R)
  + 0.05 * dt*sum(charge+discharge)/B
  + 0.05 * sum(preferred_SOC_band_shortfall)/(H*B)
  + 0.5  * sum(per_step_worst_box_exceedance)/(H*R)
  + 0.1  * abs(E_H-1300)/B
```

The preferred band is 900 to 1,700 kWh; physical bounds are 800 to 1,800 kWh.
This objective does not minimize the count of threshold violations directly.
It can accept many small exceedances instead of fewer large ones, and it trades
ramp performance against throughput and inventory goals. Those are design
incentives, not mathematical errors.

In deterministic MPC, L=U=p so the uncertainty term equals the nominal exceedance
term: default effective nominal ramp coefficient is 1.5. This intentional
zero-width equivalence must be considered when interpreting risk-weight changes;
such changes also rescale deterministic ramp aversion.

For symmetric fixed +/-200 kW intervals away from zero clipping, later-step
worst-box excess is `200 + abs(delta nominal grid)`. Consequently, the risk cost
penalizes forecast variation even below the nominal 200 kW threshold. Reducing
one such slack by 1 kW saves 0.5/(6*200)=0.000416667 objective units. A 1 kW
one-interval charge adds 0.05*(1/6)/1000=0.000008333 throughput cost: a **50-fold
coefficient ratio**. This is not a full trajectory derivative; adjacent ramp,
SOC, terminal and feasibility effects also matter. It nevertheless explains why
the design may spend battery energy flattening forecast jitter with no realised
threshold benefit.

## 2. Confirmed defects and scoped corrections

### D1 - incomplete solver certificate validation (corrected)

The original physical-plan check could accept a mocked status-0/success result
whose auxiliary slack was negative, reported gap was NaN or 0.5, node count was
negative, or minimization dual bound exceeded its incumbent. These were
reproduced directly against the archived original code; corrected code returns
battery-safe fallback for each. They demonstrate an integrity gap, not that
HiGHS generated those corrupted values in the original runs.

`controllers._validate_solver_certificate` now checks:

- Complete finite incumbent; original variable bounds and every A*x row.
- All declared integrality constraints; finite `c @ x` matching reported fun.
- Correct termination metadata; finite nonnegative reported MIP gap within
  requested relative tolerance plus 1e-9 roundoff allowance.
- Finite consistent minimization dual bound and nonnegative integer node count.
- Then the existing physical reconstruction, all SOC/power/grid bounds and
  agreement with the recomputed weighted physical objective.

Primal row/bound tolerance is 1e-5, integrality tolerance 1e-6; objective checks
use relative/absolute 1e-5. These are numerical consistency checks, not an
independent proof of global mathematical optimality. Actual residuals and
certificate metadata are now logged in accepted plans.

### D2 - incomplete run verification (corrected)

The original verifier accepted completion-consistent manifests with empty
source/artifact maps and contradictory counts. A deliberate adversarial fixture
with scenario_count=999 and comparison_rows=0 was accepted by the archived
verifier. It was not a genuine experiment and was never inserted into results.

New production manifests use **schema v2** and hash the governance policy.
Verification requires nonempty exact source/artifact membership, scope/schema,
identities, counts, complete scenario/controller traces, source/current policy
consistency, independently reconstructed metrics and paired comparisons, CSV/JSON
agreement and recomputed trace/comparison fingerprints. Extra/omitted files and
malformed inventories fail closed. Checksums still establish consistency, not
external authorship or scientific provenance.

### D3 - comparison guard missing explicit time/state checks (hardened)

The original guard checked wind/configuration/forecast hashes and denominators,
but not actual decision/interval timestamps or initial realised energy/grid
anchor. The built-in old runs supplied these consistently; no original unfair
comparison was demonstrated. The guard now rejects mismatched row cohorts,
realised wind values, initial energy or previous-grid anchor. Regression tests
cover those counterexamples.

### Correction versus original results

A new v2 baseline reran the same ten scenarios, seed 20261110, 24 intervals and
all original defaults. All **50 dispatch traces and all non-timing metrics match
exactly**, covering 1,200 controller intervals. Original files were not replaced.
The corrected fingerprint differs because accepted plans now log extended
certificates, not because a better controller was selected:

```text
dc345d782f92382f9228a1313f45026ca22470307fccb36947db6676f413e246
```

## 3. Risk and forecast correctness

- **Deterministic:** point path only; zero-width risk equals nominal ramp cost.
- **Fixed margin:** shared battery trajectory against clipped p +/-200 boxes.
- **Adaptive:** shared trajectory against supplied horizon-specific [L,U].

For k>0, the risk epigraph bounds both
`U_k+u_k-(L_(k-1)+u_(k-1))-R` and the opposite cross corner. At k=0 the previous
box collapses to observed grid exchange. These are correct per-step extrema for
the Cartesian box. Their sum is a conservative envelope, not necessarily the
maximum total on one consistent trajectory; the 64-corner tests and a separate
counterexample establish that distinction. This is interval-based optimization,
not a stochastic scenario-probability model, CVaR or joint chance constraint.
Optional grid bounds apply across the supplied box; ramp exceedance remains soft.

Bounds genuinely affect controls and horizon decisions. Zero-width variants,
asymmetric-bound perturbations, dimensional scaling and risk sensitivity are
covered by tests. Floor clipping can make bounds asymmetric and change storage
incentives. Larger widths do not imply a universal monotonic dispatch rule.

Production synthetic forecasting uses released past observations only. Whole
packets enforce aware issue/availability/model times, six aligned targets,
finite ordered bounds, calibration target timestamps strictly before issue/decision,
and residual availability no later than issue.
No future-information leakage was found in the current synthetic replay.
The assumed zero-latency clock and interval-average endpoint convention are
explicit simulation assumptions, not historical deployability evidence.

Current synthetic intervals are analytic fixtures with alpha=0.1 metadata;
**no measured 90% conformal coverage, six-step joint coverage or guaranteed grid
compliance is established**. Provenance strings do not authenticate actual models
or feature origins. A future Stage 2 adapter must bind model/config hashes,
origin/support and availability. Finite NumPy float32 packet scalars also require
explicit conversion to supported Python numeric values or a separately tested
validator extension; the current Python-float fixtures are unaffected.

## 4. Preserved original scenario-level results

Each cell below is **violations / total exceedance in summed kW**. These are the
original Stage 3.1 results, also exactly reproduced by the corrected default run.

| Scenario | Uncontrolled | Deterministic | Fixed margin | Adaptive | Heuristic |
| --- | ---: | ---: | ---: | ---: | ---: |
| stable | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 |
| gradual_increase | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 |
| gradual_decrease | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 |
| sudden_ramps | 3 / 3001.151 | 3 / 3001.151 | 3 / 3019.688 | 3 / 2934.185 | 3 / 3001.151 |
| forecast_bias | 3 / 3011.581 | 3 / 3233.011 | 4 / 3367.687 | 5 / 3306.508 | 3 / 3877.475 |
| high_uncertainty | 3 / 2985.578 | 3 / 2985.578 | 3 / 2966.096 | 3 / 3009.733 | 3 / 2985.578 |
| low_initial_soc | 0 / 0.000 | 2 / 12.356 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 |
| high_initial_soc | 0 / 0.000 | 4 / 50.585 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 |
| invalid_forecasts | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 |
| conflicting_constraints | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 |

Aggregate original totals, descriptive only:

| Controller | Violations | Exceedance kW | AC throughput kWh |
| --- | ---: | ---: | ---: |
| Uncontrolled | 9 | 8998.310 | 0.000 |
| Deterministic | 15 | 9282.681 | 1551.754 |
| Fixed margin | 10 | 9353.471 | 2420.848 |
| Adaptive | 11 | 9250.425 | 2248.657 |
| Heuristic | 9 | 9864.204 | 526.316 |

No aggregate or scenario result was adjusted to make MPC superior.

## 5. Explanation of negative findings from original traces

### Predicted versus realised ramps and forecast errors

For the first move of a horizon, both predictions use the same actual previous
anchor, so the exact signed identity is:

```text
(actual_grid - previous_grid) - (predicted_grid - previous_grid)
    = actual_wind - first_point_forecast
```

It holds within approximately 2.27e-13 kW in the saved plans. A planned ramp below
or at 200 kW therefore does not guarantee a realised ramp below that threshold.

At the three sudden jumps, point errors are +1155.469, -1361.634 and +1102.585 kW.
Adaptive first-step planned absolute ramps are only 33.041, 38.540 and 13.923 kW,
while realised ramps become 1122.428, 1323.094 and 1088.662 kW. Narrow synthetic
intervals cannot cover those unanticipated jumps just by being called robust.

### SOC restoration, saturation and terminal effects

All six additional deterministic violations occur in low/high-initial-SOC
scenarios. Each of these first-step nominal ramps was at exactly 200 kW; forecast
errors pushed actual ramps to 202.122, 210.233, 236.924, 208.749, 201.877 and
203.035 kW. Their positive exceedances total 12.356 and 50.585 kW in the two
scenarios. Soft terminal restoration is buying battery inventory while creating
small real ramp violations.

All 48 low/high-SOC deterministic plans target 1,300 kWh at their six-step ends.
That is a moving planned terminal, not a hard actual experiment-end target:
high-SOC actual final energy is 1,289.348 kWh. Fixed H=6 is preserved; the audit
does not claim a tested optimum horizon length. Horizon-length sensitivity would
require a separately reviewed configurable-horizon implementation.

In the bias scenario, all MPC variants charge 526.316 kWh and reach 1,800 kWh.
There are 16 deterministic and 18 fixed/adaptive post-step upper-bound hits.
Every first-step outcome is outside the used fixed/adaptive interval in this
deliberately biased case. Saturation and wrong-direction/inventory-restoring
commands limit later adjustment. Fixed adds one violation; adaptive adds two.

### Exact exceedance decomposition versus uncontrolled

| Comparator | Scenario contributions, kW | Net excess change, kW |
| --- | --- | ---: |
| Deterministic | Bias +221.430; high SOC +50.585; low SOC +12.356 | +284.371 |
| Fixed margin | Bias +356.105; sudden +18.537; high uncertainty -19.482 | +355.161 |
| Adaptive | Bias +294.926; high uncertainty +24.155; sudden -66.966 | +252.115 |

The risk penalty can consume battery throughput on forecasts whose variations
are harmless to the realised threshold metric. Original stable-wind throughput
is 28.842 kWh fixed and 13.272 kWh adaptive, versus zero deterministic/uncontrolled.
Original high-uncertainty adaptive throughput is 382.293 kWh versus fixed
177.850 kWh, with different terminal inventory. Its clipped lower-bound geometry
changes dispatch beginning at step 13. This does not show a universal benefit of
higher uncertainty or lower throughput.

Original cross-scenario contrasts alone are not clean sensitivities: different
scenario seeds alter wind and forecasting noise. The paired experiments below
hold those inputs fixed when changing one declared factor.

### Fallback and solver explanation

Each original MPC has 27 fallbacks: 24 deliberately conflicting grid constraints
and three invalid/missing forecasts. The total ramp exceedance on all those
fallback intervals is **zero**. Fallback does not explain the negative aggregate
ramp finding. The conflicting case nevertheless has 24 actual grid-limit
violations for every comparator; those are retained, not claimed compliant.

All 639 original successful plans record gaps no larger than about 2.40e-15.
The corrected default run accepts the same controls and metrics. No evidence
shows that the earlier solver-certificate validation gap caused those negative
performance results.

## 6. Controlled exploratory synthetic diagnostics

These diagnostics were designed after inspecting the original synthetic results.
The full grid was recorded before its first solve, but this is **exploratory
outcome-informed investigation**, not untouched/confirmatory evaluation.
No configuration was selected as a new production default.

Seed **20261111**, H=6, **16 intervals**, two announced forcing profiles:
stable 1,000 kW and repeating four-interval levels 600/1750/400/1500 kW.
The schedule continues analytically beyond the scored window, avoiding false
end-of-window forecast padding. All five controllers share exactly the same
forcing and forecast packet within a case.

Thirty configurations produce **150 comparison rows and 2,400 controller
intervals per diagnostic run**:

- Eight forecast/width cases: 2 profiles x perfect/imperfect x half-width 50/400.
- Fourteen weight cases: 2 profiles x the seven settings below; imperfect
  forecasts, width 200 and initial SOC 0.65.
- Eight extra SOC/terminal cases: 2 profiles x SOC 0.40/0.90 x default/terminal-off.

Perfect mode is an **ideal-information preannounced deterministic schedule**,
known by construction before simulation, not a forecaster reading future
historical outcomes. Imperfect mode uses only released past wind and the fixed
analytic rule. The production replay/forecaster is not replaced by an oracle.
There is no calibration or asserted probability attached to the width changes.

Weight order is nominal ramp, throughput, SOC margin, risk envelope, terminal:

| Setting | Weight vector |
| --- | --- |
| default | (1, .05, .05, .5, .1) |
| ramp_only | (1, 0, 0, 0, 0) |
| risk_off | (1, .05, .05, 0, .1) |
| risk_high | (1, .05, .05, 2, .1) |
| throughput_high | (1, .5, .05, .5, .1) |
| terminal_off | (1, .05, .05, .5, 0) |
| soc_margin_off | (1, .05, 0, .5, .1) |

Except ramp_only, weight cases change one coefficient. Ramp-only can have
nonunique control optima; one solver's returned throughput is not a theorem
about all minimizers. Uniform weight scaling and physical-unit scaling have
separate regression tests.

All configurations and five-controller outputs are disclosed in
`diagnostics_a/all_tested_configurations.json` and
`diagnostics_a/diagnostic_summary.csv`, with complete traces/plans. The table
below includes all 30 cases for the three MPC variants. Cells are
**violations / summed exceedance kW / AC throughput kWh**. Uncontrolled/heuristic
are included in the complete 150-row CSV/JSON, not silently discarded.

| Diagnostic case | Deterministic | Fixed margin | Adaptive |
| --- | ---: | ---: | ---: |
| forecast_stable_announced_perfect_w50 | 0 / 0.000 / 0.000 | 0 / 0.000 / 0.000 | 0 / 0.000 / 0.000 |
| forecast_stable_announced_perfect_w400 | 0 / 0.000 / 0.000 | 0 / 0.000 / 0.000 | 0 / 0.000 / 0.000 |
| forecast_stable_imperfect_w50 | 0 / 0.000 / 0.000 | 0 / 0.000 / 44.750 | 0 / 0.000 / 0.000 |
| forecast_stable_imperfect_w400 | 0 / 0.000 / 0.000 | 0 / 0.000 / 44.750 | 0 / 0.000 / 44.750 |
| forecast_rapid_announced_perfect_w50 | 0 / 0.000 / 889.077 | 0 / 0.000 / 1443.103 | 0 / 0.000 / 1224.540 |
| forecast_rapid_announced_perfect_w400 | 0 / 0.000 / 889.077 | 0 / 0.000 / 1443.103 | 0 / 0.000 / 1443.103 |
| forecast_rapid_imperfect_w50 | 3 / 3000.000 / 0.000 | 3 / 2987.076 / 161.417 | 3 / 3000.000 / 0.962 |
| forecast_rapid_imperfect_w400 | 3 / 3000.000 / 0.000 | 3 / 2987.076 / 161.417 | 3 / 2987.076 / 219.903 |
| weight_stable_default | 0 / 0.000 / 0.000 | 0 / 0.000 / 44.750 | 0 / 0.000 / 44.750 |
| weight_stable_ramp_only | 0 / 0.000 / 0.000 | 0 / 0.000 / 0.000 | 0 / 0.000 / 0.000 |
| weight_stable_risk_off | 0 / 0.000 / 0.000 | 0 / 0.000 / 0.000 | 0 / 0.000 / 0.000 |
| weight_stable_risk_high | 0 / 0.000 / 0.000 | 0 / 0.000 / 44.750 | 0 / 0.000 / 44.750 |
| weight_stable_throughput_high | 0 / 0.000 / 0.000 | 0 / 0.000 / 8.630 | 0 / 0.000 / 8.630 |
| weight_stable_terminal_off | 0 / 0.000 / 0.000 | 0 / 0.000 / 44.750 | 0 / 0.000 / 44.750 |
| weight_stable_soc_margin_off | 0 / 0.000 / 0.000 | 0 / 0.000 / 44.750 | 0 / 0.000 / 44.750 |
| weight_rapid_default | 3 / 3000.000 / 0.000 | 3 / 2987.076 / 161.417 | 3 / 2987.076 / 161.417 |
| weight_rapid_ramp_only | 3 / 3000.000 / 0.000 | 3 / 3000.000 / 0.000 | 3 / 3000.000 / 0.000 |
| weight_rapid_risk_off | 3 / 3000.000 / 0.000 | 3 / 3000.000 / 0.000 | 3 / 3000.000 / 0.000 |
| weight_rapid_risk_high | 3 / 3000.000 / 0.000 | 3 / 2987.076 / 161.417 | 3 / 2987.076 / 161.417 |
| weight_rapid_throughput_high | 3 / 3000.000 / 0.000 | 3 / 2993.178 / 8.482 | 3 / 2993.178 / 8.482 |
| weight_rapid_terminal_off | 3 / 3000.000 / 0.000 | 3 / 2987.076 / 161.417 | 3 / 2987.076 / 161.417 |
| weight_rapid_soc_margin_off | 3 / 3000.000 / 0.000 | 3 / 2987.076 / 161.417 | 3 / 2987.076 / 161.417 |
| soc_stable_40_default | 3 / 17.185 / 526.316 | 0 / 0.000 / 46.326 | 0 / 0.000 / 46.326 |
| soc_stable_40_terminal_off | 0 / 0.000 / 0.000 | 0 / 0.000 / 46.326 | 0 / 0.000 / 46.326 |
| soc_stable_90_default | 2 / 3.405 / 475.164 | 0 / 0.000 / 16.820* | 0 / 0.000 / 16.820* |
| soc_stable_90_terminal_off | 0 / 0.000 / 95.000 | 0 / 0.000 / 16.071 | 0 / 0.000 / 16.071 |
| soc_rapid_40_default | 8 / 2964.378 / 602.417 | 3 / 2987.076 / 180.729 | 3 / 2987.076 / 180.729 |
| soc_rapid_40_terminal_off | 3 / 3000.000 / 0.000 | 3 / 2987.076 / 180.729 | 3 / 2987.076 / 180.729 |
| soc_rapid_90_default | 3 / 2797.268 / 491.655 | 3 / 2989.993 / 266.596* | 3 / 2989.993 / 266.596* |
| soc_rapid_90_terminal_off | 3 / 3000.000 / 95.000 | 3 / 2989.431 / 265.660 | 3 / 2989.431 / 265.660 |

`*` indicates one **application relative-gap certificate rejection**, discussed
below. All other diagnostic cells have zero optimization failures. No diagnostic
has a battery SOC, power or simultaneous-operation violation; maximum total
energy-accounting residual is approximately 7.35e-13 kWh.

### What the paired diagnostics establish

- Stable perfect forecasts produce zero throughput for all MPCs at either width.
  With imperfect stable forecasts, adaptive width 50 uses zero, while width 400
  uses 44.750 kWh; deterministic remains zero. Fixed's unchanged +/-200 bounds
  give 44.750 kWh at either supplied adaptive width. Widths genuinely influence
  the adaptive design, but width alone does not force cycles with perfect flat
  forecasts.
- With a perfectly announced rapid schedule, all MPCs achieve zero realised
  ramp exceedance. With imperfect forecasts the same trace retains three
  violations: deterministic 3000.000 kW, fixed 2987.076 kW, adaptive 3000.000/2987.076
  at widths 50/400. The perfect case is an ideal-information benchmark, not a
  measured real-data forecasting improvement.
- In stable imperfect cases, setting risk weight to zero removes the fixed/adaptive
  44.750 kWh dispatch while all retain zero ramp exceedance. Increasing risk from
  .5 to 2 does not improve this fixture's realised metric. This does not validate
  risk-off as a universal operating policy.
- Increasing throughput weight from .05 to .5 reduces stable fixed/adaptive
  throughput from 44.750 to 8.630 kWh. In the rapid fixture it reduces throughput
  from 161.417 to 8.482 kWh but increases exceedance from 2987.076 to 2993.178 kW.
  Improving one objective worsens another.
- At SOC 0.40, stable deterministic default creates three violations/17.185 kW
  while restoring 800 to 1300 kWh. Terminal-off uses zero battery and has no
  violations, retaining 800 kWh. At SOC 0.90, deterministic terminal-off uses
  95 kWh to reach the preferred upper-band energy 1700 kWh, with zero violations.
- Rapid, SOC 0.40 deterministic default has **eight violations but only 2964.378 kW
  exceedance**, versus uncontrolled's three/3000 kW. Terminal-off returns to
  three/3000 kW with zero throughput. Minimizing severity/inventory deviation does
  not minimize the number of violations.

No best weights, preferred controller or new efficacy conclusion was selected.

### Numerical stopping-policy finding retained as a limitation

Four high-SOC fixed/adaptive cases (stable/rapid, default terminal weight) reject
one native status-0 result each. The reproduced objective is 0.47240009546035644,
dual bound 0.4723993397881706: absolute gap about 7.56e-7, relative gap
1.5996444e-6. The bundled solver's absolute-gap default is 1e-6, so native optimal
termination is compatible with that criterion. The application separately requires
relative gap <=1e-8+1e-9 and therefore rejects the incumbent.

These are **not infeasible MILPs, false HiGHS optimality claims or unsafe battery
commands**. They are stricter application certificate rejections, and their zero
fallbacks and realised consequences remain in the table. Native absolute and
relative criteria are documented in the
[official HiGHS options](https://ergo-code.github.io/HiGHS/dev/options/definitions/).
No tolerance was loosened or solver option changed after observing these cases.
Any future harmonization of stopping and acceptance policy must be prespecified,
versioned and followed by complete reruns. Affected cases partly diagnose that
numerical policy, not only the intended SOC/risk factor.

### Repeatability and output scope

`diagnostics_a` and `diagnostics_b` reproduce all dispatch/plan and non-timing
metrics exactly on the exercised stack. The repeat does not double the case
count or create independent statistical replication. Fingerprint:

```text
70c52e8e05dfd2812406535d2aa7ee174d224190153562a5b5e41ea562ca7bce
```

Wall-clock timings are excluded from equality. No clean-machine/native-library
replication, statistical significance, joint conformal coverage or general grid
compliance is inferred.

## 7. Updated tests and verification

| Suite | Run | Passed | Failed/errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Available published Stage 1 synthetic tests | 59 | 58 | 0 | 1 |
| Available published Stage 2 synthetic tests | 48 | 48 | 0 | 0 |
| Stage 3.1 plus scientific-audit tests | 135 | 135 | 0 | 0 |
| Total | 242 | 241 | 0 | 1 |

The 60 additions comprise 23 certificate, 17 strict-run-verifier, 12 objective/
cohort/scaling and eight diagnostic-design tests. They cover raw ramp epigraphs,
original constraint rows, realised anchor, sixth-step SOC, loose-but-feasible
zero-weight slacks, integrality/gaps/duals/statuses, infeasibility, corrupted plan,
forecast perturbations, paired timestamps/states, fallback realised ramps,
objective/physical scaling, risk sensitivity, inventories and reproducibility.

The skip is the existing Windows symlink privilege fixture. Historical
private-artifact integration and model-fitting tests remain unavailable/excluded;
none were counted as passed. No model training or real-data experiment occurred.
Original tests and original outputs were not rewritten. Separate adversarial
probes reproduce the old defects against archived code and show corrected
fallback/rejection; these are software fixtures, not fabricated experiment data.

## 8. Exact audit changes and reproduction

Modified existing Stage 3.1 files:

- `publication_v2/stage31/controllers.py`: complete certificate acceptance gate.
- `publication_v2/stage31/evaluation.py`: exact cohort/anchor comparison guard.
- `publication_v2/stage31/runner.py`: v2 evidence, governance hash and strict
  manifest/trace verification.

Added:

- `publication_v2/stage31/audit311.py`: separate exploratory/archival CLI.
- `tests/test_scientific_certificate.py`, `tests/test_scientific_runner.py`,
  `tests/test_scientific_objective.py`, `tests/test_audit311.py` under Stage 3.1.
- This report. All outputs stay under ignored `stage31/runs/`.

The original README, Stage 3.1 design/results document, physical/forecast code,
requirements, production defaults and original test files are unchanged by this
audit. Source/hash and unchanged-formulation proofs are saved in the audit
folder. The inherited publication manifest still authenticates only its base.

From this isolated checkout, using the exercised Python/native environment:

```text
python -S -B -m unittest discover -s publication_v2/tests -v
python -S -B -m unittest discover -s publication_v2/stage2/tests -v
python -B -m unittest discover -s publication_v2/stage31/tests -v
python -B -m publication_v2.stage31.runner run --run-id my_audit_baseline --seed 20261110 --steps 24
python -B -m publication_v2.stage31.runner verify --run publication_v2/stage31/runs/my_audit_baseline
python -B -m publication_v2.stage31.audit311 run --output publication_v2/stage31/runs/my_diagnostic_a --seed 20261111 --steps 16
python -B -m publication_v2.stage31.audit311 run --output publication_v2/stage31/runs/my_diagnostic_b --seed 20261111 --steps 16
python -B -m publication_v2.stage31.audit311 compare --first publication_v2/stage31/runs/my_diagnostic_a --second publication_v2/stage31/runs/my_diagnostic_b
```

Use new output names; existing directories/files are never overwritten.
No dependency package was installed. The exercised stack remains Python 3.12.5,
NumPy 2.5.4, SciPy 1.18.1, bundled HiGHS 1.12.0 on Windows 11 AMD64.

## 9. Remaining limitations and preservation

The battery is a constant-efficiency, interval-mean synthetic model, with no
validated aging, inverter transients, curtailment, market cost or network model.
Throughput is an operating proxy, not lifetime benefit. Default import permission
and any optional export bounds must remain explicit in later comparisons.

Horizon length is fixed at six. Terminal and risk preferences can improve one
metric while worsening another. Interval shapes are not a probabilistic
trajectory model; conservative boxes may encourage needless cycling. Solving a
MILP optimally within numerical tolerances does not make the forecasts accurate
or the weighted objective a good operational policy. Strict relative acceptance
can reject native absolute-gap termination. This requires a separate numerical
policy review, not silent adjustment.

Before Stage 3.2 real-data integration, bind model/config hashes and feature
origins, establish endpoint versus interval-average semantics, handle scalar dtype
conversion explicitly and preserve strict calibration availability. Independent
rights, lineage, clock, exclusion and non-exposure review remain unresolved.
**PENDING_REVIEW and BLOCKED_CONFIRMATORY_TEST remain active.**

All project writes occurred in the existing isolated worktree. No new branch was
created. Original research/review/publication branch identities and the shared
original index's SHA256 remain unchanged; its 185 staged paths are untouched.
The known index SHA256 is:

```text
131c0b2e149ec81feb7cadcdeeb5115bd25b73b71abacc950a15a5424a711809
```

No private SCADA or protected historical artifact was read for a fresh hash audit;
the earlier 2,170-file/59-reference verification remains historical evidence.
This stage's assurance is isolated write targeting, unchanged original Git
metadata, preserved old synthetic inventories and no private-data access. The
private backup was not modified. No commits or pushes were made.

**READY_TO_COMMIT applies only to the reviewed synthetic software scope with
these documented limitations. Await approval before staging, committing or
pushing. Negative results are preserved and do not need to be improved to make
the code scientifically honest.**
