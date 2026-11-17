# Publication v2 Stage 2.3: retrospective protocol amendment and review

This is a versioned amendment to the [Stage 1 protocol](PUBLICATION_V2_PROTOCOL.md), read alongside the [Stage 1 report](PUBLICATION_V2_STAGE1_REPORT.md), [Stage 2 plan](PUBLICATION_V2_STAGE2_PLAN.md), [Stage 2 methods](PUBLICATION_V2_STAGE2_METHODS.md) and [Stage 2.1 validation](PUBLICATION_V2_STAGE2_VALIDATION.md). Those historical documents are preserved unchanged. This amendment corrects the cohort-declaration clock for a new, explicitly retrospective pathway. It does not revise historical results, approve a dataset, authorize an experiment or establish untouched validation.

**`BLOCKED_CONFIRMATORY_TEST` remains in force. The real-data review registry remains empty. No real-data experiment was run for this correction.**

## Problem and scoped correction

The Stage 2.1 cohort validator required `declared_at` to precede every candidate historical forecast origin. That is appropriate evidence of a prospective declaration only when the declaration genuinely existed at that time. It is not a defensible prerequisite for a newly designed retrospective analysis of older observations: a new protocol must retain its actual creation date rather than claim that it existed in 2018.

Stage 2.3 introduces explicit study roles:

- `RETROSPECTIVE_DEVELOPMENT`: previously collected and potentially inspected observations may support a reviewed retrospective study. A declaration may postdate their event and replay-decision times. Prior access, assumptions and exclusions must be disclosed. New execution must follow actual approval.
- `PROSPECTIVE_CONFIRMATION`: untouched status requires independent non-exposure, custody and prespecification evidence. Selecting this string cannot authorize confirmation. The current implementation and empty registry continue to refuse confirmation.

The correction changes the relationship between analysis declaration time and historical event time. It does not weaken feature, target, fitting, calibration, source identity, rights, transformation or cohort checks. The existing exclusion of historically evaluated observations from new Stage 2 development admission remains in force. Historical observations remain exposed for confirmation purposes regardless of their development eligibility.

## Separate clocks and evidence

| Record | Meaning | Required interpretation |
| --- | --- | --- |
| Actual protocol creation | When the new analysis specification was created | Preserve the real date; bind it to independently reviewed evidence. For the new pathway, the cohort declaration must identify this creation record. |
| Actual protocol approval | When the reviewed analysis, declared use, exclusions and timing assumptions were approved | Must follow creation and precede new authorized execution. Approval does not establish a historical preregistration. |
| Independent clock anchor | Separately reviewed evidence anchoring the creation/approval record | Declared dates must agree with that evidence. Hashing a document does not establish its authenticity. |
| Actual acquisition and access | When the research team obtained or inspected the source and its outcomes | Preserve prior access even when it predates the new protocol. Acquisition is not an SCADA event or operational receipt time. |
| Historical observation | Source event or interval timestamp in the reviewed source clock | Retains its historical date and authenticated timestamp/interval semantics. |
| Historical replay decision | Simulated decision and forecast-information cutoff | Determines which source information may enter a simulated prediction. |
| Historical availability | Established or explicitly assumed source, feature, observation and residual availability in the replay clock | Each consumed item must satisfy the unchanged causal eligibility rules. An offline file containing future values is not an availability record. |
| Replay fitting cutoff and model availability | Historical information permitted for the simulated fit and the replay time at which the fitted object may be used | Training labels and receipts must be available by fitting; the model must be available before its first replay use. |
| Calibration cutoff | Latest permitted calibration target in the replay clock | The strict requirement remains `target_time < decision_time`, together with observation and residual availability. Equal-time targets are rejected. |
| Actual execution/fitting | When new software execution and fitting really occur | Must follow actual approval and the reviewed execution floor. A newly fitted artifact is not represented as having existed at a historical decision. |

Prior access is permissible in the retrospective role, but it must be recorded as prior exposure. It is not erased by an approval occurring later. Actual protocol dates and model wall-clock timestamps must never be replaced with historical observation times or filesystem modification times.

Code can validate timestamp syntax, ordering, consistency and hash bindings. It cannot prove that a self-authored historical date is true, that a reviewer was independent, or that an access log is complete. Those are external review responsibilities. Missing or inconsistent evidence fails closed; dates must not be backfilled to satisfy a check.

## Study contract and admission

The versioned implementation is [study.py](../publication_v2/stage2/study.py), integrated through [lineage.py](../publication_v2/stage2/lineage.py). Its closed schema and validation functions are the executable specification; a new real-data admission requires a separately hashed study-contract artifact. The dataset's `study_contract` reference has exactly `path` and `sha256`; evidence references use the same two keys. Timestamps must be explicit offset-aware strings. Unsupported keys in the closed contract and evidence objects fail validation.

