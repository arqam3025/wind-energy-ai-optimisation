# Publication V2 Stage 3.1 - synthetic risk-aware battery MPC

Status: implemented and tested locally on `research/stage31-risk-aware-mpc`.
Base: published commit `968773d8f2c85dd28ed5bd28ec873a231c2d3db5`.
**SYNTHETIC DATA ONLY. Data admission PENDING_REVIEW.
BLOCKED_CONFIRMATORY_TEST remains active. No commit or push authorized.**

## Motivation and implemented contribution

This stage implements a modular battery plant, timestamped forecast contract,
multi-objective mixed-integer MPC, causal synthetic replay and common comparison
metrics. It prepares an engineering interface for the Stage 2 forecasting and
horizon-specific conformal code. It does not train a model, load SCADA, implement
an authenticated Stage 2 adapter, establish methodological originality or claim
journal readiness. The interval cost is a conservative exposure surrogate, not
CVaR, a joint chance constraint or an empirically calibrated risk probability.

The implementation lives under `publication_v2/stage31/`. Battery and packet
validation are separate from optimization, scenario generation, replay and
output verification. Existing published runtime code is unchanged. The inherited
`publication_v2/publication/release_manifest.json` authenticates the original
40-file parent release, not this expanded uncommitted development tree.

## Assumptions, units and signs

All parameters below are simulation assumptions, not installation specifications.

| Parameter | Value |
| --- | --- |
| Nominal energy capacity | 2,000 kWh (2 MWh) |
| Maximum AC-side charging/discharging power | 1,000 / 1,000 kW |
| Hard SOC range | 0.40 to 0.90; energy 800 to 1,800 kWh |
| Default initial SOC / energy | 0.65 / 1,300 kWh |
| One-way charge and discharge efficiency | 0.95 each |
| Control interval | 10 minutes, delta = 1/6 hour |
| Planning horizon | Six intervals, 60 minutes |
| Ramp reference | R = 200 kW per interval |
| Preferred SOC band | 0.45 to 0.85 (soft operating margins) |
| Optional terminal SOC target | 0.65; penalty disabled by terminal_weight=0 |
| Fixed uncertainty margin | 200 kW, clipped at zero on the wind lower bound |

Charge c >= 0 consumes AC power; discharge d >= 0 supplies AC power.
Signed grid exchange g > 0 is export and g < 0 is import. Grid import is allowed
by default because no export-only condition was supplied. Optional grid bounds
are explicit shared scenario settings, not hidden comparator-specific changes.
There is no curtailment actuator, self-discharge, aging, temperature model,
reserve product or unverified turbine rating cap in Stage 3.1.

For interval k:

```text
E[k+1] = E[k] + eta_c*c[k]*delta - d[k]*delta/eta_d
u[k]   = d[k] - c[k]
g[k]   = wind[k] + u[k]
r[k]   = abs(g[k] - g[k-1])
x[k]   = max(0, r[k] - R)
```

Powers are kW; delta is hours; energy and conversion losses are kWh. The first
ramp uses the same declared, observed previous grid anchor for every comparator.
A ramp violation is x > 1e-6 kW to avoid counting numerical boundary noise.
Raw exceedance totals retain max(0, r-R), in summed kW across discrete intervals;
they are not an energy measure or a continuous-time grid-code certification.

## Physical constraints and optimization class

For k = 0,...,5:

```text
800 <= E[k+1] <= 1800
0 <= c[k] <= charge_max*z[k]
0 <= d[k] <= discharge_max*(1-z[k])
z[k] in {0,1}
```

The actual initial state is validated, and the hard energy bound includes the
sixth/terminal state. Six binary mode variables exclude simultaneous charging and
discharging using physical power limits as tight big-M constants. Epigraph
variables represent absolute values and positive parts. The resulting model is a
**mixed-integer linear program**, not a convex program. Its continuous relaxation
is linear; rounding a relaxed result is not used as a controller.

Every returned plan is checked for complete finite controls, binary mode bounds
and links, power limits, reconstructed energy dynamics, every SOC state, optional
grid bounds and agreement of physical and solver objective values. Numerical
power cleanup is limited to 1e-7 kW; meaningful violations are rejected. Battery
and accounting tests use a declared 1e-6 numerical tolerance, with the solver-state
comparison additionally allowing its documented 1e-5 absolute residual.

## Dimensionless multi-objective formulation

