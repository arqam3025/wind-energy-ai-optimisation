# Publication V2 Stage 2.7: controlled local commits

Date: 2026-11-10. Commit construction and verification completed at
2026-11-10T16:05:18.945376+00:00.

Status: **48 Publication V2 paths added in three verified local commits. No push.**
Real-data admission remains **PENDING_REVIEW** and the installed registry is empty.
**BLOCKED_CONFIRMATORY_TEST** remains in force. No real-data experiment or model
training was performed.

## Local branch and commit identities

The new, un-checked-out local branch is
`research/publication-v2-stage27-review`. The active source branch remains
`research/publication-v2`, with HEAD unchanged at
`9517ec8bc0caac82774c32409287f449f5ce7923`.

Moving the active branch would change how its preserved index is interpreted.
Creating a separate review ref permits inspection of the scoped commits while
preserving both the original index bytes and its original staged differences.
No checkout, reset, restore, clean, blanket staging, merge or rebase was used.

| Commit | Added paths | Message |
| --- | ---: | --- |
| `aae8fe59a5cd25134a5a5cd483445217c3836f84` | 38 | Add development forecasting and causal uncertainty contracts |
| `49ab53424024f56609c0a8a02bfc286ca34b06de` | 7 | Add pending SCADA provenance and admission review package |
| `c5d355bac5fdd9fd0d34ef502683fb439f38c36e` | 3 | Document publication readiness and backup verification |

Parent chain: original HEAD, then the three commits in table order. Their trees,
respectively, are:

```text
88765790a6eb9a344c790156dbb293404a1e59c6
abf19201fd30fddf55faa095e470e90335a3c2fe
d841ac18f39d04acb726e52848d97564093130ed
```

The 48 paths are additions relative to the inherited base tree. The commits also
inherit all existing base-tree content unchanged; this is not a new repository
containing only 48 files.

## Exact file membership

Commit 1, 38 paths:

```text
docs/PUBLICATION_V2_RETROSPECTIVE_PROTOCOL_REVIEW.md
docs/PUBLICATION_V2_STAGE2_METHODS.md
docs/PUBLICATION_V2_STAGE2_VALIDATION.md
docs/PUBLICATION_V2_STAGE3_MPC_SPEC.md
publication_v2/stage2/.gitignore
publication_v2/stage2/__init__.py
publication_v2/stage2/config.json
publication_v2/stage2/conformal.py
publication_v2/stage2/data.py
publication_v2/stage2/environment.py
publication_v2/stage2/forecasting.py
publication_v2/stage2/lineage.py
publication_v2/stage2/metrics.py
publication_v2/stage2/plots.py
publication_v2/stage2/preservation_baseline.json
publication_v2/stage2/provenance_policy.json
publication_v2/stage2/requirements.txt
publication_v2/stage2/runner.py
publication_v2/stage2/study.py
publication_v2/stage2/tests/__init__.py
publication_v2/stage2/tests/fixtures.py
publication_v2/stage2/tests/test_conformal.py
publication_v2/stage2/tests/test_data.py
publication_v2/stage2/tests/test_environment.py
publication_v2/stage2/tests/test_forecasting.py
publication_v2/stage2/tests/test_lineage.py
publication_v2/stage2/tests/test_metrics.py
publication_v2/stage2/tests/test_retrospective.py
publication_v2/stage2/tests/test_workflow.py
publication_v2/stage2/validation/environment_constraints.txt
publication_v2/stage2/validation/environment_manifest.json
publication_v2/stage2/validation/preservation_verification.json
publication_v2/stage2/validation/stage21_stage1_tests.log
publication_v2/stage2/validation/stage21_stage2_test_summary.json
publication_v2/stage2/validation/stage21_stage2_test_summary_final.json
publication_v2/stage2/validation/stage21_stage2_tests.log
publication_v2/stage2/validation/stage21_stage2_tests_final.log
publication_v2/stage2/workflow.py
```

Commit 2, seven paths:

```text
docs/PUBLICATION_V2_REAL_DATA_PROVENANCE_REVIEW.md
publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/evidence_register.json
publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/proposed_registry_entry.json
publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/reviewer_decision_form.json
publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/test_validate_package.py
publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/validate_package.py
publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/validation_report.json
```

Commit 3, three paths:

