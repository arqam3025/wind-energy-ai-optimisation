# Publication V2 Stage 2.8: publication safety and push readiness

Date: 2026-11-10. Scope: the three Stage 2.7 commits, their complete reachable
history, portability, scientific representations and preservation of the original
working state. This report contains repository-relative paths and evidence
identifiers; personal machine paths and contact details are deliberately omitted.

## Decision

**Push readiness: READY_WITH_RESTRICTIONS — for a code-and-audit release only.**

No high-confidence credentials were detected. The three commits faithfully
capture the intended corrected versions. They are suitable for owner review,
but this assessment does not authorize a push, certify clean-clone reproduction,
admit real data or establish independent scientific validation.

Before public publication:

1. The owner must explicitly accept the disclosed machine layout, username paths
   and normal Git author identity, or approve a separately constructed sanitized
   history. Neither acceptance nor history rewriting is inferred by this audit.
2. The public release description must state that this is development-only code
   and archival validation, with missing private inputs and an unverified clean
   installation. It must not advertise a fully reproducible independent study.
3. Correct or explicitly flag the methods' target-label ambiguity: the code uses
   nonnegative measured generation, not established unconstrained available wind.
4. Obtain explicit push approval after reviewing the exact publication branch.

If the intended requirement is **no personal machine paths anywhere in public
history**, the present branch is **BLOCKED for that requirement** until an
approved reconstruction. An ordinary follow-up redaction commit is insufficient.

**PENDING_REVIEW** and **BLOCKED_CONFIRMATORY_TEST** remain unchanged. The installed
real-data registry is empty. Full research reproduction and real-data experiments
remain blocked independently of whether code is published.

## Sensitive-information scope and findings

All 48 added paths and their committed content were inspected. Each is an
addition in its respective commit; none has an earlier intermediate version
within these three commits. The reachable-history scan covered **12 commits,
380 Git objects and 306 unique blobs**, including earlier versions rather than
only the final tree.

No high-confidence private key, access token, credential, JWT, bearer credential
or authenticated-URL secret was detected. A deliberately fake signed-URL fixture
is software test material. There is one author name/email identity in metadata
across the 12 commits; its values are not reproduced here. Normal authorship is
intentional Git metadata, but the owner should accept its public disclosure.
Public dataset-provider attribution and bibliographic names are not secret
research-subject identifiers and should retain their legitimate attribution.

The 48 additions contain no raw SCADA CSV, turbine archive, trained model binary
or real-data experiment payload. Synthetic fixtures are explicitly labelled.
The final tree has 281 paths, including 15 inherited summary/inventory CSVs; those
are distinguishable from a newly admitted raw dataset. No confidential provider
contract or private participant record was identified in scope.

Negative pattern scans do not prove the absence of every possible secret.
Binary historical figures were not certified by forensic image/document review;
encrypted, image-embedded or unrecognized secrets cannot be ruled out by text
patterns. No remote service, credential validity check or GitHub push was used.

## Eight-file machine-path disclosure review

Line references below refer to the immutable blobs at
`c5d355bac5fdd9fd0d34ef502683fb439f38c36e`, not a redacted working version.

Classification: **H** harmless explanatory/diagnostic content; **P** privacy
disclosure of a user or local layout; **M** machine-specific reference or
fingerprint; **R** reproducibility limitation. Categories can coexist. A path
being useful evidence does not make it free of privacy implications.

| Committed file | Exact locations and occurrences | Classification and implication |
| --- | --- | --- |
| `docs/PUBLICATION_V2_RETROSPECTIVE_PROTOCOL_REVIEW.md` | L140: 1 | P/R. A temporary evidence location; not a durable public reproduction reference. |
| `publication_v2/stage2/validation/environment_manifest.json` | 721 scalar path values; complete field/line catalogue below | P/M; R when treated as portable. Captured interpreter, package and native-library locations, rather than hardcoded forecast inputs. |
| `publication_v2/stage2/validation/stage21_stage1_tests.log` | L49: 2 escaped temporary paths | H/P. Windows symlink-fixture diagnostic; no runtime input dependency. |
| `publication_v2/stage2/validation/stage21_stage2_tests.log` | L98, 101, 104, 107, 109, 111: 1 each | H/P. Archived traceback paths; no runtime input dependency. |
| `docs/PUBLICATION_V2_REAL_DATA_PROVENANCE_REVIEW.md` | L177: 1 | P/R. Temporary local evidence reference; public readers cannot resolve it. |
| `docs/PUBLICATION_V2_STAGE25_READINESS.md` | L176: 1; L586: 1 | L176 H/P/M: machine-specific command example. L586 P/R: private temporary evidence. |
| `docs/PUBLICATION_V2_STAGE26_BACKUP_VERIFICATION.md` | L12: 1 | P/M. Private backup location; useful custody context, not a public dependency. |
| `docs/PUBLICATION_V2_STAGE261_BACKUP_VERIFICATION.md` | L20: 1; L21: 1 | L20 P/M: backup layout, without a username. L21 P/M: recovery location containing a user path. Neither is an experiment input. |

