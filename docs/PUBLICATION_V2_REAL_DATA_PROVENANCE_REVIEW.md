# Publication V2 Stage 2.4: real-data provenance and admission review package

Prepared 5 November 2026 for independent review on `research/publication-v2`. **Status: `PENDING_REVIEW`; real-data admission is not approved. `BLOCKED_CONFIRMATORY_TEST` remains in force.** This package assembles evidence and questions. It does not authorize a fit, certify operational availability, establish an untouched cohort or revise any archived result.

Read this with the preserved [Stage 1 protocol](PUBLICATION_V2_PROTOCOL.md), [Stage 1 report](PUBLICATION_V2_STAGE1_REPORT.md), [Stage 2 plan](PUBLICATION_V2_STAGE2_PLAN.md), [Stage 2 methods](PUBLICATION_V2_STAGE2_METHODS.md), [Stage 2.1 validation](PUBLICATION_V2_STAGE2_VALIDATION.md) and [Stage 2.3 retrospective amendment](PUBLICATION_V2_RETROSPECTIVE_PROTOCOL_REVIEW.md). Those records remain unchanged. The implemented admission requirements are in [lineage.py](../publication_v2/stage2/lineage.py) and [study.py](../publication_v2/stage2/study.py); the [installed trust policy](../publication_v2/stage2/provenance_policy.json) has no approved real-data reviews.

Package artifacts:

- [Machine-readable evidence register](../publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/evidence_register.json).
- [Proposed registry entry, pending only](../publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/proposed_registry_entry.json).
- [Reviewer decision form](../publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/reviewer_decision_form.json).
- [Non-experimental package validator](../publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/validate_package.py), its [regression tests](../publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/test_validate_package.py) and [validation report](../publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/validation_report.json).

The proposed entry is separate from the installed registry. Its pending status, unresolved fields and unsigned decision form cannot supply independent review or approve themselves. A checksum identifies bytes; it does not authenticate scientific provenance, a legal right, a date or a reviewer's independence.

## Evidence categories and source identity

| Category | Meaning in this review | What it cannot establish |
| --- | --- | --- |
| Independently authenticated evidence | Provider/custodian records whose authority, identity and relevant content have been independently checked. | No substantive source licence, release mapping, clock or availability evidence currently meets this category. A resolving website title is not authentication of SCADA acquisition history. |
| Local corroboration | Directly observed local bytes, headers, archive contents, hashes and Windows download-origin metadata. | Upstream ownership, licence, unmodified historical receipt history or truthful operational latency. Local filesystem/alternate-stream metadata is mutable. |
| Author-created records | Repository attribution, scripts, audit outputs, exposure inventories, protocol statements and software tests. | Independent provider confirmation or independent non-exposure. They can document implemented transformations and prior access. |
| Assumptions | Explicit simulator conventions or a future reviewed scenario, clearly separated from observations. | Measured historical latency, verified deployment, source rights or an independently reserved cohort. |
| Missing evidence | A fact or supporting record that has not been established. | A plausible value is not a substitute. Missing fields remain unresolved rather than receiving inferred dates, offsets or permissions. |