Let H=6 and B=Emax-Emin=1,000 kWh. Nominal grid power uses point forecast p.
Let a_k be nominal ramp-exceedance epigraphs and b_k be per-step worst-box
ramp-exceedance epigraphs. Let s_low/s_high be preferred-band energy shortfalls,
and t be absolute terminal energy deviation.

```text
J = w_r * sum(a_k)/(H*R)
  + w_q * delta*sum(c_k+d_k)/B
  + w_s * sum(s_low_k+s_high_k)/(H*B)
  + w_u * sum(b_k)/(H*R)
  + w_t * abs(E_H-E_target)/B
```

Default weights are respectively **1.0, 0.05, 0.05, 0.5, 0.1**. Each term is
dimensionless. All variants share the same weights, normalization, physical
parameters, forecast points, initial state and scoring cohort. These illustrative
weights were declared in code before the synthetic runs; no scenario-performance
selection or tuning was performed. The throughput term uses the full horizon's
AC energy, while ramp and margin terms use horizon averages; H is fixed at six.
This is a weighted multi-objective trade-off, not lexicographic optimization.

Preferred-band shortfalls are max(0,900-E) and max(0,E-1700), in kWh. The
terminal target is soft; its weight may be zero. Neither soft term relaxes hard
SOC or power bounds. Counteracting SOC/terminal goals can worsen ramp metrics,
which is reported rather than hidden.

## Interval treatment and controller variants

The uncertainty set is a supplied sequence of six marginal wind bounds [L_k,U_k].
Battery commands are shared open-loop within each plan. Bounds are combined
as a Cartesian box; no trajectory probability or cross-horizon dependence model
is supplied. For k>0, b_k >= 0 and:

```text
b_k >= (U_k+u_k) - (L_[k-1]+u_[k-1]) - R
b_k >= (U_[k-1]+u_[k-1]) - (L_k+u_k) - R
```

At k=0 the previous lower/upper grid anchor is the single observed g_previous.
Optional grid constraints enforce L_k+u_k >= grid_min and
U_k+u_k <= grid_max. Both limits are None by default.

The sum of these per-step envelopes is conservative and is **not necessarily the
exact worst total along one realizable trajectory**: the maximizing corners can
differ by step. Automated tests enumerate all 64 box corners, checking the
per-step envelopes, optional grid limits and AC energy accounting. A separate
counterexample distinguishes a 2,600 kW sum of envelopes from an 1,800 kW exact
worst trajectory total.

Implemented comparators:

1. `uncontrolled`: zero battery dispatch; no forecast needed.
2. `deterministic`: L=U=p; point-forecast MPC.
3. `fixed_margin`: L=max(0,p-200), U=p+200; robust-style fixed-box MPC.
4. `adaptive`: supplied horizon-specific L and U; interval-aware MPC.
5. `heuristic`: first-point ramp-following command, clipped to feasible battery
   power/energy and any configured nominal grid limits; it logs an honest
   one-step rule, not invented six-step solver internals.

All three MPC variants have the same objective, including b. Therefore zero-width
fixed/adaptive intervals reduce to the deterministic formulation; this is tested.
The word robust describes an interval-envelope design here, not a demonstrated
closed-loop robustness, chance-compliance or empirical coverage guarantee.

## Forecast contract and receding-horizon chronology

`ForecastBundle` records aware issue, availability and model-availability times;
six point/lower/upper values; six target endpoints; alpha; provenance; and explicit
uncertainty kind. Valid packets have issue <= availability <= decision, model
availability <= issue, correctly ordered finite nonnegative bounds and six exact
future target times. Unknown uncertainty kinds and malformed metadata fail.

Supplied calibration metadata must satisfy target < issue and target < decision,
with residual availability no later than issue and decision. Conformal-labelled
packets require complete calibration metadata. A packet with information between
its earlier claimed issue and decision is rejected, not silently accepted.
Provenance is a validated descriptive string at this stage, not an independently
authenticated source/model certificate.

The synthetic contract forecasts interval-average generation for
[d+k*10,d+(k+1)*10), labelled by the interval's endpoint. Historical interval
observations become available at the endpoint with **assumed zero synthetic
latency**. This convention is explicit; it does not establish real operational
availability. Stage 2 sensor endpoint targets cannot be silently interpreted as
these interval-average energy inputs.

At every decision, the simulation constructs forecasts using only released past
observations, seals the action, then reveals the current interval's synthetic
wind, applies the first battery move, updates actual energy/grid state and
replans. No future realized wind array is accepted by `decide`. Regression tests
replace future outcomes and verify that already issued forecasts/actions do not
change.