**Total: 736 real machine-path occurrences in eight scoped files.** Generic
Windows command syntax, URLs, a synthetic outside-path test and an environment
variable placeholder are excluded from this count.

Every environment-manifest occurrence is accounted for by the following exact
catalogue. Ranges expressed with a step include both endpoints. All rows classify
each listed occurrence as P/M; the final column distinguishes portability effects.

| JSON field family | Exact line set | Count | Portability interpretation |
| --- | --- | ---: | --- |
| `direct_requirements.path` | 42 | 1 | Installation pointer; requirements content is separately hashed. |
| `installed_distributions[*].location` | 50 through 519, step 7 | 68 | Locations of installed distributions; private environment fingerprint. |
| `native_distribution_artifacts[*].path` | 528 through 5592, step 8 | 634 | Locations of native binary artifacts. Hashes authenticate that machine's binaries; they do not supply a portable installation. |
| `native_runtime.modules.*.module_file` | 5602 through 5656, step 6 | 10 | Module locations recorded from the current runtime, not required original-directory literals. |
| `native_runtime.threadpools.libraries[*].filepath` | 5676, 5688, 5700, 5711 | 4 | Native runtime fingerprint; exact historic environment verification is machine-sensitive. |
| `python.base_executable` | 5737 | 1 | Interpreter location; not a launch requirement for another checkout. |
| `python.executable` | 5745 | 1 | Virtual-environment interpreter location. |
| `python.executable_sha256[*].path` | 5748, 5753 | 2 | Interpreter-hash source locations. |
| Total | | 721 | |

The full reachable history also contains two inherited disclosure files:

- `publication_v2/evidence/exposure_and_provenance.json`, L561;
- `publication_v2/evidence/stage1_tests_stdlib_final.log`, L49.

These are already inherited from the base at `9517ec8...`; they are not extra
Stage 2.7 additions. Rebuilding only the three new commits would leave these two
files reachable. Remote state was not queried; a local remote-tracking ref is not
proof of current server state. Already published copies, if any, would remain
separately accessible even after a new sanitized branch was created.

## Reproducibility and scientific integrity

### Paths and runtime portability

No executable Stage 2 runtime requires the original personal Windows directory.
`workflow.py:20–21` derives the implementation root from its module location.
`runner.py:12` accepts a dataset argument, and `data.py:72–76` resolves it within
the declared workspace. Evidence references are relative and constrained against
escaping that workspace. This is deliberate path confinement, not a requirement
for the original drive or username.

`environment.py:161–199` captures the current environment afresh. The archived
manifest with 721 paths is not loaded as a hardcoded startup installation.
However, `workflow.py:267–268` compares a recorded environment with the current
capture exactly. Consequently, the existing historical `verify_run` does not
provide a portable artifact-only verification mode after relocation or on another
machine. Keep exact authentication intact; any portable verifier should be a
separate operation with an explicitly narrower claim.

Windows `.venv/Scripts/python.exe` examples need equivalent `python`/POSIX
instructions. A new path-neutral public guide is preferable to silently editing
the original audit records.

### Dependencies and a concrete clean-export probe

`publication_v2/stage2/requirements.txt:2–7` pins six direct dependencies:
NumPy, SciPy, scikit-learn, XGBoost, LightGBM and Matplotlib. The captured
constraints record 68 installed distributions, and the manifest records Python,
OS and native libraries. This is an environment inventory, not a validated
cross-platform hash lock or independently tested clean installation.
`environment.py:193–199` explicitly says clean-environment reproduction was not
executed. Package-index availability, dependency resolution and an installation
in a new OS/container were not tested in Stage 2.8.

