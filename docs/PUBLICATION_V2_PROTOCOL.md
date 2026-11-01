# Publication v2: Stage 1 chronology and evaluation protocol

Protocol version: `publication_v2`, Stage 1. Prepared 1 November 2026. This protocol establishes validation and provenance gates. It implements no new forecasting, uncertainty-estimation or MPC algorithm and reports no new efficacy result. Completion of a Stage 1 audit is distinct from permission to run a confirmatory experiment.

The scientific starting point is the [repository audit](RESEARCH_AUDIT.md), [reproducibility guide](RESEARCH_GRADE_REPRODUCIBILITY.md), [completed retrospective results](EXPERIMENTAL_RESULTS.md) and [publication assessment](PUBLICATION_READINESS.md). Frozen source, models, datasets, manifests and historical results remain authoritative records of the earlier study and must not be overwritten or relabelled.

## 1. Information timeline

An event timestamp describes the phenomenon being measured; an availability timestamp describes when an algorithm could actually read that information. Timestamp joins alone do not establish operational availability. A provenance record must establish clock semantics, aggregation intervals, latency and the meaning of an observation's timestamp before a deployment-like chronology can pass.

| Record | Required meaning | Eligibility at decision time `d` |
| --- | --- | --- |
| Raw observation | Source identity, event time or interval end, value, unit, and actual availability time | A feature may use it only when its event/support end is no later than the forecast origin and its availability is no later than the information cutoff |
| Feature | Feature name/value; all source event and source-availability times; support window; derivation identity; computed/available time | Every source availability is at or after its event and no later than feature availability; all support is complete and feature availability is no later than the forecast origin and decision |
| Forecast | Model hash; forecast origin `o`; issue time `i`; target `t`; horizon `h`; feature lineage | For the regular ten-minute direct horizons, `t = o + h × 10 minutes`, `h ∈ {1,…,6}`; features are available by `o`, and `o <= i <= d < t` |
| Model or fitted preprocessing | Hashes, fitting cutoff and completed training/calibration records | All fitted target labels and their availability precede the first origin at which the fitted object is used; an unknown fitting history is a provenance blocker, not a fabricated cutoff |
| Calibration residual | Original forecast/target identity; observation value; target time; observation availability; residual computation availability | **`target_time < d`**; observation availability is at or after its target; residual availability is no earlier than its forecast issuance and observation availability, and no later than `d` |
| Controller decision | Decision time, observed state availability and forecast/residual identities | All admitted information passes its own timing rule; future targets are not admitted merely because they are present in an offline CSV |
| Scored outcome | Target observation and subsequent verified execution trace | Read by the evaluator after decision commitment; never exposed as an input to the deployable decision policy |

The strict calibration-target inequality is intentional. A target exactly equal to decision time is rejected even if the same measurement could legitimately be used as a current-state feature. Availability at or before the decision does not override `target_time < decision_time` for residual calibration. Conversely, a past target whose measurement arrives late is still ineligible. A residual cannot be available before both its forecast and observation.

The forecast origin is the feature-information cutoff. Issuance may follow the origin to allow computation, but this delay never admits feature values released after the origin. For a retrospective simulation, training-label cutoff and declared model availability are records in the modeled data clock; filesystem modification time is not a substitute. Current hashes cannot independently attest when historical fitting, feature receipt or prediction actually occurred.

Operational timestamps must be unambiguous and timezone-aware. Comparison may use normalized UTC only after the source timezone, offset/DST treatment and interval semantics are evidenced. The historical SCADA timestamps are not silently assigned UTC or the workstation's London timezone. Naive timestamps may support a clearly labelled structural audit within the same unresolved source clock; they cannot pass confirmatory operational provenance. Date ordering is not a latency attestation.

The normative validator accepts an explicit authenticated grid anchor and checks elapsed multiples of ten minutes; its generic default is the UTC epoch phase. Forecast and residual records carry their declared anchor. A cohort must use one frozen source-supported grid convention, including for nonzero UTC phases, rather than selecting an anchor separately to repair individual records. This is a declared grid convention, not an inference about the historical source timezone. Timestamps must not be shifted to make them pass.

## 2. Feature and target checks

The new validation path must reject missing timestamps, invalid timestamps, duplicate record identities, duplicate source timestamps, nonmonotonic order and unresolved required joins. A missing ten-minute observation is a gap, not an invitation to shift positional indices. No forward fill, interpolation, timezone repair, duplicate aggregation or missing-row exclusion is implicit. Any later explicit repair requires a separate, versioned preprocessing policy fitted only on its permitted development data.