A 90% marginal conformal interval would not imply 90% simultaneous six-horizon
coverage. Current synthetic bounds are analytic width fixtures, not calibrated
conformal intervals; alpha=0.1 is metadata, not measured coverage. No Stage 2
forecasting model is trained or invoked by this demonstration.

## Solver, failure modes and dependencies

The implementation uses `scipy.optimize.milp`, which wraps HiGHS; see the
[official SciPy documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html).
The exercised stack is Python 3.12.5, NumPy 2.5.4, SciPy 1.18.1 and SciPy's
bundled HiGHS 1.12.0, on Windows 11 AMD64. No new package was installed.
`stage31/requirements.txt` pins the two numerical packages. Clean installation
and cross-OS/native numerical reproduction were not tested.

Only an optimal solver result with a valid physical plan is accepted. The
configured time limit is 5 s and relative MIP gap is 1e-8. Non-optimal/exceptional
results and invalid returned plans cause zero-dispatch fallback. Missing/invalid
forecasts also cause fallback but do not count as an optimization failure because
no solve occurred. The heuristic's impossible grid bounds are recorded separately
from MILP failures. Invalid initial physical state or malformed operating
configuration raises explicitly rather than pretending that zero power repairs it.

Zero power preserves a valid battery state. It does **not** guarantee ramp or
arbitrary grid bounds. Without optional grid bounds, valid forecasts and a valid
initial battery state always admit zero dispatch, since ramp and terminal goals
are soft. Default-case solver infeasibility would therefore be a defect or solver
failure, not unavoidable grid noncompliance.

## Synthetic experiment design and outputs

Seed **20261110**, 24 intervals per scenario, ten scenarios, five controllers:
**50 comparison rows and 1,200 realized controller intervals per run**. Two runs
used separate non-overwriting directories:

```text
publication_v2/stage31/runs/stage31_seed20261110_n24_a
publication_v2/stage31/runs/stage31_seed20261110_n24_b
```

Scenarios cover stable generation, gradual increase/decrease, sudden ramps,
positive forecast bias, high uncertainty, low/high initial SOC, three invalid/
missing forecast events and deliberately conflicting grid constraints. Seeds,
parameters and complete synthetic traces are recorded. All five controllers
within a scenario receive identical wind, forecast packets, initial SOC, anchor,
limits and scoring denominators. Different scenarios can have different seeds;
their cross-scenario differences are not paired uncertainty ablations.

Forecasts use a declared past-only analytic persistence/trend rule with separately
seeded small noise and width dependent on past variation. They are not oracle
truth-plus-noise predictions. No output is labelled historical SCADA or real-data
validation. No model training, controller selection or metric-dependent tuning
occurred.

Each run has source/configuration identity, environment, scenarios, row-level
traces and actual logged plans, metrics/paired CSVs, validation and time-excluding
fingerprints. Source/environment are captured before execution and checked
unchanged afterward. Unique directory creation and atomic final `COMPLETED.json`
prevent overwrite or false completion; failures have a distinct `FAILED.json`.
Governance is checked but its input hash is not yet a separate manifest field;
Stage 3.2 should bind that explicitly. Current policy bytes remain the published
parent version.

Repeated dispatch, solver-plan data and non-timing metrics matched exactly on
this software/native stack. Comparison fingerprint:

```text
8781051df8db494e99b2c81ebe114425b563e313e8874228d0babc6012379b80
```

Wall-clock timings are excluded from reproducibility equality. The total cases
are not doubled by the second run, and matching output on one stack is not a
cross-machine bitwise-reproduction guarantee.

### Ramp violation counts - all scenarios

| Synthetic scenario | Uncontrolled | Deterministic | Fixed margin | Adaptive | Heuristic |
| --- | ---: | ---: | ---: | ---: | ---: |
| stable | 0 | 0 | 0 | 0 | 0 |
| gradual_increase | 0 | 0 | 0 | 0 | 0 |
| gradual_decrease | 0 | 0 | 0 | 0 | 0 |
| sudden_ramps | 3 | 3 | 3 | 3 | 3 |
| forecast_bias | 3 | 3 | 4 | 5 | 3 |
| high_uncertainty | 3 | 3 | 3 | 3 | 3 |
| low_initial_soc | 0 | 2 | 0 | 0 | 0 |
| high_initial_soc | 0 | 4 | 0 | 0 | 0 |
| invalid_forecasts | 0 | 0 | 0 | 0 | 0 |
| conflicting_constraints | 0 | 0 | 0 | 0 | 0 |

