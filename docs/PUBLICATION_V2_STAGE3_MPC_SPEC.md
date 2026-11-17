# Publication v2: Stage 3 MPC integration specification

Prepared 1 November 2026. This is a **future integration specification**, not an MPC implementation, authorized controller redesign or completed control experiment. Stage 2 develops forecasting/uncertainty interfaces; the [Stage 1 chronology protocol](PUBLICATION_V2_PROTOCOL.md), [Stage 1 report](PUBLICATION_V2_STAGE1_REPORT.md), [Stage 2 methods](PUBLICATION_V2_STAGE2_METHODS.md) and [research audit](RESEARCH_AUDIT.md) govern their interpretation. `BLOCKED_CONFIRMATORY_TEST` remains unresolved until affirmative untouched-data evidence is supplied.

## Admission and experiment identity

A development control experiment requires resolved data-use/provenance and operational availability evidence even if its outcomes will remain descriptive. Confirmatory execution additionally requires independently reserved outcomes, access/custody records and a freeze predating outcome access. Renaming the original 49 episodes or purging their boundaries cannot restore non-exposure. A separate authorization must precede Stage 3 implementation or execution.

Before integrating forecasts, freeze the question, dataset/source version, exact model/calibration identities, control code/configuration, common physical parameters, initial/terminal policy, exposure, boundaries, failures and analysis definitions. New Stage 2 adapters do not authorize replacing the frozen historical controllers or retrospectively changing their preferred model. Any new model/controller choice belongs to a separately recorded development decision.

## Decision-input contract

Every proposed controller call must consume a validated immutable decision bundle. Its minimum contents are:

| Component | Required evidence |
| --- | --- |
| Identity | Decision/episode IDs, protocol/config/source/data hashes, declared role and scientific status |
| Clock | Offset-aware decision time, source-supported cadence/grid anchor, measurement-window convention and recorded latency |
| Observed state | Battery DC energy/SOC, previous realised grid export and battery injection, event/receipt/availability timestamps and state units |
| Forecast | Origin, issue time, all six target times, model hashes, fitting window/available-at record, ordered feature identities and prediction units |
| Feature lineage | All contributing source events/receipts, full lag support and computed availability; no post-origin observation |
| Uncertainty | Per-model/per-horizon method and parameters, eligible residual identities, newest admitted target/receipt/computation time, sample count, quantile/radius, floor/fallback diagnostics |
| Physical/configuration | Capacity, power limits, efficiencies, SOC band, interval duration, horizon, ramp definition, objectives/tolerances and execution policy |

Reject unknown or changed identities, inconsistent clocks, future feature/state availability, future/equal-time residual targets, late residual computation, mismatched model/horizon residuals, missing horizons, stale or duplicate records and incompatible units. A forecast origin and an outcome timestamp are different objects. Quantile availability must be established at the current decision, not from an offline file's existence.

An offline data-clock fitting cutoff is not an actual model-commissioning timestamp. Stage 3 must distinguish fitting data eligibility, completed fitting, model deployment/availability and wall-clock inference/optimization time. A retrospectively fitted model must not be described as historically deployed, and a feasible past-label window does not by itself establish that computation finished before a real issue/decision deadline. Filesystem modification time does not supply these records.

The production decision API must receive forecasts, uncertainty and observed state only. A separate scorer owns future actual generation. Intervention tests change every unobserved target while holding admitted information fixed; committed first commands must remain unchanged. A later realised state can change only after command commitment and the declared physical execution step.

## Uncertainty-to-control semantics

An adapter must explicitly name the uncertainty object used by the controller. A two-sided empirical interval is not automatically a joint six-horizon prediction set. A lower-only scenario bound `[L,+infinity)` has infinite width; `nominal-L` is a finite downside offset. Neither object alone supplies a probability guarantee for the scenario fan or a chance-constrained grid-compliance guarantee.

If a lower scenario is constructed from a Stage 2 interval, persist its exact transformation, clipping and horizon alignment. Any floors, smoothing, risk weights or fallbacks are new control parameters unless they reproduce an authenticated frozen definition; they cannot be chosen after reading control-scoring outcomes. Failed or insufficient calibration should fail the requested experiment or invoke a separately predeclared safe policy with an explicit failure flag. It must never become a zero-width bound or silently borrow another horizon/model's residuals.

