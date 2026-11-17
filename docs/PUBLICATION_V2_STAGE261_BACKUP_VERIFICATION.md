# Publication V2 Stage 2.6.1: verified backup and recovery

Prepared 10 November 2026 (Europe/London). All operational timestamps below are UTC. Branch `research/publication-v2`; HEAD `9517ec8bc0caac82774c32409287f449f5ce7923`.

**Outcome: the fresh snapshot is VERIFIED, the non-destructive recovery rehearsal passed, and the original 46-file plan was audited only after both gates passed.** No staged entry, HEAD, protected research artifact, admission policy or previous report was modified. No Git staging/commit/push or research experiment was performed. This report is a new file; the failed Stage 2.6 report remains unchanged.

## Resumption and previous-attempt diagnosis

The interrupted `w261_1405d72d62b` process was inspected before any new copy. It was no longer running. Its primary verification marker existed, but `FAILURE.json` recorded a recovery-phase source-stability failure at `2026-11-10T15:16:44.285339+00:00`. No recovery or overall-success marker existed. Its recorded source, backup and restored canonical manifests were byte-identical, SHA256 `6975143fb7cac8051afda290200890ebeb809e8adbf3b18cff6e5f563bd2f8cc`; this proved recorded point-in-time equivalence, not overall completion or current-source coverage.

Control-flow review located the failure after restored content/Git/protection checks, during the subsequent live-source inventory. Later inventory differences were confined to Git/Codex tracking metadata: two reference paths replaced and existing object metadata changed. The exact writer was not independently attributed. These changes were not ignored or excluded. The earlier process was conclusively stopped, and a new whole-state snapshot was necessary to cover the current complete Git inventory. Only then was one fresh full research backup started.