A non-experimental probe exported the committed tree into an isolated temporary
directory: **281 files, 2,170 expected protected paths, 1,937 protected paths
missing**. Calling the preservation validator there produced the expected
fail-closed missing-artifact rejection. No model was fitted and no data were
admitted. This demonstrates a clean-clone input blocker; it is not a model test
failure or successful full-suite reproduction.

`workflow.py:33–35,93` requires the protected artifacts and frozen manifest.
`lineage.py:84–98,202` reads the historical raw source and schedule to identify
exposure even for synthetic admission fixtures. Thus some nominally synthetic
Stage 2 integration tests currently depend on private historical files.
Stage 2.4 live validation also needs preserved evidence/model artifacts
(`admission_reviews/berker_isen_t1_stage24/validate_package.py:228–236`).
Documentation-only tests must be distinguished from live package validation.

All 59 frozen references and seven historical saved models are absent from the
inherited HEAD and unchanged by these commits. A public checkout therefore does
not provide full historical or Stage 2 research reproduction. Do not fill this
gap by automatically publishing protected SCADA data or bypassing exposure and
preservation gates. A rights-governed artifact inventory, acquisition procedure
and independent environment reproduction are needed.

### Scientific claims and chronology

The installed registry remains `{}`. The proposed T1 entry has `approved=false`
and `status=PENDING_REVIEW`; it is not an admission decision. No new real-data
Stage 2 comparison, coverage result or independent validation is established by
these commits. Older test logs and summaries are software evidence, not
scientific outcomes. Historically inspected cohorts remain retrospective.

Reviewed boundaries include complete feature and receipt metadata validation,
training-label cutoffs and cross-split rules (`data.py:128–180`), and
metadata-first, horizon-specific calibration validation (`conformal.py:182–215`).
Calibration still requires **target time strictly before decision time**, plus
available observations/residuals; equal-time and future labels are rejected.
These code-level guards do not independently authenticate historical timing.
Unapproved source rights, availability, lineage, exclusions and custody remain
real experiment blockers.

The uncertainty text appropriately limits weighted/rolling calibration claims
under chronological dependence. Horizonwise empirical coverage is not asserted
to guarantee conditional, simultaneous or operational coverage. No improved
accuracy, coverage or controller efficacy is claimed. The archived negative
uncontrolled-wind finding and original results remain preserved.

One scientific terminology defect needs correction:
`docs/PUBLICATION_V2_STAGE2_METHODS.md:11` says **available wind power**, whereas
`data.py:115–116,165–168` and `forecasting.py:272` implement nonnegative **measured
generation**, `max(0, raw_power_kw)`. SCADA measurements do not establish
unconstrained potential under outages or curtailment. Stage 2.5 already flags
this ambiguity at L288. Correct the label in a versioned public methods text;
do not change measurements, algorithms or historical results to match the label.

## Git integrity and preservation

| Commit | Added files | Verified tree |
| --- | ---: | --- |
| `aae8fe59a5cd25134a5a5cd483445217c3836f84` | 38 | `88765790a6eb9a344c790156dbb293404a1e59c6` |
| `49ab53424024f56609c0a8a02bfc286ca34b06de` | 7 | `abf19201fd30fddf55faa095e470e90335a3c2fe` |
| `c5d355bac5fdd9fd0d34ef502683fb439f38c36e` | 3 | `d841ac18f39d04acb726e52848d97564093130ed` |

Exact membership matches the Stage 2.5 Commit A/B tables (38/7) and Commit C's
Stage 2.5 report plus the Stage 2.6 and Stage 2.6.1 reports. No unexpected path
or protected artifact is added. **48 of 48 raw committed blobs match corrected
working copies; zero mismatches.** The ten older staged versions remain untouched.

The review branch is exactly three commits ahead of the original branch; its
merge-base is the original HEAD:
`9517ec8bc0caac82774c32409287f449f5ce7923`. The active branch remains
`research/publication-v2`; the review branch remains
`research/publication-v2-stage27-review`. No ref, commit or checkout was changed.