A future independently approved real-data registry entry must retain all Stage 2.1 dataset/provenance/lineage/cohort/review-document bindings and additionally pin `study_role`, `study_contract_sha256`, `analysis_clock_evidence_sha256` and `availability_mode`. A missing or mismatched binding refuses admission. No such entry was installed. Synthetic tests exercise a temporary in-memory mock of this review over invented measurements; that mock is not a real approval.

The contract schema is `publication_v2.stage23.study.v1`, with exactly these top-level keys: `schema_version`, `study_role`, `analysis`, `data_access`, `availability` and `replay`.

| Object | Exact required fields and constraints |
| --- | --- |
| `analysis` | `protocol_created_at`, `protocol_approved_at`, `planned_execution_not_before`, `reviewer`, `clock_evidence`. Creation must be no later than approval, approval no later than the execution floor, and the floor no later than actual admission time. The cohort's `declared_at` equals `protocol_created_at`. |
| Analysis `clock_evidence` JSON | `schema_version` = `publication_v2.stage23.analysis-clock.v1`, `protocol_created_at`, `protocol_approved_at`, `reviewer`, `recorded_at`. The creation/approval/reviewer values must match the contract; recording must be at or after approval and no later than the execution floor. |
| `data_access` | `acquired_at`, `first_access_at`, `exposure_status`, `prior_study_roles`, `custodian`, `recorded_at`, `evidence`. Acquisition must be no later than first access, first access no later than recording, and recording no later than approval. Exposure is `PREVIOUSLY_INSPECTED` or `EXPOSURE_UNKNOWN`; neither means untouched. Prior roles are a unique list drawn from the two study roles. |
| Access `evidence` JSON | `schema_version` = `publication_v2.stage23.access-record.v1`, plus the exact access fields above except `evidence`. Every repeated value must match the contract. |
| `availability` | `mode`, `operational_availability_established`, `historical_deployability_verified`, `evidence`; additionally `scenario` only for `ASSUMED_LATENCY`. Mode is `VERIFIED_OPERATIONAL` or `ASSUMED_LATENCY`. The operational flag must match that choice, and the historical-deployability flag must be `false` for both choices. The evidence file is hash-checked and independently reviewed, not authenticated by its hash. |
| Assumed `scenario` | `scenario_id`, `units` = `seconds`, `measurement_latency_seconds`, `feature_processing_latency_seconds`, `residual_processing_latency_seconds`, `rationale`. Delays must be numeric, finite and between zero and 86,400 seconds inclusive; booleans are rejected. Identity and rationale must be nonempty. |
| `replay` | `model_fitting_cutoff`, `model_available_at`, `static_calibration_target_cutoff`, `calibration_rule` = `target_time < decision_time`, `availability_rule` = `observation_available_at <= decision_time and residual_available_at <= decision_time`. The current runner supports fitting cutoff and model availability both equal to the dataset's `fit_time`; differing values fail instead of being ignored. |

The dataset must explicitly declare `contains_confirmation_data: false`. If it also supplies `study_role`, it must agree with the contract. For real data, `provenance.availability.value` must be an object identifying the same availability `mode`; an undifferentiated attestation cannot substitute for this distinction. Historical observations must precede the actual execution floor. The admission report records the actual check time and distinct historical observation, replay-decision, feature-availability and target-availability ranges.

Training target, observation-availability and residual-availability times must not exceed the replay fitting cutoff. The fitted object must be available before calibration use. All static calibration targets must be no later than the declared static cutoff, which must be strictly before the first development decision; all static observation/residual receipts must be available by that decision. The underlying Stage 1 checks continue to enforce complete source support, strict embargoes and target-disjointness.

The contract is additional evidence. It does not replace the upstream/canonical source ledger, reviewed source rights and clock semantics, transformation manifest, authorized role-specific periods, missing-data policy or complete feature/target support. Real admission still requires a separately trusted registry entry that pins the reviewed dataset and its evidence identities. A dataset cannot approve itself by supplying a reviewer name, an `ATTESTED` flag or a matching checksum.

Legacy synthetic software fixtures remain identified as software-only. They do not supply approval or operational evidence for a real dataset. Retaining their earlier declaration guard avoids rewriting the previously staged fixtures while the new pathway receives separate regression coverage.

## Verified and assumed availability