The original November 6 failure was independently diagnosed separately. Its 261-character copied dependency path fails ordinary opening and native attributes lookup with WinError 3, while extended `\\?\` access succeeds. The copied file is 14,035 bytes with SHA256 `5e3da45d4ca710d617f19f1020e25bdbd6bb118f6836fabff93b82b03fba21d8`, matching its source and recorded source manifest; it has no named streams. Thus legacy path handling caused that specific failure. It did not prove the entire old snapshot complete. `LongPathsEnabled` remains zero; system policy was not changed.

The November 6 unverified snapshot, the failed disposable fixture and the interrupted November 10 snapshot/recovery copy are all retained unchanged. No failed marker was replaced with a success claim.

## Verified private locations and timestamps

```text
Backup:   C:\ResearchBackups\w261_1c75083b1d
Recovery: C:\Users\arqam\AppData\Local\Temp\w261r_1c75083b1d
```

| Event | UTC timestamp |
| --- | --- |
| New private snapshot created | `2026-11-10T15:28:04.727413+00:00` |
| Primary verification passed | `2026-11-10T15:29:42.933937+00:00` |
| Recovery verification passed | `2026-11-10T15:31:08.470803+00:00` |
| Overall completion | `2026-11-10T15:31:08.471803+00:00` |

The destination is a new short path on fixed local NTFS, outside the source and detected cloud-sync roots, with no Git ancestor or redirected ancestor. No upload occurred. Access is restricted to the current user, SYSTEM and administrators; private ACL checks cover the root and representative copied Git/archive files. There were 764,079,579,136 free bytes before copying, exceeding the checked backup/recovery safety margin. The recovery directory was created only after primary verification passed.

## Long-path-safe implementation and preflight

The old helper passed ordinary paths to traversal, stat, open and stream APIs. The replacement consistently uses absolute extended-length paths for native traversal, hashing, metadata and ADS access; relative inventory keys remain ordinary and deterministic. Robocopy uses ordinary short root arguments with its native long-path support enabled; `/256` is not used. An initial disposable test showed this host's Robocopy rejected explicitly prefixed root arguments with error 123. That failed fixture was retained, the invocation corrected before any research copying, and fresh fixtures were used thereafter.

The current preflight passed a 469-character path, hidden file, empty directory, binary/LF/CRLF bytes, and three named streams attached to a file, directory and root. Default bytes, streams, attributes and creation/write times matched with zero mismatches. This demonstrated the actual host/tool behavior before the full research copy.

No source objects were excluded. Traversal refuses reparse points, symlinks and unsupported filesystem objects instead of following or silently skipping them. None was encountered. Hard-linked, encrypted, offline, compressed or sparse objects would require a reviewed preservation policy; none blocked this source. Copy flags `/SL /SJ` prevent following links introduced during a race; a newly observed reparse point would still fail verification. Complete directory inventories include empty and hidden directories, `.git`, `.venv`, ignored data/models/results and all working files.

Robocopy `/E /COPY:DAT /DCOPY:DAT /R:0 /W:0 /SL /SJ /MT:16` performed byte copying. No Git checkout or text rewriting was used. Named streams were explicitly checked/copied, including directory/root streams, before verification; required timestamps/attributes on new copies were restored as part of copying, never on the source. There was no mirror, purge, move or deletion operation.

## Independent inventory and SHA256 verification

Source, backup and recovery were independently enumerated using iterative `scandir` and `os.walk` implementations, followed by fresh SHA256 reads. Complete destination sets were compared, not only paths supplied by the source list. A second traversal detects directory churn; before/after file identity, metadata and content checks detect observed source changes. Sixteen hashing workers change execution order, not sorted manifest output.

| Required payload | Source | Backup | Recovery |
| --- | ---: | ---: | ---: |
| Repository files | 27,261 | 27,261 | 27,261 |
| Directories excluding root | 3,652 | 3,652 | 3,652 |
| Default-stream bytes | 1,067,822,121 | 1,067,822,121 | 1,067,822,121 |
| Repository named streams | 2 / 164 bytes | 2 / 164 bytes | 2 / 164 bytes |
| Additional original archive | 1 / 1,571,389 bytes | 1 / 1,571,389 bytes | 1 / 1,571,389 bytes |
| Archive named stream | 1 / 910 bytes | 1 / 910 bytes | 1 / 910 bytes |
| Required byte/inventory mismatches | Reference | 0 | 0 |
| Required metadata mismatches | Reference | 0 | 0 |

Source, backup and restored canonical manifests have identical SHA256:

```text
9436384c35733b7e65be285092dbe35b572648f1e79aa168b5ee17a0c9739802
```

Canonical records contain relative paths, sizes, SHA256, complete stream-name/size/hash maps, file creation/write timestamps and attributes, plus directory/root stream and metadata records. Capture timestamps, roots and file IDs are separate operational sidecars so canonical manifest bytes are deterministic. Source identity/link-count checks are additionally compared across bracketing reads. Source inventories before/after copying and recovery passed; the backup was re-read after restoration and remained unchanged. All current required-check exception lists are empty.

The external archive was independently re-read at source, backup and recovery with matching SHA256, stream names/sizes/hashes and required metadata. Its default-stream SHA256 remains `a867d34200add600eedb3832540435cf57335ba6374c77b50f90b0ab16553ea1`. T1 remains `f92c33c1cc199756b759fec251eeddc506f35d6a9e47ede034fc3e339a7c46d5`. Acquisition stream contents and signed-URL values are private and are absent from this report.

Private evidence lives under the verified snapshot's `evidence` directory: canonical manifests and capture sidecars; source Git/index/blob state; copy logs; preflight record; `BACKUP_VERIFIED.json`, `RECOVERY_VERIFIED.json`, `SUCCESS.json`; external archive verification; and `commit_plan_audit.json`. Copier logs alone were never accepted as proof.

## Recovery and source preservation

The full snapshot was restored into the separate new private recovery directory using file copies, not clone/checkout/index regeneration. All restored file/stream bytes and required metadata match the captured source. Recovery retained:

- Branch `research/publication-v2` and HEAD `9517ec8bc0caac82774c32409287f449f5ce7923`.
- Raw index SHA256 `131c0b2e149ec81feb7cadcdeeb5115bd25b73b71abacc950a15a5424a711809`.
- All 185 staged paths and their original blob object identities/content hashes.
- Ten corrected working copies, distinguishable from their older staged versions.
- All 26 pre-report untracked paths and their hashes.
- All 2,131 Stage 1 protected files, all 2,170 Stage 2 protected files and all 59 freeze references.

The freeze manifest remains `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a`. The original workspace's HEAD, index, staged/working distinctions and original untracked bytes were rechecked without modification. The recovery copy remains available and was not deleted.

The snapshot records a point-in-time state before this new report. A separately hash-verified report addendum is saved outside the immutable `workspace` payload in both backup and recovery. Restoring the base workspace reproduces the 26-untracked-file captured state; applying that addendum intentionally adds this report. Base manifests remain unchanged.

## Original 46-file commit-plan audit

The audit ran only after both successful verification markers existed and the overall worker exited successfully. The original Stage 2.5 plan passes its scoped checks:

| Check | Result |
| --- | --- |
| Original proposed groups | 38 / 7 / 1, 46 unique paths |
| Missing or working-hash-mismatched paths | 0 |
| Protected historical/frozen path overlap | 0 |
| Selected paths already staged | 21 |
| Unrelated staged paths retained/excluded | 164 |
| Older staged versus corrected working versions accounted for | All ten |
| Main index/HEAD changes | None |

All six documents in the original plan are LF-only UTF-8 without BOM. Forty package files inherit `publication_v2/.gitattributes`'s `** -text`; document text attributes are unspecified and `core.autocrlf=true` remains. A future checkout/add can therefore invalidate document hashes unless byte handling is controlled. Do not change protected attributes here; use process-local `core.autocrlf=false` and verify both candidate blob and checkout hashes before any approved commit.

The original 46-file scope covers the earlier implementation/review/readiness work. It excludes the newer Stage 2.6 failure report and this Stage 2.6.1 report. If those audit records are to be committed, the explicit proposal becomes **48 files, 38/7/3**, or a separate two-file documentation commit. That scope revision requires approval; nothing was added automatically. Exact extra paths:

```text
docs/PUBLICATION_V2_STAGE26_BACKUP_VERIFICATION.md
docs/PUBLICATION_V2_STAGE261_BACKUP_VERIFICATION.md
```

### Isolated temporary-index recommendation ? not executed

After approval, create a unique private candidate index outside `.git/index`; use `GIT_INDEX_FILE` only in a child process environment and seed it from the captured HEAD. Select explicit NUL-delimited path lists for approved groups, with literal pathspecs and process-local `core.autocrlf=false`. Compare selected names/counts and raw blob hashes with the approved working hashes. Never use the current staged index or a blanket add.

A temporary index alone does not isolate newly written objects or prevent a normal commit from moving HEAD. If original Git metadata must remain byte-for-byte untouched, use a separate candidate object directory with the original object store available read-only as an alternate, or a separately approved isolated review repository. Review candidate trees before any commit/ref operation; future commit and branch reconciliation need explicit approval. No temporary index, object store, worktree, staging, commit or ref update was created in this task.

## Limits, privacy and next action

- This is verified file/state recovery, not a VSS/sector-image or atomic filesystem snapshot. Bracketing scans establish observed stability, not proof against a change reverted invisibly between reads.
- Required default/ADS bytes, directory membership, creation/write times and attributes were checked. Original owner/DACL/SACL, last-access timestamps, physical file IDs and unrelated filesystem bookkeeping are not claimed identical. Private destination ACLs intentionally replace source access permissions. No encountered required object or stream remains unresolved.
- Both copies are on C:. They provide separate verified locations, not protection against loss of that physical storage. A later independently verified offline-device copy is advisable.
- `.venv` is preserved, but this is not a clean-environment or portable-OS reproduction. No forecasting/model tests, training, inference, MPC or real-data experiment ran.
- Potentially sensitive dependency filenames, Git configuration and acquisition metadata were preserved privately; no credentials, keys, access-token values or stream contents were printed in this report. No backup was uploaded.
- Backup integrity is not dataset-provenance approval. The installed registry remains empty, T1 remains `PENDING_REVIEW`, and `BLOCKED_CONFIRMATORY_TEST` remains unchanged.

**Next action:** review the verified backup and approve the precise 46-file or amended 48-file candidate scope plus the isolated-index procedure. No commit/push is authorized by this report. Independent provenance/rights/timing review remains a separate gate before retrospective experiments. Stop here and await approval.