The repository attributes the source to **Berker Isen, Wind Turbine SCADA Dataset**, at the [official Kaggle landing page](https://www.kaggle.com/datasets/berkerisen/wind-turbine-scada-dataset). The landing URL and title resolve, but substantive metadata was not readable through the automated browser during this review. Repository attribution and the local Kaggle acquisition trace corroborate the dataset association; they do not independently establish the original operator, farm, turbine model, release authority or upstream extraction procedure.

## Exact local artifacts and acquisition corroboration

| Artifact or record | Local finding | Evidence limit |
| --- | --- | --- |
| `data/raw/T1.csv` | 3,971,851 bytes; SHA256 `f92c33c1cc199756b759fec251eeddc506f35d6a9e47ede034fc3e339a7c46d5`. | Identifies the supplied raw file, not its legal rights or an independently authenticated release. |
| Existing `Downloads/archive.zip` | 1,571,389 bytes; SHA256 `a867d34200add600eedb3832540435cf57335ba6374c77b50f90b0ab16553ea1`. The ZIP contains only `T1.csv`; that member matches the repository file byte-for-byte. | Archive association is directly corroborated. No licence or provider metadata sidecar is present in the archive. |
| Raw-file `Zone.Identifier` | Refers to the local `Downloads/archive.zip`. | A mutable local origin reference, not a signed acquisition certificate. |
| Archive `Zone.Identifier` | Kaggle referrer; storage path `kaggle-data-sets/133415/317642/bundle/archive.zip`; signed-URL generation time `2026-10-12T14:17:29Z`. | Bundle identifiers are lookup clues. The signature/query was not published or reused. URL generation time is not an independently verified completed-download time. |
| Local archive timestamps | Creation `2026-10-12T14:17:29.3497419Z`; modification `2026-10-12T14:17:30.1259435Z`, consistent with the download trace. | Filesystem timestamps are mutable; they do not establish first research access, a protocol date or an observation's operational receipt. |
| ZIP member timestamp | `2019-10-19 17:14:48`, without authenticated timezone semantics. | Must not be promoted to a release or acquisition date. |

The archive was inspected locally without extraction or modification. Its recovered trace strengthens the acquisition trail compared with the earlier documents, which recorded acquisition as unknown. Those historical documents are not rewritten to imply that this evidence was available to their original authors. A complete first-access/exposure ledger remains missing.

## Public metadata: findings and requests

Only metadata was sought; no new outcome files, dataset previews or archives were downloaded. On 5 November 2026 the following official endpoints were attempted:

| Public metadata route | Review result |
| --- | --- |
| [Current dataset landing](https://www.kaggle.com/datasets/berkerisen/wind-turbine-scada-dataset) and [legacy URL](https://www.kaggle.com/berkerisen/wind-turbine-scada-dataset) | Title/URL resolve; no readable substantive page body. Legacy URL redirects to the current landing. |
| [Dataset-view API](https://www.kaggle.com/api/v1/datasets/view/berkerisen/wind-turbine-scada-dataset), [metadata API](https://www.kaggle.com/api/v1/datasets/metadata/berkerisen/wind-turbine-scada-dataset) and [list query](https://www.kaggle.com/api/v1/datasets/list?search=wind-turbine-scada-dataset) | Inaccessible through the browser tool. |
| [Version lookup `317642`](https://www.kaggle.com/dsv/317642) and [numbered-version query](https://www.kaggle.com/datasets/berkerisen/wind-turbine-scada-dataset?datasetVersionNumber=1) | Inaccessible; no authenticated mapping to a numbered release was obtained. |
| [Uploader-discussion reference](https://www.kaggle.com/datasets/berkerisen/wind-turbine-scada-dataset/discussion/86526) | Inaccessible; alleged provider statements in third-party citations cannot replace the original record. |

These are retrieval limits, not evidence that Kaggle omits a licence or version. The reviewer should capture the official metadata in an ordinary browser or authorized metadata-only API, preserving retrieval date, URL and exact returned record. Do not substitute a notebook's software licence, a mirror's licence or generic Kaggle licence documentation for the dataset's terms.

| Question | Potential public evidence | Provider/custodian clarification if unresolved |
| --- | --- | --- |
| Exact release | Owner/publisher, release/version number and ID, update history, file identity and checksum metadata; mapping to storage bundle `133415/317642`. | Identify the exact released archive and original extraction/version when public records cannot map the local bytes. |
| Applicable rights | Official dataset licence field and text, versioned/archived terms applicable to the apparent 12 October 2026 acquisition; attribution and redistribution requirements. | Confirm uploader authority and operator/OEM rights where the release authority or scope is unclear. Current public terms alone do not establish acquisition-time terms. |
| Physical source | Provider description and authenticated clarification of farm/turbine/operator and measurement provenance. | Confirm identities and any restrictions without relying on inconsistent third-party papers or inferring them from measured values. |
| Measurement semantics | Official signal dictionary, unit/aggregation definitions and clock documentation. | Confirm timezone/DST, clock synchronization, interval labels/windows, sensor position, latency and quality flags. |

No substantive licence, release, clock or availability fact has been independently authenticated here. Third-party reuse corroborates attribution only; repeated claims are not provider evidence.

## Clock, sampling, power and availability uncertainties

Stage 1's structural inventory reports **50,530 observations**, from `2018-01-01 00:00` to `2018-12-31 23:50` in an unresolved naive source clock, with **zero duplicate timestamps, 32 gaps and 2,030 absent expected ten-minute slots**. Missing slots are not zero generation; gap causes and outage/curtailment/sensor flags are unresolved. These counts are local audit evidence, not a provider quality certificate.

| Field | Established locally | Unresolved review requirement |
| --- | --- | --- |
| Timestamp parsing | Historical code parses day-month-year and sorts the recorded times. | Source timezone, UTC offset/DST, clock synchronization and start/end/instantaneous label meaning. Do not assign UTC, London time or a presumed Turkish offset. |
| Ten-minute cadence | Expected grid and observed gaps are structurally checkable. | Whether each value is an instantaneous reading, ten-minute average or other aggregate; its complete physical support window. |
| Measured active power | Source header says `LV ActivePower (kW)`; signed measurements exist. | Signal's net/gross/auxiliary-load interpretation and quality/curtailment flags. |
| Wind signals | Headers specify wind speed in m/s and direction in degrees. | Sensor location, averaging convention, corrections and operational delivery semantics. |
| Theoretical curve | Header says `Theoretical_Power_Curve (KWh)`; unused by the frozen feature set. | Physical interpretation/unit ambiguity requires provider clarification, not a silent correction to kW. |
| Observation and feature availability | Complete lag joins can be reconstructed. | Historical observation receipt, feature computation/delivery, issuance, residual-computation and model-availability records are absent. |
| Interval-ending convention | Historical simulator documentation declares an interval-ending interpretation. | It remains an author-created simulation convention, not source-confirmed semantics. |

The target transformation `max(0, raw_power_kw)` is a declared nonnegative representation of **measured active power**. It does not identify unconstrained available wind power or counterfactual production without turbine curtailment. Do not infer aerodynamic potential, recoverable curtailment or an operator-independent generation ceiling from this table. Any later study must state that measurement limitation.

Where actual availability cannot be recovered, Stage 2.3 allows only an independently reviewed, named `ASSUMED_LATENCY` retrospective scenario consistent with every supplied source/feature/residual record. All delays, units, rationale and scenario evidence remain pending; zero delay is not automatically selected. Assumed timing cannot establish timezone, timestamp-window semantics, a legal permission or a genuine historical receipt.

The existing feature set includes the current event at the forecast origin. Positive measurement or feature-processing latency makes that current feature unavailable under the unchanged origin contract. The implementation rejects that combination; no origin or receipt is silently shifted. A new feature/origin convention or a transformation that constructs assumed availability needs separate review and implementation. Both availability modes retain `historical_deployability_verified: false` because operational receipts would still not prove that a newly fitted model existed or met a deadline in 2018.

## Transformations, fitting chronology and exclusions

The preserved scripts and structural audits establish an implemented historical chain:

1. [prepare_forecasting_data.py](../scripts/prepare_forecasting_data.py): raw SCADA parsing and sorting, signal selection, and retention of exact ten-minute forecast pairs.
2. [build_wind_features.py](../scripts/build_wind_features.py): exact timestamp joins for 10/20/30/60-minute lags, current-minus-previous changes and the four-point power mean at `t`, `t-10`, `t-20`, `t-30`; incomplete required support is dropped rather than interpolated.
3. [prepare_multistep_ml_data.py](../scripts/prepare_multistep_ml_data.py): six targets at origin plus 10 through 60 minutes; complete-horizon filtering and intended target-level split embargoes.

Stage 1 reconstructed 50,320 feature rows, 50,125 multistep rows, 1,406,230 feature-support checks and 401,195 raw target joins. These are structural check counts, not independent statistical samples. Signed raw/features and the nonnegative target/persistence/evaluation representations remain distinct and preserved. The scripts were not executed during this provenance-package task; some historical scripts overwrite their destinations if run.

**No admissible new canonicalization of the real T1 source has been instantiated.** The current supported transform is a closed one-to-one mapping of an already offset-aware source ledger containing event time, availability time and stable observation IDs. The five-column naive T1 file does not supply those fields. A column map cannot legitimately invent them. A later conversion requires reviewed source semantics, an explicit identity scheme that does not misrepresent generated IDs as provider-issued, and a separately reviewed transformation identity if the conversion exceeds the supported implementation. A matching raw checksum or structurally correct old feature table does not fill this gap.

The historical preparation script's `2018-09-09 02:50` validation boundary and `2018-11-05 15:10` test boundary are **historical source-clock constants**, not actual fit/approval dates or newly authorized Stage 2 cutoffs. The script intends to retain earlier origins only when their last six-step target is strictly before the next boundary. Current source code does not independently attest which exact code/data fitted each historical model, when fitting finished or which outcomes influenced selection. The seven archived model artifacts remain unchanged and are not retrained.

For a new retrospective study, the reviewer must specify and pin actual protocol creation/approval and access evidence separately from replay model-fitting/availability cutoffs and the static calibration target cutoff. Training labels and their receipts must be available by the replay fit cutoff; fitting must precede calibration use. Static calibration targets must precede the first development decision, and every rolling/weighted residual must satisfy **`target_time < decision_time`** plus observation/residual availability by that decision. Equal-time labels remain ineligible. **All new study, fit, calibration and authorized-period values are unassigned pending review.** Historical constants must not be copied in as presumed approvals.

Preserved historical exposure and boundary findings from the [Stage 1 report](PUBLICATION_V2_STAGE1_REPORT.md) must be disclosed:

- All 49 historical scored blocks have been examined. Prior raw/full-feature audits and pre-freeze block-25/block-34 investigations are recorded. No local interval gains untouched status from absence of a saved metric.
- At the first development episode (`2018-10-15 11:00`), static calibration has 21 affected horizon/decision cells across six decisions, containing 56 repeated unavailable-label/decision pairs. This historical calibration is not repaired in place.
- Development-designated block 6 shares 15 cross-horizon target pairs and five scored h1 target timestamps with evaluation block 7. Its evaluation-style filename supplies no independent eligibility.
- The 2,990-origin development-labelled table extends to `2018-11-05 15:00`, with inferred h6 support to `16:00`; its tail shares another 15 pairs and five scored h1 timestamps with evaluation block 1. Use of that tail in frozen-controller selection is not established. The union contains 30 horizon-target pairs and ten scored h1 timestamps of overlap.

The existing real-development gate excludes historically evaluated support and unresolved matches to it. No new authorization window is proposed here. Missing-source slots, missing feature/target support, candidate windows, included/excluded origins, reasons and denominators must be declared and reviewed before new execution. Do not omit difficult periods because of their forecast or controller outcomes. CSV reserialization, reordering, renamed files or namespaces cannot erase source exposure. No known match is not evidence of non-exposure.

## Retrospective admission checklist and reviewer decision

The supplied [decision form](../publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/reviewer_decision_form.json) is uncompleted. Reviewer identity, independence evidence, decision date, signature/attestation and authorized periods must not be fabricated or backdated. The report's preparation date is not a source or study approval date.

| Review gate | Evidence needed for a legitimate decision | Current disposition |
| --- | --- | --- |
| Reviewer authority and independence | Named reviewer, relevant authority, independence/conflicts disclosure and authenticated decision record. | Pending; no reviewer has approved this package. |
| Exact source/release and acquisition | Official release mapping, raw/archive identity, acquisition evidence and disclosed limitations. | Local bytes/trace corroborated; independent mapping and complete access history pending. |
| Rights | Applicable licence or explicit permission, release authority, permitted research/reproduction/redistribution scope and required attribution. | Not independently verified. |
| Clock and measurement semantics | Source-supported timezone/DST, grid, interval/window, units and signal meaning. | Headers/grid checkable; substantive timing semantics unresolved. |
| Availability interpretation | Reviewed operational records or explicitly conditional, named assumed-latency scenario; no deployability claim. | No real operational evidence or approved scenario. |
| Processing lineage and identities | Separate source/canonical artifacts, reviewed transformation implementation and hashes, stable observation namespace/IDs and no unreviewed repairs. | Historical code structurally audited; no admissible new real canonical ledger. |
| Actual study and access clocks | Real creation, approval, execution floor, acquisition/access/exposure records with independent evidence. | Not instantiated for a new real study. |
| Cohort and exclusions | Exact train/calibration/development support periods, missing slots, candidate windows, exclusions/reasons/denominators and historical-match review. | Unassigned; preserved historical defects disclosed. |
| Fitting and calibration | Reviewed replay fit/model availability/static cutoff, causal residual checks, strict embargo and target-disjointness; actual new fits after approval. | Validators exist; new cutoffs remain unassigned. |
| Reproduction | Legally accessible inputs, complete environment/native records and checked execution instructions; explicit clean-environment limits. | Recorded software checks exist; clean-environment reproduction remains unverified. |
| Claim scope | Retrospective/development-only, conditional on assumptions, no independent confirmation or historical deployment claim. | Required restriction; does not itself grant admission. |

For this package the defensible current decision is **defer admission pending evidence**. A reviewer may acknowledge the local identities, archive association, structural audits and truthful retrospective classification without approving real-data execution. No partial acknowledgement should populate the trusted registry or be read as research authorization.

A later reviewer could conditionally approve a specific retrospective-development question only after rights, source/clock semantics, transformation, exposure/cohort, exclusions, fitting chronology and availability interpretation have been resolved and pinned to exact artifacts. If operational receipts cannot be recovered, approval may cover a clearly stated hypothetical timing scenario; it cannot certify that scenario as observed history. Approval must identify its restrictions, unresolved nonblocking limitations and permitted periods, and precede new fitting. User authorization and a successful fail-closed preflight remain separate execution conditions.

Confirmation remains blocked even after such retrospective admission. Reusing the historical source, changing study-role labels or collecting a fresh copy of already inspected observations cannot establish non-exposure. A future confirmation proposal requires independently reserved data, custody/access evidence and prespecification before outcome access through a separately reviewed pathway.

## Scientific interpretation and next actions

This package supplies no new forecast-accuracy, interval-coverage, statistical-significance or MPC-efficacy result. Chronological dependence and overlapping horizons remain limitations; passing timestamp code is not a coverage theorem. The archived negative uncontrolled-wind comparison remains visible: 1,465 uncontrolled violations, 1,486 adaptive MPC violations and 1,502 fixed-margin MPC violations. No archived measurement or result is changed.

Recommended sequence:

1. Independently capture the official release/licence metadata and acquisition-version mapping; seek provider clarification only through a separately authorized contact.
2. Resolve clock/interval/unit and rights questions, or document that the source cannot meet the current protocol. Preserve unknowns as unknown.
3. Review an explicit retrospective measurement/availability scenario and any necessary new transformation; do not synthesize admissible timestamps or IDs in this package.
4. Define new actual analysis/access records, eligible source periods, fitting/calibration cutoffs and a complete exclusion ledger without backdating or reusing evaluated support.
5. Have an independent reviewer complete a new decision record. Only a subsequent authorized change may install a reviewed registry entry; this pending proposal must not be promoted automatically.
6. Recheck preservation and the complete admission/environment gates before seeking authorization for any real-data experiment. Retain `BLOCKED_CONFIRMATORY_TEST`.

## Validation and preservation

Current non-experimental checks completed on 5 November 2026 on `research/publication-v2`, HEAD `9517ec8`:

| Executed validation | Run | Passed | Failed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: | ---: |
| New package tests, standard library only | 20 | 20 | 0 | 0 | 0 |
| Existing Stage 2 data/lineage/retrospective/conformal guards | 68 | 68 | 0 | 0 | 0 |
| Stage 1, standard library only | 59 | 58 | 0 | 0 | 1 |
| Total | 147 | 146 | 0 | 0 | 1 |

The skip is the Windows account's unavailable native symlink-creation privilege. No native model-fitting tests, model loading/inference, real-data fits or research experiments were executed. Synthetic guard fixtures and temporary test bytes are software checks, not SCADA performance evidence.

The read-only package validator returns `INTERNALLY_CONSISTENT_PENDING_REVIEW`, `scientific_admission: false`, `experiments_authorized: false` and `BLOCKED_CONFIRMATORY_TEST`. It checks 25 evidence items, 22 unchecked review areas, 29 hashed local evidence references, seven model byte hashes without loading the models, and the still-empty installed registry. With the explicit local archive argument it also rechecks archive/member hashes without extracting files. Success means that this initial pending package is internally consistent; it does not approve legal or scientific provenance. A later completed reviewer decision must be retained in a new version and separately reviewed; this initial-pending-state validator does not promote a completed form into an approval.

New regressions reject approval-state promotion, false confirmation roles, fabricated reviewer identities/dates/periods/cutoffs, missing review areas, omitted evidence topics, false independent-authentication claims, populated missing evidence, changed artifact hashes, signed-URL credential leakage, escaping or missing file references, and incorrect archive contents.

Reproduce the non-experimental checks from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:GIT_OPTIONAL_LOCKS = '0'
.venv/Scripts/python.exe -S -B -m unittest discover -s publication_v2/stage2/admission_reviews/berker_isen_t1_stage24 -p test_validate_package.py -v
.venv/Scripts/python.exe -S -B -m unittest discover -s publication_v2/tests -v
.venv/Scripts/python.exe -B -m unittest publication_v2.stage2.tests.test_data publication_v2.stage2.tests.test_lineage publication_v2.stage2.tests.test_retrospective publication_v2.stage2.tests.test_conformal -v
.venv/Scripts/python.exe -S -B publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/validate_package.py --root . --archive-path "$env:USERPROFILE\Downloads\archive.zip"
```

The archive argument is optional for portable metadata checks. Omitting it records `NOT_REQUESTED`, never a verified archive. Missing/mismatched supplied files fail explicitly. No validator command writes a completion marker, registry entry or research output.

Preservation passes for all **2,170 protected files** and all **59 freeze references**. The frozen manifest remains `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a`. A task-start snapshot additionally verifies all **2,208 existing files** in the protected/staged/untracked scope, including Stage 2.3 work, unchanged. All **185 staged working files** and the Git index remain unchanged; index SHA256 is `131c0b2e149ec81feb7cadcdeeb5115bd25b73b71abacc950a15a5424a711809`. The real-data registry remains empty and `publication_v2/stage2/runs/` remains absent.

The [machine-readable validation report](../publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/validation_report.json) records the executed counts, local package checks and preservation results. Detailed logs and the task-start snapshot were written outside the repository to `C:/Users/arqam/AppData/Local/Temp/wind_stage24__27zj2kt/`; temporary evidence may expire.

Exactly seven new files comprise Stage 2.4; no pre-existing file was changed:

- `docs/PUBLICATION_V2_REAL_DATA_PROVENANCE_REVIEW.md`
- `publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/evidence_register.json`
- `publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/proposed_registry_entry.json`
- `publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/reviewer_decision_form.json`
- `publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/validate_package.py`
- `publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/test_validate_package.py`
- `publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/validation_report.json`

For context only, the recorded Stage 2.3 software report contains 58 Stage 1 passes plus one skipped symlink fixture, and 120 Stage 2 passes including 28 retrospective regressions: 178 passes and one skip across 179 cases. Those are prior recorded results, not a Stage 2.4 rerun. The Stage 2.1 report separately retains its earlier native-probe error and successful final recheck. No prior validation record is overwritten.

The Stage 2.4 task must leave the 185 staged additions, their current working contents, unrelated working changes, protected historical research, frozen manifests and installed empty registry unchanged. No reset, clean, staging, commit, merge, push, real-data model fit or research experiment is authorized by this package.