### Complete synthetic comparison table

Exceedance is summed kW; AC throughput is kWh. Failure means actual optimization
failure, while fallback also includes invalid-input and heuristic cases.

| Scenario | Controller | Violations | Exceedance kW | Throughput kWh | Optimization failures | Fallbacks |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| stable | uncontrolled | 0 | 0.000 | 0.000 | 0 | 0 |
| stable | deterministic | 0 | 0.000 | 0.000 | 0 | 0 |
| stable | fixed_margin | 0 | 0.000 | 28.842 | 0 | 0 |
| stable | adaptive | 0 | 0.000 | 13.272 | 0 | 0 |
| stable | heuristic | 0 | 0.000 | 0.000 | 0 | 0 |
| gradual_increase | uncontrolled | 0 | 0.000 | 0.000 | 0 | 0 |
| gradual_increase | deterministic | 0 | 0.000 | 0.000 | 0 | 0 |
| gradual_increase | fixed_margin | 0 | 0.000 | 456.129 | 0 | 0 |
| gradual_increase | adaptive | 0 | 0.000 | 71.999 | 0 | 0 |
| gradual_increase | heuristic | 0 | 0.000 | 0.000 | 0 | 0 |
| gradual_decrease | uncontrolled | 0 | 0.000 | 0.000 | 0 | 0 |
| gradual_decrease | deterministic | 0 | 0.000 | 0.000 | 0 | 0 |
| gradual_decrease | fixed_margin | 0 | 0.000 | 407.152 | 0 | 0 |
| gradual_decrease | adaptive | 0 | 0.000 | 75.680 | 0 | 0 |
| gradual_decrease | heuristic | 0 | 0.000 | 0.000 | 0 | 0 |
| sudden_ramps | uncontrolled | 3 | 3001.151 | 0.000 | 0 | 0 |
| sudden_ramps | deterministic | 3 | 3001.151 | 0.000 | 0 | 0 |
| sudden_ramps | fixed_margin | 3 | 3019.688 | 243.674 | 0 | 0 |
| sudden_ramps | adaptive | 3 | 2934.185 | 96.928 | 0 | 0 |
| sudden_ramps | heuristic | 3 | 3001.151 | 0.000 | 0 | 0 |
| forecast_bias | uncontrolled | 3 | 3011.581 | 0.000 | 0 | 0 |
| forecast_bias | deterministic | 3 | 3233.011 | 526.316 | 0 | 0 |
| forecast_bias | fixed_margin | 4 | 3367.687 | 526.316 | 0 | 0 |
| forecast_bias | adaptive | 5 | 3306.508 | 526.316 | 0 | 0 |
| forecast_bias | heuristic | 3 | 3877.475 | 526.316 | 0 | 0 |
| high_uncertainty | uncontrolled | 3 | 2985.578 | 0.000 | 0 | 0 |
| high_uncertainty | deterministic | 3 | 2985.578 | 0.000 | 0 | 0 |
| high_uncertainty | fixed_margin | 3 | 2966.096 | 177.850 | 0 | 0 |
| high_uncertainty | adaptive | 3 | 3009.733 | 382.293 | 0 | 0 |
| high_uncertainty | heuristic | 3 | 2985.578 | 0.000 | 0 | 0 |
| low_initial_soc | uncontrolled | 0 | 0.000 | 0.000 | 0 | 0 |
| low_initial_soc | deterministic | 2 | 12.356 | 540.319 | 0 | 0 |
| low_initial_soc | fixed_margin | 0 | 0.000 | 199.094 | 0 | 0 |
| low_initial_soc | adaptive | 0 | 0.000 | 516.143 | 0 | 0 |
| low_initial_soc | heuristic | 0 | 0.000 | 0.000 | 0 | 0 |
| high_initial_soc | uncontrolled | 0 | 0.000 | 0.000 | 0 | 0 |
| high_initial_soc | deterministic | 4 | 50.585 | 485.119 | 0 | 0 |
| high_initial_soc | fixed_margin | 0 | 0.000 | 243.516 | 0 | 0 |
| high_initial_soc | adaptive | 0 | 0.000 | 482.154 | 0 | 0 |
| high_initial_soc | heuristic | 0 | 0.000 | 0.000 | 0 | 0 |
| invalid_forecasts | uncontrolled | 0 | 0.000 | 0.000 | 0 | 0 |
| invalid_forecasts | deterministic | 0 | 0.000 | 0.000 | 0 | 3 |
| invalid_forecasts | fixed_margin | 0 | 0.000 | 138.275 | 0 | 3 |
| invalid_forecasts | adaptive | 0 | 0.000 | 83.874 | 0 | 3 |
| invalid_forecasts | heuristic | 0 | 0.000 | 0.000 | 0 | 3 |
| conflicting_constraints | uncontrolled | 0 | 0.000 | 0.000 | 0 | 0 |
| conflicting_constraints | deterministic | 0 | 0.000 | 0.000 | 24 | 24 |
| conflicting_constraints | fixed_margin | 0 | 0.000 | 0.000 | 24 | 24 |
| conflicting_constraints | adaptive | 0 | 0.000 | 0.000 | 24 | 24 |
| conflicting_constraints | heuristic | 0 | 0.000 | 0.000 | 0 | 24 |

