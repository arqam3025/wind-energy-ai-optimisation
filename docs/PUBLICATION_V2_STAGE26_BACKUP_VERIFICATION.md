# Publication V2 Stage 2.6: backup verification ? failed, stopped

Prepared 6 November 2026 (Europe/London; operational timestamps below are UTC).

**Status: FAILED / STOPPED. This attempt did not establish a verified, recoverable backup.** The full copy completed according to the copier, but the independent verifier failed before completing its destination inventory. The strict stop condition was applied: recovery rehearsal and the 46-file commit-plan audit were not performed. The copied snapshot is retained privately, clearly unverified. No attempt was made to repair, retry, overwrite or delete it after verification failed.

## Backup location and timestamps

Private local snapshot:

```text
C:\Users\arqam\AppData\Local\WindEnergyResearchBackups\stage26_20261106T152729Z_894a443ba8d3
```

| Event | UTC timestamp |
| --- | --- |
| Backup creation/access precheck | `2026-11-06T15:41:29.3174027Z` |
| Primary verification failure | `2026-11-06T15:54:22.977500+00:00` |
| Source safety check after failure | `2026-11-06T15:58:09.455496+00:00` |

The snapshot is outside the source repository, has no Git-working-tree ancestor, is on a fixed local NTFS volume, and is outside detected OneDrive sync roots. No cloud or public-repository upload occurred. The destination ACL has protected inheritance with access restricted to the current user, SYSTEM and administrators. Representative copied Git/archive items passed the private-ACL check before content verification began. This does not claim that unknown third-party whole-disk backup software has been audited.

Available space before copying was 768,497,184,768 bytes. The initial accessibility and named-stream write/read probes passed. The destination was new and unique; no existing backup was overwritten. Source and destination bytes were copied with Robocopy `/E /COPY:DAT /DCOPY:DAT /R:0 /W:0 /XJ`, preserving the scope of hidden, ignored and untracked files. Source metadata screening found no reparse points, so the junction exclusion did not intentionally omit any source payload. No source Git checkout or newline transformation was used.

## Source and destination inventories

| Comparable payload | Source inventory | Copier-reported destination | Independent destination result |
| --- | ---: | ---: | --- |
| Repository files, including `.git`, `.venv`, ignored data/models/results and hidden files | 27,257 | 27,257 copied; zero copy failures reported | Incomplete; not verified |
| Repository directories, excluding the repository root | 3,651 | 3,652 including root | Incomplete; not verified |
| Repository default-stream bytes | 1,067,804,060 | Same amount reported by copier, rounded in its display | Incomplete; not verified |
| Repository named streams | 2 / 164 bytes | Copy requested with stream-preserving options | Not established |
| Original archive outside the repository | 1 file / 1,571,389 bytes | Archive copy phase completed without a reported copy failure | Not independently verified |
| Original archive named streams | 1 / 910 bytes | Copy requested with stream-preserving options | Not established |

The copier's directory total includes its source root; the manifest directory total excludes it. Private evidence/control files are outside the comparable `workspace` and `external` payloads and are not counted as source research files. Counts reported by the copier are **not** proof of hash equivalence.

All source payload files were inventoried with relative paths, sizes and SHA256 values. Named file/directory/root streams were enumerated, and their bytes hashed without printing their contents. The initial source Git state includes original index bytes, staged blob object IDs and content hashes, working hashes, HEAD, branch, and staged/unstaged/untracked distinctions. The source archive and acquisition streams were recorded privately.

Evidence inside the snapshot's `evidence` directory includes:

- `source_manifest.json` ? complete initial source inventory and SHA256 values.
- `source_git.json`, `external_source.json`, `source_preservation.json` ? initial state and source checks.
- `destination_precheck.json`, `workspace_copy.log`, `archive_copy.log` ? access/capacity and copy records.
- `FAILURE_backup.json`, `WORKER_FAILURE.json` ? failed verification and stop records.
- `source_safety_after_failure.json`, `source_untracked_safety_after_failure.json` ? source safety checks only.

The source manifest's SHA256 is `df5852a4f30f1ef8bb0dfac68380f99ddb5bbc417edebb2b7ca540d1347119f0`. Its existence and integrity do not establish destination equality. No completed `backup_manifest.json`, `backup_verified.json`, `recovery_verified.json` or `SUCCESS.json` exists.

## Verification failure and interpretation

At `PRIMARY_VERIFICATION`, the independent reader raised `FileNotFoundError` / `WinError 3` while opening a copied dependency bytecode path of 261 characters. The counterpart exists in the source. The host's `LongPathsEnabled` value was zero, and inventory analysis showed copied paths could reach 287 characters.

