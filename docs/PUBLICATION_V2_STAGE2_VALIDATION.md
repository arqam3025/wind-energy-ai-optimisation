# Stage 2.1 scientific validity corrections

Validation date: 4 November 2026. Branch: `research/publication-v2`; starting HEAD: `9517ec8`. This is a correction and software-validation task, not a research experiment. **`BLOCKED_CONFIRMATORY_TEST` remains in force. Real development experiments must not proceed with the currently supplied evidence.**

## Existing work and Git preservation

Initial inspection found 185 staged additions, no unstaged tracked changes, and 21 staged Stage 2 code/documentation paths mixed with 164 other additions. Relevant Stage 2 files were absent from HEAD and their working copies matched the staged blobs before editing. Corrections were applied only to the working tree; the original staged versions remain available for review.

The original index digest was `131c0b2e149ec81feb7cadcdeeb5115bd25b73b71abacc950a15a5424a711809`. No reset, clean, restore, unstage, staging, commit, merge or push command was used. Protected source, raw/processed data, models, calibration, manifests, original results, Stage 1 files and unrelated staged work were preserved.

## Corrections

### Source identity, transformation and trust

`stage2/lineage.py` requires a versioned transformation manifest binding separate upstream and canonical artifacts, their byte hashes, stable provider/dataset/release/observation-namespace identities, source observation IDs and a closed transformation implementation identified by its own hash. The implementation re-executes an explicit one-to-one column map, parses offset-aware event/receipt timestamps and finite measurements, and compares complete normalized observations. It rejects missing/extra CSV cells, duplicate headers, duplicate timestamps/observation IDs, unsupported transformations and lineage mismatches. Numeric spelling, quoting, newline serialization and row order do not change the normalized observation identity.

**Verified transformation is not verified scientific provenance.** The separate `provenance_policy.json` contains an empty real-data review registry. A dataset's `ATTESTED` flag, self-authored evidence file or matching checksum cannot populate that registry or authorize a fit. A future real-data entry must follow independently checked acquisition, rights, clock, availability, feature-recipe, transformation and authorized-period evidence. It pins the source identity, lineage/cohort manifests, scientific provenance object, full dataset document and review-document identity. The validity/authority of the external review must be established outside the hashing code; no review or custody evidence has been invented here.

The supported converter deliberately does not invent a timezone or measurement latency for the old naive SCADA table. Other conversions or repairs require a separately implemented, reviewed transformation identity; arbitrary user-supplied transformation code is not executed.

### Historical exposure and authorized observations

The former single-raw-hash exclusion is replaced by source/namespace identity, normalized observation identity/content, upstream lineage and role-specific authorized source periods. A protected historical observation registry also detects matching historical measurements or unresolved identity collisions despite changed CSV bytes, row order or a new claimed source name. Its opaque-clock evaluation boundary is checked against the preserved schedule rather than silently assuming an unrelated configurable date.

Known matches and collisions are conservatively classified as exposed or unresolved; absence of a match is explicitly **not evidence of an untouched observation**. Included feature support and all targets must lie within the independently authorized period for their role. Historically evaluated observations, and unresolved matches to them, cannot enter the new development cohort through a re-export. Confirmation remains unsupported for every completion status.

Exact normalized values identify unchanged observations under serialization/reordering; they are not a universal identity oracle for altered/rounded measurements or another site. Stable provider observation IDs and independently reviewed lineage remain required. Ambiguous signal collisions are rejected for review rather than silently declared new.

### Missing data, gaps and cohort denominators

A hashed, prespecified cohort policy is mandatory. It declares the expected measurement coverage (including leading/trailing slots), role candidate windows, authorized periods, no-imputation/duplicate/missing-cell rules, declared missing slots and individual origin exclusions. The declared policy precedes the candidate origins; real admission additionally requires its independently reviewed identity.

The audit accounts for expected/observed measurement slots, timestamp gaps, candidate/provided/accepted/excluded origins, missing feature and target support, and timestamp-specific rejection reasons. Every ten-minute candidate inside each role window must be included or have a fact-verified missing-support exclusion. Arbitrary error-based exclusions, unaccounted edge truncation, undeclared gaps and silent omission fail. Failed admission records retain the available rejection report; successful software workflows save an authenticated `admission_report.json` before fitting. Declared partition windows remain subject to Stage 1 strict embargo and all-horizon overlap checks.

### Interval fairness and metadata

Interval scoring now rejects unequal nominal alpha across complete methods or models by default. Unequal-alpha analysis requires an explicit nonempty named `sensitivity_experiment`; outputs preserve the levels and identify an alpha-sensitivity analysis rather than a fair fixed-alpha method comparison. A model/method/horizon group still cannot pool different nominal levels.

Calibration validates every supplied candidate's issuance, origin, target, observation/residual receipt, model training/availability, horizon, hash and grid metadata in a first pass—even future, other-model and other-horizon records. Only then does eligibility filtering apply `target_time < decision_time` and the availability rules. This pass does not inspect unavailable prediction/observation values. Well-formed unavailable candidates may be excluded; malformed evidence cannot disappear through filtering.

### Environment and native configuration

The new environment manifest captures full Python implementation/build/compiler/executable hashes; OS, architecture and CPU information; all installed distributions; direct requirement checks; installed native binary hashes; isolated actual library/solver versions; threadpool-runtime identities; and explicitly unavailable evidence. The installed environment contains 68 distributions and 634 native/static binary entries. The full installed-version constraints are included in the validation evidence.

This is an exact-machine fingerprint, not a portable wheel/container lock, verified OS-transitive dependency closure or completed clean-environment installation. Unknown native versions remain unknown. Required unavailable/mismatched evidence fails validation and prevents a completion marker. Probe errors are retained; no timeout or unavailable-version fallback was relaxed.