Negative findings are retained. In the biased-forecast case, uncontrolled wind
has 3 violations and 3,011.581 kW exceedance, versus adaptive MPC's 5 and
3,306.508 kW. In the stable case, fixed/adaptive incur 28.842/13.272 kWh throughput
while uncontrolled, deterministic and heuristic use zero, with zero violations
for all. In the high-uncertainty case, adaptive exceedance (3,009.733 kW) exceeds
uncontrolled (2,985.578 kW). Conversely, the sudden-ramp adaptive example reduces
exceedance from 3,001.151 to 2,934.185 kW with the same three violations. None of
these hand-constructed scenarios establishes a generally superior controller.

Across these ten illustrative scenarios, totals are descriptive only:

| Controller | Violations | Exceedance kW | AC throughput kWh | Mean decide ms | Max decide ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Uncontrolled | 9 | 8998.310 | 0.000 | 0.004 | 0.012 |
| Deterministic | 15 | 9282.681 | 1551.754 | 5.057 | 31.126 |
| Fixed margin | 10 | 9353.471 | 2420.848 | 8.745 | 38.460 |
| Adaptive | 11 | 9250.425 | 2248.657 | 10.095 | 43.621 |
| Heuristic | 9 | 9864.204 | 526.316 | 0.019 | 0.171 |

Mean timing covers 240 decision calls per comparator, including fallbacks, and
excludes forecast generation/output IO. It is a local measurement, not a real-time
or deployment performance guarantee. No dependence-aware significance claim,
confidence interval or representative-population average is inferred.

The conflicting scenario sets wind=1,800 kW and grid_max=400 kW without curtailment.
Even maximum charging leaves at least 800 kW export: infeasibility is intentional.
Each MPC records 24 failures/fallbacks; the heuristic records 24 fallbacks. All
five cases retain 24 actual grid-limit violations. These periods are not omitted
or relabelled compliant. The invalid-forecast scenario records three fallback
events per active controller and zero optimization failures for those events.

## Physical accounting and constraint validation

AC charge/discharge throughput is sum(c*delta) and sum(d*delta); total is their
sum. It is an operational proxy, not a validated aging or lifetime model.
Conversion loss is:

```text
loss = sum(((1-eta_c)*c + (1/eta_d-1)*d)*delta)
wind_energy + actual_grid_import - actual_grid_export = E_terminal-E_initial + loss
```

Actual export, actual import, signed net exchange and terminal inventory are
reported separately. Terminal inventory is not credited as actual exported
energy. An explicit round-trip test verifies 100 kW charge then 90.25 kW
discharge over equal intervals returns to the same energy, with 1.625 kWh loss.

Across all 1,200 realized intervals in run A:

- SOC, power and simultaneous-charge/discharge violations: **0 / 0 / 0**.
- Global SOC range: **0.40 to 0.90**, including initial and terminal states.
- Maximum actual charge/discharge: **865.894 / 753.233 kW**, below 1,000 kW.
- Maximum per-step power/energy residuals: **0 kW / 0 kWh**.
- Maximum total energy-accounting residual: **1.0232e-12 kWh**.
- **639 accepted six-step MPC plans** independently rechecked; maximum plan
  energy-equation residual **2.2737e-13 kWh**. Every predicted state includes
  the terminal bound. Heuristic plans are separately labelled one-step plans.

These are synthetic software checks under the stated battery model, not
independently measured physical-system validation.

## Tests executed and unavailable tests

| Suite | Run | Passed | Failed/errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Published Stage 1 synthetic suite | 59 | 58 | 0 | 1 |
| Published Stage 2 self-contained synthetic suite | 48 | 48 | 0 | 0 |
| New Stage 3.1 tests | 75 | 75 | 0 | 0 |
| Total | 182 | 181 | 0 | 1 |