This is consistent with a path-length limitation in the verification helper used for this attempt. It does not prove the copied file is missing or corrupted. Conversely, a successful copy log cannot establish that it is intact. The verifier could not complete, so there is no valid complete destination hash inventory, mismatch total or recoverability claim.

The workflow exited immediately at this failure. No global execution/security/path policy was changed, no in-place repair was attempted, and no second copy was started. Earlier temporary-helper access and script-launch issues were resolved before copying, using a private host helper and normal command execution without changing execution policy; those pre-copy issues are separate from this actual verification failure.

## Recovery rehearsal

**NOT RUN.** Recovery was conditional on successful primary verification. The reserved rehearsal directory was never created. No files were restored, no original paths overwritten and no recovery Git checkout/index regeneration performed. The snapshot must not be described as recoverable on the basis of this run.

The new failure report was created after the failed snapshot. It is not part of the original copied payload, and no post-failure addendum copy was made because the stop condition was in force.

## Source Git and research preservation

Read-only safety checks after failure confirm:

| Source check | Result |
| --- | --- |
| Branch | `research/publication-v2` |
| HEAD | `9517ec8bc0caac82774c32409287f449f5ce7923` ? unchanged |
| Raw index SHA256 | `131c0b2e149ec81feb7cadcdeeb5115bd25b73b71abacc950a15a5424a711809` ? unchanged |
| Existing staged working files | 185 unchanged, with staged blob IDs/content identities retained |
| Corrected unstaged paths | 10 unchanged; older staged versus corrected working distinctions retained |
| Original untracked files | 25 independently rehashed against initial inventory; no changes |
| Stage 1 preservation baseline | 2,131 files pass |
| Stage 2 preservation baseline | 2,170 files pass |
| Frozen references | 59 pass |
| Freeze manifest SHA256 | `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a` |

These are checks of the original workspace. They do **not** certify the failed backup. No staging, reset, clean, restore, rebase, commit, push, branch change or source-content repair was performed. This report is the only intended new repository file.

No model was deserialized, trained or used for inference. No forecasting, calibration, MPC or real-data experiment ran. The Stage 2.5 report's 198 passing tests/one skip remain earlier evidence, not new Stage 2.6 test counts.

The installed real-data registry remains empty. The original source proposal remains `PENDING_REVIEW` and unapproved; `BLOCKED_CONFIRMATORY_TEST` is unchanged. Copying data privately does not grant scientific provenance or usage rights.

## Proposed 46-file commit-plan audit

**DEFERRED / NOT PERFORMED.** The prior Stage 2.5 report proposed 46 paths in 38/7/1 groups. This task did not validate those paths, certify their selection, propose a corrected commit scope, or construct an isolated index/worktree after the backup failed. Source Git safety checks above are not a commit-plan approval.

The required ordering remains: verified backup, successful recovery rehearsal, then exact commit-plan audit. No Git construction commands are supplied as an authorization to proceed before those gates.

## Security and outstanding risks

- The retained snapshot is private but unverified; it must not replace the original workspace or serve as the sole claimed recovery copy.
- Filename-only screening found potential key/certificate or secret-related names inside installed dependencies. Their contents were not interpreted or exposed, and they are not classified here as confirmed private keys. The whole copy, Git configuration and original acquisition streams were treated as private.
- Acquisition streams can contain sensitive signed-URL metadata. Their contents and credential values are absent from this report. Complete streams remain in the private source/copy scope; destination equivalence has not been established.
- The selected destination length exposed a verifier limitation under the current Windows path configuration. The actual verification code needs demonstrated long-path handling before another full attempt.
- The snapshot is on the same C: volume as the source. Even a future verified local snapshot would not by itself protect against loss of that physical storage; a separately verified offline-device copy should be considered later.
- `.venv` was included, but its copy would not alone establish a portable environment or include the external base Python/OS installation. No clean-environment reproduction is claimed.
- Known cloud-root and ancestor checks are limited to detected configuration. No upload/sync command was run, and no public destination was used.

## Exact next recommendation

Request approval for a **new uniquely named backup attempt**, retaining this failed snapshot untouched. Before copying, test the replacement verifier on disposable paths longer than the maximum source-to-destination path, with named streams and hidden files, under the actual host configuration. Use an approved shorter private local destination and/or explicitly long-path-safe access throughout inventory, hashing and recovery. Do not silently change system policy.

Then repeat complete source/destination SHA256 and stream inventories and the non-destructive recovery rehearsal. Only if both pass should the 46-file plan be audited. A later index/worktree construction, commit or push still requires explicit approval. Provenance/admission and confirmatory blockers remain separate and unchanged.

**Stop here. No further backup retry, recovery, commit planning or Git mutation was performed after the verification failure.**