```text
docs/PUBLICATION_V2_STAGE25_READINESS.md
docs/PUBLICATION_V2_STAGE26_BACKUP_VERIFICATION.md
docs/PUBLICATION_V2_STAGE261_BACKUP_VERIFICATION.md
```

The original 46-path plan is preserved, expanded only by the Stage 2.6 and 2.6.1
reports. Neither newer report was excluded: both are relevant local custody
records, including the failed-backup history and subsequent verified recovery.
All 45 working-file hashes recorded in the original A/B plan matched before
construction. All 48 final committed blobs match current working bytes.

## Exclusions and publication inspection

The 164 unrelated staged paths were excluded. Their exact file list and original
categorisation remain in Appendix B of
[the Stage 2.5 report](PUBLICATION_V2_STAGE25_READINESS.md): dashboard (27),
historical audits/backups (38), historical research/scripts/docs/results/tests
(96), historical documentation backups (2), and one older Stage 1 log.
No dataset, trained model, original result or frozen controller was newly added
by these scoped commits. No proposed path overlaps the protected baseline.

A separate read-only review found no actual credentials in the 48 selected files:
private-key, token, authentication URL and signed-secret scans identified no
credential material. An intentional fake signed-URL test fixture remains.
This review does not certify the inherited repository history for public release.

Eight selected files contain actual machine-specific absolute paths:

```text
docs/PUBLICATION_V2_RETROSPECTIVE_PROTOCOL_REVIEW.md
docs/PUBLICATION_V2_REAL_DATA_PROVENANCE_REVIEW.md
docs/PUBLICATION_V2_STAGE25_READINESS.md
docs/PUBLICATION_V2_STAGE26_BACKUP_VERIFICATION.md
docs/PUBLICATION_V2_STAGE261_BACKUP_VERIFICATION.md
publication_v2/stage2/validation/environment_manifest.json
publication_v2/stage2/validation/stage21_stage1_tests.log
publication_v2/stage2/validation/stage21_stage2_tests.log
```

These paths were retained as local audit evidence. Public disclosure must be
reviewed before any push. No existing hash-bound record was redacted or rewritten.
No keys, credentials or token values are included in this report.

## Construction and preservation evidence

Private construction evidence is retained at
`C:\ResearchCommits\w27_745f8d62bc`. It includes the separate index and object
store, exact membership and source inventories, validated tree previews, commit
identities, a scoped object pack and `SUCCESS.json`.

Raw working bytes were hashed without Git filters and inserted into the private
index with explicit paths and modes. All three candidate trees were checked in
full against the inherited base plus their exact additions before any commit
object was created. The verified object closure was imported into the source
object database, its connectivity and every selected blob were checked, and an
atomic new-ref creation made the commits reachable. No alternate-object
configuration was installed in the source repository.

An independent post-construction read-only review confirmed all three memberships
(38/7/3), all 48 raw blob hashes, the original HEAD, original index hash and 185
staged paths, with zero mismatches.

| Check | Actual result |
| --- | --- |
| Original index SHA256, before and after | `131c0b2e149ec81feb7cadcdeeb5115bd25b73b71abacc950a15a5424a711809` |
| Original `.git/HEAD` SHA256, unchanged | `2d22973b66d9bca05d112909e85fc4d9341952ad1faf5969c8ea5338c8eaf5d1` |
| Original `.git/config` SHA256, unchanged | `43b40651e1dccdd9a571fe49c1a8e531ef9126623d47f53c64c521e8914defad` |
| Source branch and HEAD | Unchanged |
| Existing staged paths | All 185 retained byte-identically in the original index |
| Existing non-Git working files | All 26,605 retained with identical bytes and alternate-stream inventories |
| Stage 1 preservation baseline | 2,131 files pass |
| Stage 2 preservation baseline | 2,170 files pass |
| Frozen references | All 59 pass |
| Frozen manifest SHA256 | `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a` |
| Final scoped trees and blobs | Exact membership/content; zero mismatches |

The full source inventory was compared with the verified backup source ledger
plus the separately verified Stage 2.6.1 report addendum. Subsequent guards
rechecked the working bytes and alternate streams throughout construction. New
Git objects, the new review ref and its reflog are the intended Git metadata
additions. Existing index, HEAD and configuration bytes were not changed.
This new report is the only project working-file addition from Stage 2.7; it was
created after construction and is intentionally outside the 48 committed paths.

