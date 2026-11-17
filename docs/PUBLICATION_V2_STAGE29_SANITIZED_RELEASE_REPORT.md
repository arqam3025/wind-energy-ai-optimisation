# Publication V2 Stage 2.9: sanitized release preparation

Date: 2026-11-10. Local branch construction and verification completed at
2026-11-10T20:53:30.069336+00:00.

**Decision: READY for the scoped code-and-synthetic-validation release, subject
to explicit push approval.** Full historical reproduction, real-data admission
and independent confirmation remain blocked. This is not journal-readiness or
efficacy certification.

## Created publication branch

```text
publication/v2-sanitized-stage29
commit 968773d8f2c85dd28ed5bd28ec873a231c2d3db5
tree   5d81c16fb68e3a75c6bbb6001250a0c5298ae351
```

The branch has exactly **one parentless root commit and 40 files**. Neither
existing research branch is an ancestor; there is no merge-base with either.
Original source identities appear only as audit identifiers in the new release
manifest, not as Git parents or inherited objects.

A clean history was necessary: changing tip files would retain the eight scoped
machine-path files and the two inherited evidence/log files in reachable history.
The original 12-commit history was re-reviewed: 306 unique blobs, no detected
high-confidence credentials, known eight scoped plus two inherited disclosure
files. No existing history was rewritten.

The existing source branch remains `research/publication-v2` at
`9517ec8bc0caac82774c32409287f449f5ce7923`. The existing review branch remains
`research/publication-v2-stage27-review` at
`c5d355bac5fdd9fd0d34ef502683fb439f38c36e`. Neither was checked out, moved or
rewritten to construct the new publication ref.

## Construction strategy and evidence custody

1. Verify the prior private backup/recovery evidence and current full working
   inventory, original index, branch identities and protected files.
2. Copy a curated software closure from committed objects into an isolated
   temporary repository. Keep production algorithms, policy and selected tests
   byte-identical. Generate new public documentation and neutral audit summaries.
3. Use explicit per-file blob insertion, no filters and byte-preserving Git
   attributes. Construct a root commit with no parent. Never stage through the
   source repository's index.
4. Validate the exact tree, manifest hashes, content/history privacy scan and
   clean-clone synthetic suites. Independent reviewers checked the final sealed
   commit, including metadata and README rendering.
5. Preserve a verified bundle and preparation evidence privately before importing
   the standalone objects and atomically creating only the new publication ref.
6. Recheck all original source bytes/alternate streams, protected artifacts,
   index and refs. Remove only the newly generated transfer archive after its
   private copy was hash-verified. No original file was removed.

The verified original snapshot and its recovery evidence remain available.
Original commits, personal-contact metadata, custody reports, raw environment
records and test transcripts remain privately preserved, including the full
original-history bundle from Stage 2.8.

New private evidence identifier: **STAGE29-PRIVATE-EVIDENCE-9b67c4d0**, relative
addendum directory `stage29_evidence_9b67c4d0` under the existing private backup.
It contains a hash-verified preparation archive, final standalone bundle,
membership/hash mapping, raw synthetic logs and preparation drafts. The sealed
bundle SHA256 is:

```text
1356fa23ce77fe78ba39c50e169363245d0e8812e627b91501d56368d3ea8130
```

`git bundle verify` passed before import. Original snapshots and prior addenda
were not overwritten. Earlier preparation drafts remain private; only the sealed
root named above was imported as the publication branch. This report itself is
new, stays untracked in the original working repository, and is outside the
40-file release.

## Exact publication membership

Thirty files are unchanged source/configuration/test bytes; ten are new public
documents, summaries or release policies. All files have explicit blob/hash
membership in `publication_v2/publication/release_manifest.json`. Its own hash
list excludes itself explicitly; the Git tree authenticates that file.

```text
.gitattributes
.gitignore
README.md
docs/DATA_GOVERNANCE.md
docs/METHODS.md
docs/RELEASE_AUDIT_SUMMARY.md
docs/REPRODUCIBILITY.md
publication_v2/__init__.py
publication_v2/integrity.py
publication_v2/inventory.py
publication_v2/metadata.json
publication_v2/protocol.py
publication_v2/publication/artifact_requirements.json
publication_v2/publication/release_manifest.json
publication_v2/publication/validation_summary.json
publication_v2/runner.py
publication_v2/stage2/__init__.py
publication_v2/stage2/config.json
publication_v2/stage2/conformal.py
publication_v2/stage2/data.py
publication_v2/stage2/environment.py
publication_v2/stage2/forecasting.py
publication_v2/stage2/lineage.py
publication_v2/stage2/metrics.py
publication_v2/stage2/plots.py
publication_v2/stage2/provenance_policy.json
publication_v2/stage2/requirements.txt
publication_v2/stage2/runner.py
publication_v2/stage2/study.py
publication_v2/stage2/tests/__init__.py
publication_v2/stage2/tests/test_conformal.py
publication_v2/stage2/tests/test_environment.py
publication_v2/stage2/tests/test_metrics.py
publication_v2/stage2/workflow.py
publication_v2/temporal_audit.py
publication_v2/tests/test_integrity.py
publication_v2/tests/test_inventory.py
publication_v2/tests/test_protocol.py
publication_v2/tests/test_runner.py
publication_v2/tests/test_temporal_audit.py
```