For a lag of `k` minutes, the source event must be exactly `o − k minutes` in the verified source clock. A rolling feature must enumerate or otherwise authenticate its complete historical support, not just its latest sample. Its support end cannot exceed `o`; a centered window or a future sample is rejected. An aggregate measurement labelled at interval start cannot be treated as known at that instant unless independent acquisition metadata supports that interpretation. The current raw value can be a feature only under evidenced end-of-interval/availability timing.

Forecast horizons are checked by timestamp arithmetic, not row shifts. Every saved target is joined to its actual source observation at the declared target time. The value/unit transformation must be explicit: historical signed raw power and the earlier nonnegative physical-power convention are different representations. Unknown power units, scale factors, missing-value sentinels or clipping provenance block operational eligibility rather than being guessed.

In the preserved artifacts, raw measurements/features and the forecast-table current-power values retain signed raw power. Prepared evaluation-block current power is clipped at zero; saved persistence predictions and actual forecast targets are also nonnegative. The structural audit applies each table's evidenced convention, rather than changing negative raw measurements or assuming every table has identical encoding. This is preservation of historical preprocessing, not a new correction to reported metrics.

## 3. Chronological partitions and embargo

Partitions are declared before test-outcome access. Training, calibration, development and any later test interval have explicit origin and target boundaries. Splitting on forecast origin alone is insufficient. For an earlier partition contributing labels to a later decision boundary `b`, every retained horizon-specific target must satisfy:

```text
origin + horizon_minutes < b
```

On a complete ten-minute clock, an origin exactly `h` intervals before `b` produces a target equal to `b` and is rejected for horizon `h`. Thus horizon-specific purging must test exact timestamps; an informal “one-hour gap” is not a substitute for the inequality. For a shared six-horizon calibration table, retain a row only if all its required target horizons meet the rule. For horizon-specific tables, preserve the distinct admissible origin sets and record exclusions without rewriting historical tables.

Cross-split target comparisons use **all horizon target timestamps**, not just matching horizons or h1. A physical observation cannot be both a development-influencing label and an independent test outcome through a different horizon. The validator checks target-time set intersections and availability relative to the earlier fitting/calibration cutoff. It also checks that every test episode follows the declared final development/freeze boundary; a valid local residual rule does not make earlier episodes independent of later controller selection.

Static partition separation is distinct from a frozen, prespecified online residual update. If a later Stage 2 protocol permits the existing adaptive rule to consume earlier test outcomes during sequential replay, those observations become eligible only for later decisions after the strict target and actual-availability checks pass. That rule must be fixed before outcome access, its update history logged, and no test-feedback tuning or controller selection permitted. Such prequential use creates chronological dependence and does not make individual scored outcomes independent. It cannot retroactively legitimize development access to the historical test cohort.

Missing timestamps do not shorten an embargo. Boundaries and gaps are interpreted in elapsed time in the authenticated clock, rather than a fixed number of surviving rows. All exclusions, including a rejected equal-time boundary, are saved in the new audit output; no original dataset or evaluation result is purged in place.

## 4. Exposure and honest cohort classification

Chronological inventory includes raw and processed data, saved prediction/calibration tables, development/evaluation blocks, archived output ranges, historical inspection scripts, source/document references and Git evidence where available. Each record distinguishes affirmative exposure evidence, inherited provenance declarations and unknown exposure. Importing or hashing data in a broad earlier audit is evidence of access, even if no final score was reported for a particular timestamp.

The fifty scheduled historical blocks include development block 6. The remaining 49 blocks have already been forecast, replayed, scored and discussed. They are **retrospective**, not untouched. Pre-freeze block-25/block-34 investigation and the block-6/block-7 target overlap are retained as historical evidence. The earlier first-development calibration-boundary defect is also retained. A correctly causal new audit cannot retroactively blind any of these observations.

Neither a filename containing `test`, an unused origin, a gap between archived blocks, nor absence of a matching metric row proves noninspection. Data uncovered by available scored ranges is classified as unknown or otherwise exposed according to evidence; it is not automatically eligible. Unknown exposure is insufficient for a confirmatory proposal.

An untouched proposal requires positive, reviewable evidence identifying a disjoint source/time interval, its complete target and feature-support ranges, pre-access reservation/custody history, absence of team outcome inspection or model/controller influence, and a freeze predating authorized access. A separate site or newly collected period may qualify only with these records and compatible input provenance. If no such candidate is evidenced, the result is:

```text
BLOCKED_CONFIRMATORY_TEST
```