The ten older staged Stage 2 versions remain intact. Their corrected working
versions were used for the scoped commits, including conformal, data,
forecasting, metrics, workflow and the five affected test/fixture files. No
newline normalization was applied, despite the source `core.autocrlf=true`.

## Backup status

The verified private backup remains available at
`C:\ResearchBackups\w261_1c75083b1d`; its recovery rehearsal is recorded at
`C:\Users\arqam\AppData\Local\Temp\w261r_1c75083b1d`.

Stage 2.7 rechecked availability, success markers, zero-exception backup and
recovery reports, and the hashes of the three canonical manifests. Each manifest
hashes to
`9436384c35733b7e65be285092dbe35b572648f1e79aa168b5ee17a0c9739802`.
The recorded verified snapshot covers 27,261 files and 1,067,822,121 default-stream
bytes, including Git metadata. Its success status is
`VERIFIED_AND_RECOVERY_REHEARSED`, with zero mismatches. The later Stage 2.6.1
report is covered by its verified addendum.

This is revalidation of the recorded backup/recovery evidence and the current
source against its ledger, not a claim that Stage 2.7 repeated the entire backup
or recovery operation. Neither the verified backup nor earlier snapshots were
overwritten. The three new commit objects and pack are also retained privately
in the separate construction directory.

## Fresh non-experimental validation

These counts were executed during Stage 2.7, separately from earlier results:

| Suite | Run | Passed | Failed/errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Stage 1 tests | 59 | 58 | 0 | 1 |
| Stage 2 data, lineage, retrospective, conformal and metrics tests | 84 | 84 | 0 | 0 |
| Stage 2.4 review-package tests | 20 | 20 | 0 | 0 |
| Total | 163 | 162 | 0 | 1 |

The skipped test requires Windows symlink-creation privileges, unavailable to
this account. Native forecasting/model-fitting and training integration suites
were not rerun in this task. Thus the earlier Stage 2.5 report of 198 passing
tests is historical evidence, not the fresh Stage 2.7 total.

Fresh logs and machine-readable summaries are retained in
`C:\Users\arqam\AppData\Local\Temp\wind_stage27_2tlwsgp2` as
`stage1_tests.log`, `stage1_summary.json`, `nonfit_stage2.log`,
`nonfit_stage2_summary.json`, `package_tests.log` and `package_summary.json`.
All test outputs used temporary locations; no historical results were overwritten.
No efficacy, coverage improvement or independent validation is inferred.

## Remaining work and next milestone

The source branch still shows its original 185 staged additions (175 `A ` and
10 `AM`). Its original 27 untracked paths remain present; adding this report
makes 28. Of the 185 staged paths, 21 are now also secured by corrected blobs on
the separate review branch and 164 are excluded. All 27 previously untracked
paths are included on that review branch. Their source status remains unchanged
because the source branch and index have deliberately not moved. The new report
remains untracked and is not a fourth commit.

Scoped code commits do not make a clean clone fully reproducible: 1,937 protected
paths, all 59 frozen references and all seven saved historical models are absent
from the inherited source HEAD. They remain preserved locally and privately
backed up. Distribution requires an appropriate artifact bundle and rights
review; these commits do not grant dataset redistribution rights.

The real-data admission registry remains empty, the proposed Berker Isen T1
entry is unapproved and **PENDING_REVIEW**, and
**BLOCKED_CONFIRMATORY_TEST** remains unchanged. Independent provenance,
source-rights, transformation, timestamp/availability, assumed-latency and
exclusion-policy review is still required before retrospective real-data work.
Historically inspected observations cannot be relabelled as untouched
confirmation. The archived negative uncontrolled-wind comparison and all
historical results remain unchanged.

The next milestone is owner review of the local commit diff and machine-path
disclosures, followed by explicit approval for any remote publication. Read-only
inspection is available without changing checkout or index:

```text
git log --oneline research/publication-v2..research/publication-v2-stage27-review
git diff --stat research/publication-v2...research/publication-v2-stage27-review
```

After Git review, obtain an independent admission decision before scheduling
development-only experiments. No push, dataset admission or further research
execution is authorized by this report. Stage 2.7 stops here pending approval.