The timing record must distinguish evidence of operational availability from a declared assumed-latency replay. Where operational availability is not established, only a clearly named, reviewed assumed-latency scenario can support the retrospective timing interpretation. Its measurement and processing delays must be explicit, finite and nonnegative, and consistent with the supplied record-level availability metadata. A missing, negative, contradictory or unsupported scenario is rejected.

Every study through this retrospective pathway must state that historical deployability is not verified, including a replay with reviewed operational receipt evidence. Receipts alone do not prove that a newly fitted model existed at a historical issue time or met an actual operational deadline. An assumed-latency replay additionally cannot claim that measurements arrived with the assumed delay. A documented assumption is a scenario definition, not a measured historical latency.

The scenario must describe the supplied ledger without rewriting it: every measurement receipt equals event time plus measurement delay; feature availability equals its latest source receipt plus feature-processing delay; and residual availability equals the later of target availability and forecast issuance plus residual-processing delay. These equality checks supplement the unchanged eligibility inequalities. The one-day bound is an explicit supported-metadata limit, not an estimated physical latency or an empirically selected performance parameter.

All causal checks still apply within the scenario:

- Features enumerate complete source support, with source availability no later than feature availability and feature availability no later than the forecast origin.
- Forecast targets retain exact horizon arithmetic; issuance and decision precede targets.
- All training labels and their availability satisfy the reviewed replay fitting cutoff; later calibration/development outcomes cannot affect fitting.
- Calibration observations have targets strictly before the current decision and observation/residual availability no later than that decision.
- Scoring outcomes are not inputs to a prediction or interval construction before their release.

In particular, the existing feature set includes the current observation at the forecast origin. A positive measurement or required processing delay makes that feature unavailable at that same origin. The validator must reject the inconsistent combination. It must not silently move the origin, shorten a delay or declare a receipt equal to its event. Changing the feature/origin convention requires a separately reviewed experiment definition. An assumed delay also cannot resolve an unknown timezone, ambiguous interval label or source licence.

## Exposure and confirmation firewall

Study role is not an observation identity or a non-exposure attestation. Source identities, stable observation identifiers, normalized measurement content, transformation lineage and reviewed authorized periods continue to constrain admission. CSV formatting, row order, paths, hashes, aliases or a changed role string cannot turn known historical observations into an untouched cohort. No known match is not evidence of non-exposure; ambiguous identity collisions remain unresolved.

The 49 archived evaluated blocks remain retrospective. The known historical source remains `HISTORICALLY_INSPECTED_NEVER_UNTOUCHED`. The [trust policy](../publication_v2/stage2/provenance_policy.json) remains unapproved for real data and retains `BLOCKED_CONFIRMATORY_TEST`.

A future confirmation proposal requires independently supported reservation/custody, source and period identity, complete access history, no outcome-driven design influence, prespecification before authorized outcome access and compatible operational provenance. This correction does not implement an override for those requirements.

## Migration instructions

1. Preserve the original dataset documents, manifests, cohort declarations, study outputs and historical source artifacts. Do not rewrite a historical declaration or replace an inconvenient result.
2. Create a new, versioned retrospective study-contract artifact with actual analysis dates and separately reviewed acquisition/access/exposure evidence. Retain unknown evidence as unknown rather than inventing dates.
3. Create a new cohort-policy version whose declaration identifies actual protocol creation. Prespecify the new analysis windows, missing-data rules, exclusions, reasons and denominators before new execution; disclose any earlier inspection influencing them.
4. Reference the new hashed contract from the new dataset/lineage declaration using the executable schema. Recalculate artifact and transformation implementation identities for the new version; do not alter an older manifest to make its hashes pass.
5. Obtain independent review of source rights, timing semantics, transformation, authorized periods, exclusion policy and replay fitting chronology. A reviewed assumed-latency scenario must retain its restricted claim scope.
6. Seek a separately approved real-data registry entry. This software correction does not populate the registry, admit Kaggle data or authorize fitting.
7. Only after admission and further user authorization may a new development-only run use a unique output path, record actual fit/execution dates and retain all failures. Confirmation remains blocked.

The exact contract keys and supported schema are defined by `study.py`; unsupported metadata must be rejected rather than silently ignored. Actual evidence must be retained separately from assumptions in the resulting admission report.

## Remaining blockers and limits

- Real-data registry approval is absent. Source rights, release identity, clock/interval semantics and historical availability still require independent review.
- A local acquisition trace or matching source hash does not establish those facts or untouched status.
- Where receipt history cannot be recovered, any authorized retrospective result must remain explicitly conditional on its reviewed availability scenario.
- Installed dependency/native fingerprints do not establish clean-environment reproduction; that remains separate work.
- Synthetic regression success is software evidence, not forecast accuracy, coverage, MPC efficacy, operational deployability or confirmatory validation.
- Chronological and overlapping-horizon dependence remains a statistical limitation. This timing correction introduces no new coverage or significance guarantee.
- The archived negative uncontrolled-wind comparison remains: 1,465 uncontrolled violations, 1,486 adaptive violations and 1,502 fixed-margin violations. No archived finding is changed.