| Original-state check | Verified result |
| --- | --- |
| Raw index SHA256 | `131c0b2e149ec81feb7cadcdeeb5115bd25b73b71abacc950a15a5424a711809` |
| `.git/HEAD` SHA256 | `2d22973b66d9bca05d112909e85fc4d9341952ad1faf5969c8ea5338c8eaf5d1` |
| `.git/config` SHA256 | `43b40651e1dccdd9a571fe49c1a8e531ef9126623d47f53c64c521e8914defad` |
| Staged paths | 185; original 175 additions and 10 additions with later working changes |
| Existing non-Git working files before this report | 26,606; full byte/alternate-stream inventory matches the Stage 2.7 final state |
| Stage 1 protection | 2,131 files pass |
| Stage 2 protection | 2,170 files pass |
| Frozen references | 59 pass |
| Freeze manifest SHA256 | `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a` |

The only intended project-file addition in Stage 2.8 is this report, left
untracked. Existing 28 untracked paths remain; this report makes 29. No existing
staged entry, source file, dataset, model, manifest or result was modified.

### Stage 2.7 report disposition

Retain `docs/PUBLICATION_V2_STAGE27_COMMIT_REPORT.md` privately, unchanged. Its
construction, backup/recovery and temporary-log locations at L148, 194–195 and
229 need not be public. Its original SHA256 is
`07d3ea3ebbe7ce8057c0f6ba0696d8c35e2db1870180d164a18276a8b48e9e3e`.
It remains untracked and is absent from the review tree. A separately labelled
publication-safe derivative can be added later without rewriting these three
commits. Preserve commit identities, counts and verification facts; substitute
neutral private-evidence identifiers rather than imply that the derivative is
the original authentication record.

## Exact proposed correction plan — not executed

The privacy choices below are alternatives: accept disclosed historical paths,
or construct a sanitized publication history after approval. Do not edit originals
or rewrite already preserved evidence in place.

| File(s) | Type | Proposed action |
| --- | --- | --- |
| `publication_v2/stage2/validation/environment_manifest.json` | Privacy; portability of published metadata | Keep original privately. For a path-minimized release, derive a clearly labelled public capture with neutral root/evidence identifiers, retaining meaningful versions/hashes and explicitly disclaiming exact-runtime authentication of the derivative. |
| `publication_v2/stage2/validation/stage21_stage1_tests.log`; `publication_v2/stage2/validation/stage21_stage2_tests.log` | Privacy | Retain original logs privately. Derive path-redacted public transcripts while retaining failures, skips, counts and dates; label them derivatives. |
| `docs/PUBLICATION_V2_RETROSPECTIVE_PROTOCOL_REVIEW.md`; `docs/PUBLICATION_V2_REAL_DATA_PROVENANCE_REVIEW.md` | Privacy; durable evidence references | Derive public copies using private evidence identifiers at the tabled lines; preserve unresolved review status and source attribution. |
| `docs/PUBLICATION_V2_STAGE25_READINESS.md`; `docs/PUBLICATION_V2_STAGE26_BACKUP_VERIFICATION.md`; `docs/PUBLICATION_V2_STAGE261_BACKUP_VERIFICATION.md` | Privacy; custody history | Derive public custody summaries with neutral roots, preserving failed-backup history and verified counts. Clearly distinguish original-byte plans from public-derived hashes. |
| `publication_v2/evidence/exposure_and_provenance.json`; `publication_v2/evidence/stage1_tests_stdlib_final.log` | Inherited privacy disclosure, conditional on a path-free-history requirement | Include in any approved broader history/export plan; rebuilding only the new three commits cannot remove them. Preserve historical originals. |
| `docs/PUBLICATION_V2_STAGE2_METHODS.md` | Scientific clarity | Correct the measured-generation target wording in an approved version; leave actual data and target transformation unchanged. |
| New `docs/PUBLICATION_V2_PORTABLE_REPRODUCIBILITY.md`; public README link | Portability; honest release scope | Add platform-neutral install/launch/test commands, suite/input matrix, missing-artifact counts and explicit code-only/retrospective limitations. Distinguish unit tests, private-artifact integration checks and research experiments. |
| New `publication_v2/stage2/publication/artifact_requirements.json` | Scientific reproducibility | Metadata-only input inventory, evidence identifiers and rights-governed acquisition requirements. No SCADA data or automatic admission. |
| New `publication_v2/stage2/publication/redaction_manifest.json` | Privacy provenance | Map original Git object/SHA256 identities to public derivative identities and explain each transformation without publishing private path values. |
| `publication_v2/stage2/workflow.py`; new `publication_v2/stage2/tests/test_portable_verification.py` | Optional future portability improvement | After separate review, add artifact-only verification with a narrower claim; retain strict existing `verify_run` and all research gates. This is not necessary merely to archive the current code honestly. |
| `publication_v2/stage2/tests/fixtures.py`; `publication_v2/stage2/tests/test_lineage.py`; `publication_v2/stage2/tests/test_data.py`; `publication_v2/stage2/tests/test_workflow.py` | Optional future standalone test design | Review explicit synthetic registry/preservation injection confined to test fixtures. Do not silently disable production exposure checks or substitute invented provenance for real inputs. |
| `docs/PUBLICATION_V2_STAGE27_COMMIT_REPORT.md` | Private custody record | Retain original privately; optionally add a new public derivative such as `docs/PUBLICATION_V2_STAGE27_PUBLIC_SUMMARY.md`. |