The blocked result is a valid Stage 1 finding. It is not a failed solver run, a negative efficacy result or permission to recycle the 49 historical blocks as a confirmatory test. The audit documents what evidence/data is missing and leaves the test split unassigned.

## 5. Provenance gates

Required provenance includes dataset source and exact release/download identity, local checksum, acquisition/processing lineage, units and transformations, timezone/interval semantics, missing-data policy, observation/feature availability, licensing and permitted redistribution/use, model and fitted-preprocessor identities, fitting access history, protocol/config/source hashes and environment identity. A local SHA256 identifies bytes; it does not prove the original upstream version, license or absence of test influence. A source URL is not licensing evidence. A timestamp range is not access attestation.

Unknown metadata remains explicitly unknown. Stage 1 may inventory the existing artifacts and compare hashes while reporting provenance blockers. It must not invent a release version, assign a source timezone, guess measurement latency, infer a license from download availability or reconstruct an unrecorded training cutoff as an attested historical fact. Legacy forecasts can be checked for structural consistency without certifying them for untouched evaluation.

The reproducibility record distinguishes installed-version capture from a clean-environment reproduction. Pinned requirements and an installed package list are useful evidence but do not demonstrate that all artifacts can be obtained legally and all commands succeed in a fresh clone. No new heavy scientific dependency is necessary for chronology and lifecycle scaffolding.

## 6. Run lifecycle and preserved evidence

Only newly created paths under `publication_v2/` and the specifically named new Stage 1 documents are written. All original models, raw/processed data, manifests, historical scripts and saved results are read-only inputs. Capture their hashes before the Stage 1 work and compare them afterward. The expected original freeze SHA256 remains `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a`.

A run has a unique identifier and an exclusively created output directory. Existing or partial run paths are rejected; the scaffold never cleans or overwrites them. The experiment/audit manifest records the stage, interpretation, protocol and implementation identities, input hashes, environment and known blockers. Artifact checks precede their use. Hash mismatches, missing required artifacts, malformed configuration and failed validation are explicit errors. No missing file is replaced by synthetic research data.

Completion is published atomically only after intended audit outputs are written, flushed and authenticated. A partial/interrupted run must not have an accepted completion marker. Audit completion means the inventory/validation procedure completed; it may legitimately record `BLOCKED_CONFIRMATORY_TEST`. It never means an experiment ran or that a controller is ready for independent testing. Experiment execution is deliberately absent from Stage 1, including when synthetic tests exercise a successful lifecycle.

The archived negative uncontrolled comparison remains visible: uncontrolled wind has 1,465 violations and 317,210.288 kW summed exceedance; frozen fixed-margin MPC has 1,502 and 326,158.296; adaptive has 1,486 and 323,638.526. These are previously archived values, not Stage 1 efficacy estimates. Byte preservation and fresh arithmetic checks do not change their retrospective interpretation.

## 7. Stage 1 acceptance and subsequent work

Stage 1 acceptance requires passing data-independent leakage/boundary and lifecycle tests, actual-input availability/provenance reporting, before/after preservation checks, and an honest test-eligibility decision. Synthetic fixtures verify guards only. The [Stage 1 report](PUBLICATION_V2_STAGE1_REPORT.md) records actual test counts, inventory findings, failures/blockers, changed files and executed commands. The [Stage 2 plan](PUBLICATION_V2_STAGE2_PLAN.md) describes gated future work; it is not permission to train, tune or score new algorithms during Stage 1.

No journal-readiness, algorithmic-novelty, guaranteed-coverage, grid-compliance, battery-lifetime or confirmatory-efficacy claim follows from these checks.

## 8. Stage 1 commands

From the checkout whose Stage 1 code is being authenticated, use the existing Python environment and an unused run identifier:

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s publication_v2/tests -v
.venv/Scripts/python.exe -B -m publication_v2.runner audit --run-id stage1_unique_name
.venv/Scripts/python.exe -B -m publication_v2.runner preflight --run publication_v2/runs/stage1_unique_name
```

The audit command inventories and validates only. A successful audit command exits zero while recording `AUDIT_COMPLETED`, `BLOCKED_CONFIRMATORY_TEST` and `experiment_executed: false`. The preflight is expected to exit **2** while that scientific blocker remains; this is not an algorithm/test failure. Missing inputs or malformed/changed artifacts produce an audit error rather than a completion claim. The Stage 1 report supplies the actual commands, paths and test outcomes from this workspace. Test fixtures are synthetic and never substitute for missing research observations.