## Validation and preservation evidence

Validation completed on 5 November 2026 on `research/publication-v2`, starting and finishing at HEAD `9517ec8`. These are new software-validation runs, distinct from the retained Stage 2.1 evidence.

| Final validation | Run | Passed | Failed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: | ---: |
| Stage 1, standard library only | 59 | 58 | 0 | 0 | 1 |
| Stage 2, including 28 new retrospective tests | 120 | 120 | 0 | 0 | 0 |
| Combined unique cases | 179 | 178 | 0 | 0 | 1 |

The Stage 1 run took 11.722 seconds. Its sole skip is the Windows account's unavailable native symlink-creation privilege; other symlink/junction rejection cases still run. The final full Stage 2 run took 128.297 seconds including discovery; the separately run 28-case retrospective suite passed in 13.611 seconds. The earlier full Stage 2 pass contained 116 cases before four additional boundary/review regressions were added; it is not added again to the unique-case total.

An initial isolated new-test run had 23 passes and one test-helper error when removing an optional fixture reference. The helper was corrected, then the complete targeted and full suites passed. The Stage 1 tests themselves passed on their first run; a temporary JSON-summary exporter subsequently failed to serialize a skipped TestCase object. The summary was recovered from the unchanged completed unittest log. Neither issue changed production guards or research artifacts.

New regressions cover late declarations, declaration/clock backdating mismatches, malformed or future actual clocks, prior access disclosure, historical observation matches after CSV reserialization/reordering, confirmation relabelling, missing/tampered independent review bindings, invalid or unsupported latency metadata, unavailable features, model fitting boundaries and strict calibration cutoffs. A fully consistent one-second feature-processing scenario reaches and fails the unchanged Stage 1 feature-origin gate. Synthetic verified-availability admission still cannot claim historical deployability. Even a fully matching mocked review cannot open prospective confirmation.

The full Stage 2 suite includes native fitting, save/reload and repeated-workflow checks on invented temporary fixtures. No real SCADA fit, forecasting experiment, uncertainty-performance comparison or MPC experiment ran. No real research metrics were generated.

Equivalent commands to reproduce the executed unittest discovery runs from the repository root are:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:GIT_OPTIONAL_LOCKS = '0'
$env:MPLBACKEND = 'Agg'
.venv/Scripts/python.exe -S -B -m unittest discover -s publication_v2/tests -v
.venv/Scripts/python.exe -B -m unittest discover -s publication_v2/stage2/tests -v
.venv/Scripts/python.exe -B -m unittest publication_v2.stage2.tests.test_retrospective -v
```

Validation used the standard unittest loader/runner with logs, machine-readable summaries and matplotlib cache outside the repository in `C:/Users/arqam/AppData/Local/Temp/wind_stage23_zmul_6at/`. Temporary evidence is local and may expire; commands and test sources are the reproduction instructions. Existing validation logs and research output directories were not overwritten. A clean-environment installation remains unverified.

Preservation checks pass for all **2,170 protected files** and all **59 frozen references**. The original freeze manifest remains `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a`. A task-start content snapshot additionally verifies **2,204 unrelated existing files** and all **185 staged working files** unchanged. The index remains `131c0b2e149ec81feb7cadcdeeb5115bd25b73b71abacc950a15a5424a711809`; no staging or other Git mutation was performed. The installed real-data registry remains empty and `publication_v2/stage2/runs/` remains absent.

Exact task changes:

- Modified the pre-existing, untracked `publication_v2/stage2/lineage.py` to call the study validator and scope the old declaration-before-origin check to legacy synthetic fixtures.
- Added `publication_v2/stage2/study.py`.
- Added `publication_v2/stage2/tests/test_retrospective.py`.
- Added `docs/PUBLICATION_V2_RETROSPECTIVE_PROTOCOL_REVIEW.md`.

None of the 185 existing staged working files was changed by Stage 2.3. The original Stage 1 protocol/report/plan, Stage 2 methods and Stage 2.1 validation remain unchanged. This amendment is the versioned protocol-documentation correction.

Protected original research, models, datasets, manifests, historical scripts and results remain read-only. Original protocol documents and existing staged additions are preserved. No reset, clean, commit, merge or push is authorized. This amendment reports a transparent retrospective-development pathway while retaining the scientific admission blockers.