The Stage 2.5 tables pin 45 original hashes. Sanitizing logs, manifests or docs
can invalidate those public byte-identity claims and downstream evidence
references. Any approved export must update derivative references consistently
and retain the original/private-to-public mapping. Do not claim a redacted
manifest or transcript is byte-identical to the authenticated original.

Git author identity is a separate owner decision: retaining normal attribution
requires no rewrite. If its historical contact details must be removed, changing
future Git settings alone cannot remove old commit metadata. That would require
an explicitly approved history plan, not a source-configuration edit here.

### History implications

- Accepting the existing disclosures and adding an honest portability/methods
  clarification can use ordinary future scoped commits; no rewrite is necessary.
- Removing the eight disclosures from reachable new history requires rebuilding
  the affected unpublished commits and their descendants on a separate approved
  branch. All three commit IDs would change. Keep the current review branch and
  original evidence intact.
- Removing the two inherited disclosures from that new branch also requires an
  approved change of ancestry or a curated history. Do not force-push or rewrite
  the original working branch or shared history. Existing external copies cannot
  be promised erased.

## Private preservation and validation evidence

The verified Stage 2.6.1 snapshot and earlier snapshots were not overwritten.
An append-only private addendum, evidence ID
**STAGE28-PRIVATE-EVIDENCE-7d8f61c2**, was created under the existing private backup
root, in relative directory `stage28_evidence_7d8f61c2`.

Its initial verification completed at 2026-11-10T20:30:47.875083+00:00:
**55 source files copied and hash-verified, plus one verified full-history Git
bundle: 56 verified payload files.** This includes all 48 original working/blob
versions, the original Stage 2.7 report and six Stage 2.7 private evidence files.
The bundle preserves reachable commit metadata and contents; `git bundle verify`
passed. `VERIFIED.json` records inventory and hashes separately. The original
index and HEAD were checked unchanged. No private backup or bundle was uploaded.

The full current working inventory, including alternate streams, was separately
rehashed against the Stage 2.7 final state and recorded privately. All 26,606
existing files matched before this report was written. Independent agent reviews
also verified commit membership, raw blobs, protected files and freeze references.

Stage 2.8 did not run model fits, research experiments or a full unit-test suite.
Its executed checks are history/content inspection, Git/blob verification,
preservation hashing, private-backup verification and the isolated clean-export
fail-closed probe. The Stage 2.7 **162 passed / 0 failed / 1 skipped** counts
remain historical test evidence and are not relabelled as fresh Stage 2.8 tests.

## Recommended next action

Choose between accepting the existing path/author disclosures for a restricted
code-and-audit release and approving a sanitized derivative branch. Approve the
exact file-level scope before any implementation or history reconstruction.
Review the final public diff, hash mapping and release limitations before issuing
a separate push instruction. Obtain independent provenance and admission review
before any retrospective real-data experiment; publication of code does not
resolve that gate or **BLOCKED_CONFIRMATORY_TEST**.

**Stopped after audit/report creation. No push, commit, amendment, history rewrite,
dataset admission or research execution was performed.**