LightGBM now enables effective row sampling when `subsample < 1` (default frequency one), retains frequency zero for full sampling, and rejects contradictory/unsupported frequencies. Saved metadata distinguishes requested overrides, resolved inputs and actual native `bagging_fraction`/`bagging_freq`. Native save/reload regressions verify these fields while retaining seed/thread/objective restrictions.

## Test evidence and execution limits

All fits performed for this task belong to explicitly synthetic software fixtures in temporary output directories. There was no real-data model training, forecast experiment, calibration comparison, MPC execution, performance claim or new research result. The repeated synthetic end-to-end test exercises model saving, interval sealing, native hash reproducibility and tamper rejection; it is not development evidence about wind performance.

Stage 1: **59 tests run, 58 passed, 0 failed/errors, 1 skipped**. The skip is the Windows account's unavailable native symlink-creation privilege; privilege-free symlink/junction rejection tests pass. Stage 1 was tested with site-packages disabled (`-S`).

The initial full Stage 2.1 run had **92 tests run, 91 passed, 0 assertion failures, 1 error, 0 skipped**. Its synthetic end-to-end run was refused at the final environment check because native-runtime probe evidence was unavailable. That failure log is preserved. A fresh standalone isolated probe subsequently succeeded; the earlier failure's precise native cause was not retained by the old generic exception and is not inferred here. The error message now identifies recorded probe failure details without weakening fail-closed behaviour. A complete recheck is recorded separately below and in the final summary file.

Evidence files under `publication_v2/stage2/validation/` retain the first failure, final test run, Stage 1 run, environment manifest/constraints and preservation verification. They are software-validation records, not experimental forecasting results.

Final full recheck: **92 Stage 2 tests passed, 0 failed, 0 errors, 0 skipped** in 318.736 seconds. This includes both repeated synthetic workflows, native model reload/hash checks, plots and the strict post-run environment checks. Combined final coverage is **150 passed and one skipped across 151 Stage 1/Stage 2 cases**. The earlier 91-pass/one-error run is retained and is not presented as a successful run. The native-probe failure remains a reason to refuse any future completion if evidence is unavailable; a successful recheck does not establish an operational latency guarantee.

Commands used from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:GIT_OPTIONAL_LOCKS = '0'
.venv/Scripts/python.exe -S -B -m unittest discover -s publication_v2/tests -v
.venv/Scripts/python.exe -B -m unittest discover -s publication_v2/stage2/tests -v
```

Regression cases include altered CSV serialization, source reordering/aliases, duplicate observations/headers, lineage/implementation mismatch, self-attestation, modified reviewed metadata, absent/misdeclared exclusions, missing edge/target support, unauthorized periods, invalid future/excluded timestamps, unequal whole-method alpha, named sensitivity and native LightGBM sampling. Environment fixtures cover missing, changed or unsupported dependencies and native evidence.

## Preservation and scientific recommendation

The current preservation verifier checks all **2,170 protected original/Stage 1 files** and all **59 freeze references**. The frozen manifest remains `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a`. A separate 2,179-file fingerprint covers protected and unrelated staged work. The validation evidence records its before/after equality and the unchanged Git index.

The archived negative comparison remains context: uncontrolled wind had 1,465 violations, adaptive MPC 1,486 and fixed-margin MPC 1,502; original summed exceedance also favoured uncontrolled wind. None of those research results was changed.

**Recommendation: do not proceed with real development experiments yet.** The real-data review registry is empty. Source release/acquisition, clock/window meaning, measurement/feature/residual availability, rights and authorized cohort evidence are still unresolved. No untouched-data custody evidence has been established. Software tests can continue; a real study requires reviewed evidence, approved trust-policy entries, reproducible transformation, prespecified cohort policy and a healthy recorded environment. `BLOCKED_CONFIRMATORY_TEST` remains regardless of later development admission.

The original mixed index is retained. Corrections and new validation files are working-tree changes awaiting the user's review and approval; no Git publication action is authorized by this report.

## Exact task change list

Modified working-tree copies of existing staged additions (the index versions are unchanged):

- `publication_v2/stage2/conformal.py`
- `publication_v2/stage2/data.py`
- `publication_v2/stage2/forecasting.py`
- `publication_v2/stage2/metrics.py`
- `publication_v2/stage2/workflow.py`
- `publication_v2/stage2/tests/fixtures.py`
- `publication_v2/stage2/tests/test_conformal.py`
- `publication_v2/stage2/tests/test_data.py`
- `publication_v2/stage2/tests/test_forecasting.py`
- `publication_v2/stage2/tests/test_metrics.py`

New implementation, test and documentation files:

- `publication_v2/stage2/environment.py`
- `publication_v2/stage2/lineage.py`
- `publication_v2/stage2/provenance_policy.json`
- `publication_v2/stage2/tests/test_environment.py`
- `publication_v2/stage2/tests/test_lineage.py`
- `docs/PUBLICATION_V2_STAGE2_VALIDATION.md`

New validation evidence files (no research observations or forecasting results):

- `publication_v2/stage2/validation/environment_constraints.txt`
- `publication_v2/stage2/validation/environment_manifest.json`
- `publication_v2/stage2/validation/preservation_verification.json`
- `publication_v2/stage2/validation/stage21_stage1_tests.log`
- `publication_v2/stage2/validation/stage21_stage2_test_summary.json`
- `publication_v2/stage2/validation/stage21_stage2_test_summary_final.json`
- `publication_v2/stage2/validation/stage21_stage2_tests.log`
- `publication_v2/stage2/validation/stage21_stage2_tests_final.log`