### Exclusions

The release manifest lists every excluded original source version and pathname.
Relative to the old 281-file review tree, **248 pathnames are absent and 251
original versions are not copied**. The difference is the new derived README,
`.gitattributes` and `.gitignore` at three existing pathnames.

Excluded material includes all original audit/custody reports, environment
captures, raw test logs, exposure inventories, preservation/freeze manifests,
historical figures/tables, historical controller scripts, dashboard and unrelated
work. No raw SCADA data, acquisition archive, saved model or original experiment
payload is included.

The original private-artifact `test_data`, `test_lineage`, `test_retrospective`
and `test_workflow` suites, and model-fitting `test_forecasting`, are preserved
privately and excluded from public default discovery. Their checks are not
claimed to have run in this clean release. Production runtime remains unchanged;
missing artifacts still fail closed.

Inspect exact included/excluded lists without changing checkout:

```text
git show publication/v2-sanitized-stage29:publication_v2/publication/release_manifest.json
```

## Sanitization and scientific terminology

The original eight scoped path-bearing files and both inherited evidence/log
files are absent, along with their ancestry. Original evidence was not edited,
redacted in place or represented as still byte-identical after transformation.
New public summaries replace the need to distribute those records. The source
mapping identifies unchanged source object/SHA256 identities; new documents are
explicitly labelled generated summaries or release policies.

The README and derived methods summary use **nonnegative measured electrical
generation**, `max(0, raw_power_kw)`. They distinguish this from unconstrained
theoretically available wind power under outages or curtailment. No scientific
measurements, transformations, results, forecasting algorithm or uncertainty
algorithm were changed to achieve the wording correction.

Personal machine paths and contact metadata are not present in release content.
Git author/committer metadata uses a transparently disclosed project-role identity
and reserved non-contact invalid-domain address. It is export metadata, not a
reviewer identity, fabricated GitHub account or scholarly author list. Actual
commit time is retained; no research decisions were backdated.

Ignore rules cover private run/input folders, raw data, models, results, bundles
and environment files. They are a release policy, not a substitute for reviewing
future explicitly staged content.

## Entire new-history scan

The final commit and all reachable objects were inspected. There is exactly one
root commit, 40 approved blobs and no inherited history. All 40 raw blobs match
the sealed checkout. Every declared manifest hash matches; all 30 copied source
files also match their original committed bytes.

The scans found:

- **Zero detected personal filesystem paths**, including the prior ten files,
  Unix user roots, UNC paths, encoded Windows paths and file URLs.
- **Zero detected high-confidence credentials**, private keys, tokens, JWTs,
  bearer credentials or authenticated URLs.
- **Zero personal contact emails** in blob content or commit metadata; only the
  disclosed non-contact release identity is used.
- **Zero dataset/archive/model payloads** or original results in the release.

The only generic absolute-path match is an intentional synthetic rejection
fixture in `publication_v2/tests/test_integrity.py:28`; it contains no personal
directory or real machine location. This is distinct from historical machine
disclosure. Pattern scans do not guarantee discovery of every conceivable secret.

This assessment concerns the new ref's reachable history. Existing branches,
remote refs and any previously published copies are not erased by a clean root.
Remote state was not queried or changed. Publishing this branch does not certify
that other branches of the hosting repository are path-free.

## Clean-checkout synthetic validation

A fresh temporary Git clone of the sealed root was created with byte-preserving
checkout. No data/model/result directories, private evidence or preservation
manifest payloads were supplied. Python **3.12.5**, `-S -B`, executed the selected
suites using only the standard library.

| Suite | Run | Passed | Failed/errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Stage 1 integrity, inventory, protocol, runner and temporal audit | 59 | 58 | 0 | 1 |
| Stage 2 conformal calibration | 17 | 17 | 0 | 0 |
| Stage 2 metrics | 16 | 16 | 0 | 0 |
| Stage 2 environment metadata | 15 | 15 | 0 | 0 |
| Total for final clean checkout | 107 | 106 | 0 | 1 |

The skip is the Windows symlink fixture: the account lacks that privilege.
Environment/native-probe checks use mocks; no forecasting model was fitted.
Repeated preparation runs are not added to the total as new independent cases.
Raw logs remain private; the release contains a path-neutral software summary.