Rolling/weighted residual updates may consume prior scored outcomes only under the preregistered online rule and strict target/receipt/computation checks. This prequential dependence is disclosed. It does not permit retraining, hyperparameter selection, controller selection or experiment exclusions based on evaluation performance.

## Physics, execution and logs

Start with authenticated frozen physical parameters when performing a source-matched comparison: 2,000 kWh capacity, 1,000 kW charge/discharge power, 40–90% SOC, 95% charging/discharging efficiencies, ten-minute steps, six-step horizon and 200 kW ramp threshold. A changed parameter requires a separately named development variant. Stored energy is kWh; charge/discharge/export are kW; the time factor is 1/6 hour.

Verify DC dynamics `E_next = E + eta_c*P_charge*dt - P_discharge*dt/eta_d`, AC balance, nonnegative wind-only charging/export, curtailment bounds, power limits, hard SOC bounds and charging/discharging exclusivity. Declare solver and physical numerical tolerances with units. Small planned numerical residuals are not exact feasibility; planned versus executed action checks are distinct.

Preserve the frozen first-command information structure when claiming a matched reproduction: common requested first charge/discharge/curtailment/mode across scenarios, later scenario recourse, wind-limited execution after actual first-target revelation, and replanning from realised state. The frozen reserve is soft; the primary-stage allowance is not exact lexicographic optimality or guaranteed realised compliance. New algorithms must document any different information structure and objective rather than borrowing the frozen label.

Record first requests and realised actions separately, all available six-step plans, model/uncertainty inputs, both solve stages/status/objectives, achieved primary cost, numerical residuals, available gaps/nodes, timing and failure handling. Missing solver internals remain unavailable. Do not manufacture diagnostics for historical traces. Use exclusive output paths, atomic authenticated completion and preservation checks; retain interrupted/failing runs.

## Comparisons and analysis

Retain uncontrolled wind, frozen fixed-margin MPC and frozen adaptive one-sided MPC under identical scored observations, physical parameters, initial SOC/export, terminal accounting and first-boundary transition handling. Forecast-family variants must use the same windows and observation cohort. Persistence or nominal control adds information-structure comparisons only when objective/physics/solver conventions are matched. A perfect-forecast case is nondeployable and is not an unconditional upper bound for every metric under finite-horizon mixed objectives.

Report violations, summed exceedance, mean/maximum ramps, introduced/removed violations, charge/discharge energy, throughput, conversion losses, curtailment, SOC constraints, solver failures/time and terminal inventory. Separate measured export from hypothetical terminal-SOC-adjusted export; hypothetical restoration does not simulate its duration or subsequent ramps. Throughput and equivalent-full-cycle proxies do not establish battery lifetime.

Pair outcomes at a predeclared chronological unit, retain difficult intervals and failures, and justify dependence handling for the actual exposure. Do not treat overlapping forecast targets as IID, choose uncertainty blocks by significance or present unperformed calculations as inference. Model rankings, forecast error, empirical interval coverage and control benefit are separate outcomes.

The historical negative comparison is mandatory context:

| Archived retrospective case | Violations | Summed exceedance (kW) |
| --- | ---: | ---: |
| Uncontrolled wind | 1,465 | 317,210.288 |
| Frozen fixed-margin MPC | 1,502 | 326,158.296 |
| Frozen adaptive one-sided MPC | 1,486 | 323,638.526 |

Adaptive's relative advantage over fixed margins does not establish aggregate mitigation against uncontrolled wind. These original scores remain unchanged regardless of later model or control outcomes.

## Acceptance before a Stage 3 result

Implementation acceptance requires exact input-contract tests, future-value interventions, target-boundary/embargo checks, state/balance/exclusivity tests, solver failure tests, authenticated repeatability and independent accounting. Scientific acceptance additionally requires a lawful, eligible dataset and a complete declared cohort. Confirmatory interpretation requires the separate untouched-data gate. No Stage 3 result, readiness or efficacy is claimed by this specification.