Stage 3.1 breakdown: battery 15, forecast 17, controller 19, box-envelope 2,
evaluation/replay/accounting 14 and runner/failure/reproducibility 8. Tests cover
all requested physical, chronology, no-battery, interval, receding-horizon,
infeasibility, fallback, seeded reproduction and common-metric cases.

The skip is the published Windows symlink fixture lacking platform privileges.
All tests present in the sanitized parent were run. Historical private-artifact
integration and forecasting-fit suites were not copied or run: their inputs are
unapproved/missing, and model fitting is excluded from this stage. No test was
silently counted as passing when unavailable. Raw software logs are under
`publication_v2/stage31/runs/validation_7156737b` and remain ignored local outputs.
An internal code/math review identified and fixed heuristic-plan length,
duplicate-cohort and mid-run source-identity issues before the final runs.

## Reproduce in the isolated development checkout

Use Python 3.12 and the exercised package versions. No data download is needed.
Install requirements only into a chosen development environment if necessary:

```text
python -m pip install -r publication_v2/stage31/requirements.txt
python -S -B -m unittest discover -s publication_v2/tests -v
python -S -B -m unittest discover -s publication_v2/stage2/tests -v
python -B -m unittest discover -s publication_v2/stage31/tests -v
python -B -m publication_v2.stage31.runner run --run-id my_synthetic_a --seed 20261110 --steps 24
python -B -m publication_v2.stage31.runner run --run-id my_synthetic_b --seed 20261110 --steps 24
python -B -m publication_v2.stage31.runner verify --run publication_v2/stage31/runs/my_synthetic_a
python -B -m publication_v2.stage31.runner compare --first publication_v2/stage31/runs/my_synthetic_a --second publication_v2/stage31/runs/my_synthetic_b
```

Use new IDs each time; existing outputs are never overwritten. Native solver
availability is required for Stage 3.1 tests. All output paths must remain inside
the isolated checkout, and this CLI has no real-dataset/model-training argument.
No code or results have been committed or pushed in this stage.

## Preservation and remaining limitations

All development writes are confined to the separate Stage 3.1 worktree. The
original research branch/index and its 185 staged paths, Stage 2.7 review branch,
published branch and private backup are unchanged. No original SCADA, model,
controller trace, freeze manifest or protected experiment artifact was opened,
copied or imported for this stage. The worktree began clean with only the 40
sanitized published files; it contains no private data/models/results directories.

The earlier Stage 3.0 verification of 2,170 protected files and 59 frozen references
is historical preservation evidence. To honor the current no-access instruction,
those private artifacts were **not re-opened for fresh hashing** in Stage 3.1.
Current assurance is isolated write targeting plus unchanged original Git
metadata/index/refs, not a newly claimed private-data hash audit.

The plant is a constant-efficiency discrete model, with no degradation, network,
inverter transient, turbine/curtailment or market validation. Default signed
exchange permits imports, and replay timing uses an assumed zero-latency synthetic
clock. Conservative boxes can produce unnecessary throughput and worse realized
ramps. Soft weighted goals do not establish Pareto optimality across methods or
grid compliance. Illustrative weights, margins, seed and scenario mix are not
validated operating policies. Provenance strings alone do not authenticate real
models or data. The partial public snapshot still cannot reproduce the complete
historical experiments.

## Proposed Stage 3.2 - planned, not implemented

1. Implement an authenticated adapter for Stage 2 point forecasts and six separate
   calibration results, binding model/config/source hashes, origin, issuance,
   availability, alpha, target times and declared interval-average support.
2. Keep strict residual target < issue/decision rules; reject missing calibration
   rather than falling back to zero uncertainty. Do not infer joint coverage.
3. Add explicit input/governance policy hashes and a reviewed portable artifact
   verifier without weakening production admission/preservation contracts.
4. Prespecify synthetic uncertainty-width and weight sensitivity experiments on
   exactly paired wind/point forecasts; do not select a preferred real controller
   from these hand-built examples or relabel synthetic outcomes confirmatory.
5. Review grid-import/curtailment assumptions and objective normalization before
   adding operating constraints, and extend failure/infeasibility stress tests.
6. Only after independent rights, lineage, clock, availability and exclusion
   review may retrospective real-data integration be considered. Keep
   PENDING_REVIEW and BLOCKED_CONFIRMATORY_TEST until their separate conditions
   are independently satisfied.