Portable commands from the publication checkout:

```text
python -S -B -m unittest discover -s publication_v2/tests -v
python -S -B -m unittest discover -s publication_v2/stage2/tests -v
```

The release README provides separate Windows and POSIX relative environment
interpreter examples for optional native dependencies. Executable source derives
roots from module locations or configured workspace-relative inputs; it does not
require a personal Windows directory.

## Reproducibility and governance limits

The old review export lacked 1,937 of 2,170 protected paths. The smaller curated
release requires a more precise accounting:

| Relationship to original 2,170-path preservation baseline | Count |
| --- | ---: |
| Absent pathnames | 2,155 |
| Present with original bytes: already tracked software/configuration/tests | 12 |
| Present as newly derived public README/Git policies | 3 |
| Original protected versions not distributed | 2,158 |

These 12 source/test copies are already tracked software dependency closure, not
private scientific payloads. Their original bytes are preserved. No included
path overlaps any of the 59 frozen references or a data/model/result payload.
The three public derivatives are confined to the new branch; the original
protected README and Git policies in the working repository are unchanged.

Original preservation/freeze manifests, historical exposure registry inputs,
schedule and saved models remain private. Stage 1/2 production workflows require
those authenticated artifacts. They intentionally cannot run completely from
this public checkout. No admission or preservation gate was weakened to make
synthetic testing succeed.

The source attribution is the Berker Isen Kaggle Wind Turbine SCADA Dataset.
The README states that a URL/hash is not source authentication or usage-rights
approval. Release identity, rights, timezone/clock, interval semantics,
availability, transformations and exclusion policies still require independent
review. The installed registry is empty; **PENDING_REVIEW** and
**BLOCKED_CONFIRMATORY_TEST** remain active.

Six direct native dependencies are pinned, but a clean native installation,
transitive wheel/container lock, cross-OS numerical reproduction and complete
historical experiments were not validated. Synthetic software success does not
prove forecast accuracy, conformal coverage, historical deployability, grid
compliance or battery lifetime improvement.

The original 49 inspected blocks remain retrospective. The archived negative
finding that uncontrolled wind had fewer aggregate ramp violations than the
archived MPC controllers is acknowledged without republishing or recalculating
original measurements/results. No independent confirmation or new efficacy is
claimed.

## Preservation verification

| Original state | Result |
| --- | --- |
| Active branch and HEAD | Unchanged: `research/publication-v2`, `9517ec8bc0caac82774c32409287f449f5ce7923` |
| Existing review tip | Unchanged: `c5d355bac5fdd9fd0d34ef502683fb439f38c36e` |
| Original index SHA256 | `131c0b2e149ec81feb7cadcdeeb5115bd25b73b71abacc950a15a5424a711809` |
| Staged paths | All 185 unchanged, including the ten older staged versions |
| Original working files | 26,607 full byte/alternate-stream records unchanged before this report |
| Stage 1 preservation | 2,131 files pass |
| Stage 2 preservation | 2,170 files pass |
| Frozen references | All 59 pass |
| Freeze manifest SHA256 | `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a` |
| Private backup and recovery evidence | Available; prior snapshots unchanged; new release bundle privately verified |

The only intended source working-file addition is this report, outside the new
branch. It makes 30 untracked paths rather than the previous 29. The source index
and existing working files were not used as an export staging area. New source
Git metadata consists of the independently verified objects and new publication
ref/reflog; original HEAD/configuration and branches are preserved.

## Exact proposed later push commands — not executed

After reviewing and explicitly approving this exact root commit, inspect locally:

```text
git rev-parse publication/v2-sanitized-stage29
git rev-list --count publication/v2-sanitized-stage29
git log --oneline publication/v2-sanitized-stage29
git ls-tree -r --name-only publication/v2-sanitized-stage29
```

Expected commit is `968773d8f2c85dd28ed5bd28ec873a231c2d3db5`; expected history
count is one and file count is 40. Once network/push approval is given, check the
new destination ref. If it already exists unexpectedly, stop for review:

```text
git ls-remote --heads origin refs/heads/publication/v2-sanitized-stage29
```

If the destination is absent and approval still applies, push only the new ref:

```text
git push origin refs/heads/publication/v2-sanitized-stage29:refs/heads/publication/v2-sanitized-stage29
```

This command neither commits staged files nor changes the current checkout. No
force, mirror or all-branches operation is proposed. The clean root has unrelated
history; merging it into a research branch would require a separate plan and is
not part of this release preparation.

**No push, real-data experiment, model training, dataset admission or existing
branch rewrite was performed. Stage 2.9 stops pending approval.**
