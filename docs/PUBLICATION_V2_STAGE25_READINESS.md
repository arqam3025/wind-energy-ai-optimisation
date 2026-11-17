# Publication V2 Stage 2.5: code custody, Git separation and retrospective readiness

Prepared 2026-11-06T07:32:11.299010+00:00. Repository: `arqam3025/wind-energy-ai-optimisation`. Branch: `research/publication-v2`. HEAD remains `9517ec8bc0caac82774c32409287f449f5ce7923`.

**Recommendation: obtain approval for a verified private backup and isolated, explicitly scoped code commits next; do not run real-data experiments.** Current software passes this workspace's tests, but T1 remains `PENDING_REVIEW`, the installed real-data registry is empty, and `BLOCKED_CONFIRMATORY_TEST` remains in force. This is not a journal-readiness, independent-validation or improved-performance claim.

This task creates only this report, using exclusive creation. Existing source, index entries, protected research, policies, results and reports remain unchanged. No staging, reset, clean, restore, commit, merge, push, worktree creation or branch movement was performed. Full Stage 2 tests fitted temporary synthetic models only; no real model was trained and no real experiment ran.

## 1. Git inventory and principal risks

| State | Finding |
| --- | --- |
| Branch | `research/publication-v2` |
| HEAD | `9517ec8bc0caac82774c32409287f449f5ce7923` |
| Staged additions | 185: 175 `A ` and 10 `AM` |
| Unstaged tracked changes | 10, all within staged Stage 2 additions |
| Untracked before this report | 24, all Publication V2 Stage 2–2.4 |
| Existing Stage 2–2.4 files | 45: 21 staged and 24 untracked; all absent from HEAD |
| New report | One further untracked file; proposed allowlist total 46 |
| Index SHA256, unchanged | `131c0b2e149ec81feb7cadcdeeb5115bd25b73b71abacc950a15a5424a711809` |
| `core.autocrlf` | `true` |

`AM` means an addition is staged but its working copy has later changes. All ten index versions predate the validated corrections. Committing the current index would capture those older versions plus 164 excluded files. Preserve both layers; a future scoped commit must select the current working bytes below through a separate index.

Recent history:

```text
9517ec8 Document Stage 1 validation and blocked confirmatory test
fc405f9 Add isolated publication v2 chronology and provenance protocol
2b49e7a Preserve authenticated research bytes across Git checkouts
b09500e Document experimental findings and reproducibility limits
```

| Existing staged classification | Count | Disposition |
| --- | ---: | --- |
| Publication V2 Stage 2 source/tests/docs | 21 | Select current working versions only after approval |
| Current dashboard | 27 | Exclude and retain staged |
| Historical audits/backups | 38 | Exclude; review archival publication separately |
| Historical research/scripts/docs/results/tests | 96 | Exclude; preserve |
| Historical documentation backups | 2 | Exclude; preserve |
| Older Stage 1 extra log | 1 | Exclude; canonical final log is already in HEAD |
| Total | 185 | No staged entry changed |

Two material limits prevent treating a scoped code commit as a complete reproducible release:

1. **Artifact custody:** 1,937 of 2,170 protected paths are absent from HEAD, comprising 217,256,125 local bytes. All seven saved models, all 59 frozen references and the manifest itself are absent from HEAD. Five frozen sources are excluded staged historical scripts; 54 development traces are ignored local files. The scoped commits will not secure them. Obtain a complete private backup before Git curation; distribute inputs only after rights review.
2. **Document bytes:** the 40 allowlisted `publication_v2/stage2/` files inherit `publication_v2/.gitattributes`'s `** -text`. The five allowlisted documents have unspecified text attributes and are UTF-8 without BOM, LF-only. Protected Stage 1 protocol/report/plan documents are also LF-only with unspecified attributes. A normal Windows checkout under `core.autocrlf=true` can change their bytes and invalidate evidence hashes. Do not change protected attributes now. Use `core.autocrlf=false` from the initial approved isolated checkout and verify blob/checkout hashes. Review a permanent narrowly scoped document policy separately.

The historical manifest, raw data, schedule and tables/documents referenced by Stage 2.4 also include paths outside the code allowlist that are absent from HEAD. A clean clone therefore lacks required inputs. Do not fabricate them, weaken preservation or include unrelated files merely to make tests pass. A lawful private input bundle or separately approved historical archival change is required. Current validation used the complete local workspace; clean-clone/clean-environment reproduction is not established.

## 2. Exact proposed commit plan — approval required

| Commit | Scope | Files |
| --- | --- | ---: |
| A | Current Stage 2 implementation, Stage 2.1 corrections and Stage 2.3 contracts, tests and retained validation | 38 |
| B | Stage 2.4 pending provenance review package | 7 |
| C | This new Stage 2.5 report | 1 |
| Total | Every other staged path excluded | 46 |

Keep A together: current lineage imports the new study validator. Reconstructing artificial earlier-stage commits from old staged blobs risks broken intermediate states. The Stage 3 MPC file is a specification, not a new implemented MPC algorithm. Preserve the retained initial validation errors alongside final passes.

The hashes below identify working-file bytes, not Git object IDs. `A` is a staged addition, `AM` an older staged addition with newer working contents, and `??` an untracked file. Recheck each hash before approved copying/staging. A difference requires renewed review; never substitute the original staged blob.

### Commit A: 38 exact files

| Path | State | Working SHA256 |
| --- | --- | --- |

| `docs/PUBLICATION_V2_RETROSPECTIVE_PROTOCOL_REVIEW.md` | `??` | `5a41922aff04d689ae880ca2ea55dcdd1adf6c61a2653b142cdb8d911ed4f378` |

| `docs/PUBLICATION_V2_STAGE2_METHODS.md` | `A ` | `999b8e92a7806d35516c0a3e31f40a09afbe3c556df98019e9b7721cfef750d1` |

| `docs/PUBLICATION_V2_STAGE2_VALIDATION.md` | `??` | `2048039895413add63b5a5f59a98bb1c22c85fd2e95f07807ab2429c060502d9` |

| `docs/PUBLICATION_V2_STAGE3_MPC_SPEC.md` | `A ` | `389a0818929a29fe97c77cb463d9c3ea071889879498f35577129049c24c8cb2` |

| `publication_v2/stage2/.gitignore` | `A ` | `ede29b448eef61193eabfdab16bd6bb5966e06ae47e7b60687ebfa8d1e58f65a` |

| `publication_v2/stage2/__init__.py` | `A ` | `43f5f3eddb4bde22d63285e508aeabce93d60a652465947c3c7d86ed78c53b99` |

| `publication_v2/stage2/config.json` | `A ` | `624aa80d90334b182b1405e751026a4da863aa58b9943d439213da92e21304ef` |

| `publication_v2/stage2/conformal.py` | `AM` | `5604dccd76ba9005596e4bd6bd02ebe4002ce79f35e5f7c89ac0bb67d966ddc6` |

| `publication_v2/stage2/data.py` | `AM` | `6faf504973cc6e942405bf981b6fc3f29e5c8ccc3d213ab6677b2305eb774d8f` |

| `publication_v2/stage2/environment.py` | `??` | `1259a1f0fb26fef066b33c47fa7524809a9d254dda4aa3cbc6f7de4fa9daf1dc` |

| `publication_v2/stage2/forecasting.py` | `AM` | `46d7f1a75d5fcf8a672d68e4e10b50e21fddb9a1cfb58ae7ee222a65d2d50a96` |

| `publication_v2/stage2/lineage.py` | `??` | `39918618848e18cf6544196b67126a0608bdfc20cd912a6d79c8e5b647abe839` |

| `publication_v2/stage2/metrics.py` | `AM` | `9fd8fe81c17bfd63d2fbde6d64169033fe102f32af996517763834cd812feaec` |

| `publication_v2/stage2/plots.py` | `A ` | `617d3b0143d7f11ae11ce551e51c69bf450d22e6d88e27460b41923d1d08c3bd` |

| `publication_v2/stage2/preservation_baseline.json` | `A ` | `b2d7c43d524e74cec9265943a3a13f0505aabd342ff3b7caf48a17a48462cad4` |

| `publication_v2/stage2/provenance_policy.json` | `??` | `229d140d785ff1c177ef090c6034cf67bee5a2464903789bc6c93df390017b7b` |

| `publication_v2/stage2/requirements.txt` | `A ` | `fbdead968c85c969a85ea4d87961f2755f9010a27a03d92bce565bbb9e7e35a4` |

| `publication_v2/stage2/runner.py` | `A ` | `f51132b831254c56e5a480609ebd4fa2fd9d6f502d5c0877117d5b5a5725acde` |

| `publication_v2/stage2/study.py` | `??` | `0c5374aed34db5ff6eeb08d209c194110863f05efef39ff69373b9e2bdb8fc01` |

| `publication_v2/stage2/tests/__init__.py` | `A ` | `80e26af66cd2c5622af911468cdeb0048a8bb70a9373283256a5c478d9d4a655` |

| `publication_v2/stage2/tests/fixtures.py` | `AM` | `739285d602ca1c629e453711eb70db3ed419f969b0802248c4577068e71aa8df` |

| `publication_v2/stage2/tests/test_conformal.py` | `AM` | `f83bd1da57171693edd62f79e0d73fe2059069252de496785de4b9b235d9c6bf` |

| `publication_v2/stage2/tests/test_data.py` | `AM` | `3d5f4cc8f10a1e78d51ce7ccfe8b06263002b521590a0165d952da1f9163eafb` |

| `publication_v2/stage2/tests/test_environment.py` | `??` | `f9c22715de6fd71116c9a30df811b637855c1f6ed89e6dbf3f2dd16830a0101a` |

| `publication_v2/stage2/tests/test_forecasting.py` | `AM` | `6b13da81fbefd25062134f0553bcdf6d6d4e95374024913eda457dc6e40c663f` |

| `publication_v2/stage2/tests/test_lineage.py` | `??` | `745cc89356a3ad86a5d35280b6ce7f444b64e59b4f718018e7edc8ceca7d13ee` |

| `publication_v2/stage2/tests/test_metrics.py` | `AM` | `a1f35f03d952d89c1bd75d20549c51a7e1b6ae0f76e9f30f4088c5d46a5f5fb9` |

| `publication_v2/stage2/tests/test_retrospective.py` | `??` | `5fbc23b3d00c434bc2c5e96b079a9dd5fa38b0f8561a9019f91594e55fea0348` |

| `publication_v2/stage2/tests/test_workflow.py` | `A ` | `fc828730690f8cb5899fef5ae703d38cd3e17b4250a01aee1ab38fa2e5a8711f` |

| `publication_v2/stage2/validation/environment_constraints.txt` | `??` | `a4850841a0aa03cf42525cc52998935617b2c6d0da31b971babd5cc996b8ef04` |

| `publication_v2/stage2/validation/environment_manifest.json` | `??` | `13d41a0f470ee8b1a964f2a9175b491c9028046961e63b4d3cc87df0c1c9141d` |

| `publication_v2/stage2/validation/preservation_verification.json` | `??` | `02379a9cebc36dcd1603d7a7c56f3f4744b87c7c6c1195dc08c18789fa5cbeed` |

| `publication_v2/stage2/validation/stage21_stage1_tests.log` | `??` | `c505cae472df2935bb8a229c57702906f92f922495f8e0f19098902709687dc7` |

| `publication_v2/stage2/validation/stage21_stage2_test_summary.json` | `??` | `21d0b88b130d8e9f570eaeb10d97dba31e919a23cf46d72fc216f1485b0158ee` |

| `publication_v2/stage2/validation/stage21_stage2_test_summary_final.json` | `??` | `731fc74cae5daefb1ad2a81d2d2d9db8a2d1fe6188dc36113272da1ddc6e1678` |

| `publication_v2/stage2/validation/stage21_stage2_tests.log` | `??` | `296a5cca84accee651f172e02bb3864deb4bbadd020ef9a5b19ceee331108267` |

| `publication_v2/stage2/validation/stage21_stage2_tests_final.log` | `??` | `eb37b06dc9ec0d1dbc4d70497a88283aa8568bc5f6e5e43917270c5111c01a80` |

| `publication_v2/stage2/workflow.py` | `AM` | `39349b7ce039811bd1615257fc91cecc64f56646466fde7b493739d190857ff4` |

### Commit B: 7 exact files

| Path | State | Working SHA256 |
| --- | --- | --- |

| `docs/PUBLICATION_V2_REAL_DATA_PROVENANCE_REVIEW.md` | `??` | `028380b084fa5f3a2986ee8a245dc465769ecba62c762202afebed6ad8120152` |

| `publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/evidence_register.json` | `??` | `c6b7c03a843a6216a70c618320cf73f2a8dd4324f04292764c97f6511f29354e` |

| `publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/proposed_registry_entry.json` | `??` | `3df1457e8118bf6a0b546e82541104241d3a236699958536d20ea876bb19ec53` |

| `publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/reviewer_decision_form.json` | `??` | `5152366849de20b0fc7815060ad8040634df059657dec1546f19d49f6a51f10f` |

| `publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/test_validate_package.py` | `??` | `a295e2f1fd13c0d3eb496004f765fa1a82a8dc233f7315d26b9b0b18adfdb405` |

| `publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/validate_package.py` | `??` | `52f0a216ed2dd7f132128e4cc89f14ce2079166cd9840535ca24b604301dc97e` |

| `publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/validation_report.json` | `??` | `711c8a55ca91742a93756bc8709a6b481a1dfb32a98acb03cd93349d3eb326f4` |


### Commit C: one file

`docs/PUBLICATION_V2_STAGE25_READINESS.md`. Compute its hash after creation and recheck at approval; this document cannot embed its own stable content hash. The separate temporary final-verification record stores that hash.

### Proposed isolation procedure

After approval and a verified backup, create a detached worktree at `9517ec8`, with `core.autocrlf=false`, then create a new review branch there. A linked worktree has a separate index and HEAD but shares objects/administrative state; it is not a backup. Leave the original branch HEAD and index unchanged. [Git worktree documentation](https://git-scm.com/docs/git-worktree)

Illustrative future commands, **not executed**; approve the new destination and verify it is absent first:

```powershell
$stage25Review = 'C:\Users\arqam\Documents\wind-energy-ai-publication-v2-review-UNIQUE'
if (Test-Path -LiteralPath $stage25Review) { throw 'Review destination exists' }
git -c core.autocrlf=false worktree add --detach $stage25Review 9517ec8bc0caac82774c32409287f449f5ce7923
git -C $stage25Review -c core.autocrlf=false switch -c research/publication-v2-stage25-review
```

Copy the exact approved working bytes. Create NUL-delimited UTF-8 path lists from each table outside the original workspace. In the isolated checkout, stage only that list with literal pathspecs and `core.autocrlf=false`; Git supports `--pathspec-from-file` and `--pathspec-file-nul`. Compare staged names, counts, blob bytes and working hashes with the approved table before every scoped commit. Refuse extras. No blanket add/commit of the original index is acceptable. [Git add documentation](https://git-scm.com/docs/git-add)

Any authorized private test bundle must remain outside the commit index. Missing inputs fail closed. After approved commits, verify the review checkout's index is clear and the original HEAD/index/working bytes remain unchanged. Later reconciliation into the checked-out `research/publication-v2` branch needs a separate approved procedure: moving its HEAD now changes the interpretation of the 185-entry index even if its bytes do not change. No merge or push is proposed.

## 3. Backup and recovery instructions — not executed

Only a temporary audit snapshot, raw index copy, inventory, logs and summaries were created. They are not a complete durable backup. Do not delete the original workspace or treat a bundle as sufficient protection.

Before Git curation:

1. Quiesce editors, generators and Git writers without discarding work. Select a new private, access-restricted NTFS destination outside the source; verify resolved paths and capacity. Do not reuse an existing destination. Keep raw data, model files, `.git` configuration and acquisition streams private pending rights/privacy review.
2. Copy the complete working tree, hidden files and `.git`, including untracked and ignored data/models/results/input/run directories and any environment required for recovery. Preserve the full object database and raw index: staged-only blobs may not be reachable from committed refs. Inventory reparse points and separately preserve required excluded targets.
3. Separately copy `%USERPROFILE%/Downloads/archive.zip`, its NTFS `Zone.Identifier`, and the T1 alternate stream. Preserve original private streams and verify both default-stream and alternate-stream hashes. Use sanitized acquisition metadata for publication. An ordinary ZIP is not an adequate substitute for checked ADS-preserving recovery.
4. Export staged and unstaged binary patches independently through Git's `--binary --full-index --output=<new-file>` options, avoiding PowerShell text pipelines. Record HEAD/refs, staged blob IDs, raw index hash, working hashes, untracked/ignored inventories and stream identities.
5. A supplementary `git bundle --all` exports reachable history, not the index/working tree or staged-only state. Keep the full `.git` and index copy. [Git bundle documentation](https://git-scm.com/docs/git-bundle)
6. Compare copied file/stream hashes and verify source invariance. If the source changes, retain that attempt and create a new uniquely named snapshot. Test recovery into a new directory before treating the backup as recoverable.

An approved NTFS copy can use Robocopy `/E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ` with a log. The `X` copy flag skips alternate streams; do not add it. `/XJ` separately excludes junctions. Codes of eight or higher indicate failure; lower codes still require log/hash review. Do not use mirror, purge or move flags. [Microsoft Robocopy documentation](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy/)

Supplementary exports after a full approved copy, using a new approved backup path, could be:

```powershell
# FUTURE ONLY: $stage25Backup names an approved private snapshot directory.
git diff --cached --binary --full-index --output="$stage25Backup\staged.patch"
git diff --binary --full-index --output="$stage25Backup\unstaged.patch"
git bundle create "$stage25Backup\refs.bundle" --all
git bundle verify "$stage25Backup\refs.bundle"
```

Recovery:

1. Choose a new absent NTFS recovery directory outside the original. Copy the verified full snapshot there; never overwrite/reset/restore/clean/move the original. The self-contained `.git` copy retains the original index and objects. Current Git common/object storage is `.git`, without object alternates.
2. With `GIT_OPTIONAL_LOCKS=0`, compare recovered HEAD/index hash/staged blob IDs, staged-versus-unstaged distinctions, working and ignored bytes, and streams against the manifest. Preserve the older index versus newer working copies. Do not apply patches on top of a complete copied tree: that would double-apply changes.
3. Verify 2,170 protected files and 59 freeze references, then the pending-package check without experiments. Confirm the registry remains empty and confirmation blocked.
4. A surviving refs bundle alone cannot prove recovery of staged, unstaged, untracked or ignored work. Any partial reconstruction needs a reviewed recovery plan in a new directory.

## 4. Validation executed for Stage 2.5

The counts below are freshly executed, not copied from earlier reports. Output-producing workflow/model tests and the Matplotlib cache use temporary directories.

| Executed suite | Run | Passed | Failed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: | ---: |
| Stage 1, standard library only | 59 | 58 | 0 | 0 | 1 |
| Full Stage 2 including native synthetic fitting and 28 retrospective tests | 120 | 120 | 0 | 0 | 0 |
| Stage 2.4 package, standard library only | 20 | 20 | 0 | 0 | 0 |
| Total unique cases | 199 | 198 | 0 | 0 | 1 |

Elapsed seconds including discovery: 2.719, 94.328, 0.078, respectively.


The sole skip is the account's unavailable Windows native symlink-creation privilege (WinError 1314); privilege-free symlink/junction guards run. No failures/errors occurred in these runs. Native tests fitted, saved and reloaded invented synthetic fixtures only. No real SCADA model was trained or used in a new experiment.

The Stage 2.4 live check reverified 25 evidence items, 22 unchecked review areas, 29 hashed references, seven historical model byte identities without loading those models, and the original archive/member association. Result: `INTERNALLY_CONSISTENT_PENDING_REVIEW`, `scientific_admission: false`, `experiments_authorized: false`. Installed registry is empty; `publication_v2/stage2/runs/` is absent before/after validation.

Earlier evidence remains separate: Stage 2.1's 92-pass final run and retained native-probe error; Stage 2.3's 178 passes/one skip; Stage 2.4's selected 146 passes/one skip. Those are not added to this task's fresh 198 passes/one skip. This task ran the full Stage 2 native suite; Stage 2.4 deliberately ran non-fitting guards only.

Equivalent commands for the executed unittest loader/runner calls:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:GIT_OPTIONAL_LOCKS = '0'
$env:MPLBACKEND = 'Agg'
.venv/Scripts/python.exe -S -B -m unittest discover -s publication_v2/tests -v
.venv/Scripts/python.exe -B -m unittest discover -s publication_v2/stage2/tests -v
.venv/Scripts/python.exe -S -B -m unittest discover -s publication_v2/stage2/admission_reviews/berker_isen_t1_stage24 -p test_validate_package.py -v
.venv/Scripts/python.exe -S -B publication_v2/stage2/admission_reviews/berker_isen_t1_stage24/validate_package.py --root . --archive-path "$env:USERPROFILE\Downloads\archive.zip"
```

Fresh runtime: Python `3.12.5 (tags/v3.12.5:ff3bc82, Aug  6 2024, 20:45:27) [MSC v.1940 64 bit (AMD64)]` on `Windows-11-10.0.26200-SP0`.

| Installed dependency | Version |
| --- | --- |
| numpy | 2.5.4 |
| scipy | 1.18.1 |
| scikit-learn | 1.9.1 |
| xgboost | 3.4.1 |
| lightgbm | 4.7.0 |
| matplotlib | 3.11.2 |


Earlier complete environment records include installed/native fingerprints; the current full-suite native save/reload and environment guards pass. This is exact-workspace evidence, not a clean installation, portable wheel/container closure or universal cross-platform byte guarantee. Timestamped manifests can differ even when native model bytes/predictions reproduce.

## 5. Preservation and historical results

All **2,170 protected files** and **59 freeze references** pass byte verification. Manifest remains `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a`. The task-start snapshot verifies **2,215 existing files**, including all prior Stage 2–2.4 artifacts. All 185 staged working files, original index, unrelated work and HEAD remain unchanged. This report is the only new repository file.

Read-only arithmetic from saved 49-block tables reproduces:

| Archived retrospective case | Ramp violations | Summed exceedance, kW |
| --- | ---: | ---: |
| Uncontrolled wind | 1,465 | 317,210.288 |
| Adaptive one-sided MPC | 1,486 | 323,638.526 |
| Fixed-margin MPC | 1,502 | 326,158.296 |

Both archived controllers have worse aggregate counts/exceedance than uncontrolled wind. These are checks of saved arithmetic, not new controller experiments or efficacy estimates. No controller was selected from them. All 49 episodes remain retrospective; block 6 and the known development/evaluation overlaps remain disclosed.

Known local identities remain T1 SHA256 `f92c33c1cc199756b759fec251eeddc506f35d6a9e47ede034fc3e339a7c46d5` and archive SHA256 `a867d34200add600eedb3832540435cf57335ba6374c77b50f90b0ab16553ea1`. Local hashes and acquisition traces do not independently authenticate rights, release identity, clock semantics or latency. Pending review material is author-created evidence organization, not approval.

## 6. Development-only experiment specification — unexecuted

### Admission, target and common comparison

The proposed question is descriptive retrospective forecast/uncertainty comparison on a reviewed development cohort, not an untouched test or confirmatory efficacy estimate. No source period, sample count, cutoff, latency value, protocol approval or reviewer identity is assigned here. Pending-package fields remain null until genuinely evidenced and reviewed. Historical script boundaries are not new approved cutoffs.

Require Stage 2.1 lineage/cohort checks and Stage 2.3's explicit `RETROSPECTIVE_DEVELOPMENT` contract. Actual creation/approval/acquisition/access/exposure/execution dates are separate from historical observations, replay decisions, availability and model/calibration cutoffs. A declaration may postdate observations and prior access; new fitting must follow actual approval. No backdating or confirmation promotion through renaming, hashing, reordering or copying is permitted.

Review the target as `max(0, measured active generation)` in kW, retaining signed raw/current features. This does not establish unconstrained wind potential when outage/curtailment status is unknown. Older Stage 2 methods' “available wind power” wording needs a future versioned reconciliation with Stage 2.4; no protected document is changed here.

Compare persistence, XGBoost and LightGBM on the same train/calibration/development origins, features, six targets and scoring observations. Persistence repeats clipped current power and deliberately ignores other feature dimensions. Each booster fits six direct regressors at 10, 20, 30, 40, 50 and 60 minutes. No early stopping, scoring-outcome callbacks, feature selection, search or controller selection belongs to this experiment.

Fourteen features: current power/wind speed/direction; power/wind-speed lags at 10/20/30/60 minutes; ten-minute power/wind changes; four-point power mean at `t,t-10,t-20,t-30`. Exact timestamp joins and a common ordered matrix are mandatory.

| Model | Current settings |
| --- | --- |
| Persistence | Repeated clipped current measured power; common cohort/window identity |
| XGBoost | 100 trees, depth 4, learning rate 0.05, squared-error objective, histogram method |
| LightGBM | 100 trees, depth 4, 15 leaves, learning rate 0.05, deterministic column-wise training |
| Shared | Seed 20261101; one thread; full row/column sampling; L1 0, L2 1; record effective native parameters |

Any later declared LightGBM partial sampling needs an effective positive sampling frequency and native verification; it is not an ablation selected here. A missing/failed comparator must fail the requested complete comparison, never disappear silently.

### Strict causal boundaries

- Require reviewed offset-aware clock/interval semantics; naive T1 cannot silently become UTC.
- Source receipts precede feature availability, which is no later than origin. Require `origin <= issuance <= decision < target`, exact horizons and complete feature support.
- Training labels and required availability must satisfy the replay fit cutoff. Current replay model availability equals `dataset.fit_time`; simulated training duration is unsupported. Native `fitted_at_utc`/`saved_at_utc` are actual new dates, not evidence the model existed historically.
- Require `last_train_origin + 60 min < first_calibration_origin` and `last_calibration_origin + 60 min < first_development_origin`. On the ten-minute grid this means at least **70 minutes between boundary origins**. All-horizon target sets are disjoint; causal feature lookbacks may reuse earlier known observations, so not all raw support is necessarily disjoint.
- Authorized periods include at least 60 minutes of feature lookback and 60 minutes of final target support. Prespecify sample/event exposure rationale; the historical 49-block count is not a sample-size justification.
- Validate all calibration candidates' metadata before filtering, including other models/horizons and unavailable records. Admit only the same model/horizon with `target_time < decision_time` and observation/residual availability no later than decision. Equal-time targets are ineligible; static calibration requires every fixed member eligible.
- Seal intervals/predictions before outcome scoring. Predeclared residual updates after release are allowed; no model refitting or method selection uses scoring outcomes.

Unknown operational availability requires a named independently reviewed `ASSUMED_LATENCY` scenario with explicit finite delays and `historical_deployability_verified=false`. It must match the supplied ledger without rewriting receipts. Same-time current features reject positive required measurement/processing delay under the present origin contract. Do not silently move origins; any redesign is a separate reviewed version. Assumptions cannot resolve rights, timezone, interval meaning or historical deployability.

### Conformal variants and ablations

Alpha is 0.10, minimum calibration support 30 per model/horizon, score absolute prediction error. Unequal alpha is refused unless explicitly named sensitivity; none is added here.

| Variant | Eligible history | Window | Half-life | Floor |
| --- | --- | ---: | ---: | ---: |
| `static_abs` | Entire fixed declared calibration set | Inactive | Inactive | 0 kW |
| `rolling_abs` | Latest eligible model/horizon residuals | 144 | Inactive | 0 |
| `weighted_abs` | Latest eligible residuals | 144 | 1,440 min | 0 |
| `rolling_window72` | Latest eligible residuals | 72 | Inactive | 0 |
| `rolling_window288` | Latest eligible residuals | 288 | Inactive | 0 |
| `weighted_half_life720` | Latest eligible residuals | 144 | 720 min | 0 |

Unweighted rank is `ceil((n+1)(1-alpha))`, without interpolation/capping infinite support. Recency weighting uses exponential weights and a unit test-point mass at infinity; insufficient finite support fails. Intervals are `[max(0,prediction-q),prediction+q]`. Rolling/weighted adaptation gives no time-series coverage theorem. All selected floors are zero; no positive-floor efficacy ablation is specified. Floor-binding diagnostics do not establish adaptation or lifetime benefit.

### Metrics, exclusions and statistical limits

Report counts, per-horizon/aggregate MAE/RMSE/signed bias in kW and paired differences/skill against persistence on identical observations. Aggregate RMSE uses squared errors, not averaged episode RMSEs. Zero-denominator persistence skill stays undefined. Report losing as well as winning complex models.

Rapid events are the offline subset `abs(actual_t-actual_t-10min)>200.001 kW`. Current metrics are forecast MAE/RMSE on that subset, not direct ramp-amplitude errors or event-detection accuracy. Membership cannot enter fitting, features or online calibration selection. Report counts and undefined empty strata.

Uncertainty metrics: marginal and rapid-event coverage, nominal-reference differences, absolute coverage error, mean width, calibration counts/effective size, margins/floor binding and drift. Default periods are UTC target calendar days. Interval comparisons require common alpha, point forecasts and observations. None proves conditional/simultaneous coverage.

No dependence-aware confidence-interval, resampling or significance module is implemented. Overlapping horizons and chronological weather dependence prevent treating forecasts as IID. Any later inference needs a separately prespecified temporal unit, block/bandwidth choice, exposure/power rationale and multiplicity policy; do not choose them for a desired p-value.

Prespecify measurement coverage, expected grid/missing slots, role windows, authorized support and missing-data rules. Current policy rejects duplicates, missing cells and imputation. Every candidate is included with complete feature/six-target support or excluded for verified missing feature/target support, with timestamps/reasons/denominators. Do not omit difficult periods because errors are large. Zero blank raw cells does not negate 32 gaps/2,030 missing slots.

Require identical cohorts for all methods; model-specific complete-case masks or missing predictions fail comparison. Retain rejected data, failed models, insufficient calibration and interrupted runs. Use unique output paths and atomic hash-verified completion markers, preserving previous artifacts. Record source/config/data/model/environment hashes, seeds, effective parameters, actual fitting dates and preservation before/after.

A future output location is `publication_v2/stage2/runs/<approved_unique_id>`, not an execution command. No real run ID or numerical outcome is assigned.

## 7. Independent review requirements and blockers

| Area | Evidence needed before real retrospective admission |
| --- | --- |
| Source/release | Provider/dataset/exact release mapped to original raw/archive; `T1:2018` is a study-period label, not authenticated release. |
| Rights | Acquisition-version/current licence, research/reproduction/redistribution scope and unresolved upstream authority. Public metadata retrieval was inconclusive, not proof of no licence. |
| Clock/measurement | Timezone/DST/synchronization, timestamp/window meaning, units, QC/curtailment/outage semantics and measured-generation target limits. |
| Acquisition/exposure | Independently checked actual access/custody history; local download metadata is not first-access/non-exposure proof. |
| Availability | Actual receipt/computation records or a restricted, explicitly reviewed timing scenario. |
| Canonical lineage | Reviewed implementation/identity for missing time/ID fields; deterministic generated IDs must be labelled derived, not provider-issued. Current one-to-one map cannot create absent evidence. |
| Cohort/exclusions | Authorized periods, full feature/target support, historical matches, missing slots and complete rejection reasons/denominators. |
| Actual/replay clocks | Genuine creation/approval/access evidence and execution floor; new fit/model/static-calibration cutoffs and approved configuration. No blank is filled here. |
| Reviewer decision | Competent named independent reviewer, conflicts record, actual decision dates/document; exact dataset/provenance/source/lineage/cohort/period/study/clock/availability hash bindings. |
| Reproduction | Verified private backup, lawful bundle, document-byte policy, supported full environment and eventual clean-clone reproduction. |

The Stage 2.4 proposal remains non-installable and pending. Decision-form options are not decisions. Do not install it, set `independently_checked=true`, or infer approval from checksums.

Unknown frozen-model fitting/selection history limits historical deployment claims. A new-model experiment that never uses those predictors must establish its own ledger; it need not invent the old history. The current generic preflight inventories old metadata and always reports missing eligible ledger/historical fitting; it is not a dataset-specific decision for a new model study. Review a dataset-specific non-fitting preflight separately if needed, preserving actual gates. Do not run an output-writing preflight merely to generate placeholder research artifacts.

## 8. Next milestone and stop condition

1. Obtain approval for a verified private full backup/recovery test and the isolated 38/7/1 commit plan. Do not publish rights-sensitive inputs through code commits.
2. Obtain the independent provenance/timing/exposure decision and review necessary canonicalization. Registry remains unapproved until all required bindings exist.
3. After separate authorization, run a dataset-specific non-fitting admission check and environment verification on the reviewed ledger.
4. Only after admission and explicit experiment approval, execute a unique retrospective development comparison under the frozen specification. Preserve negative/inconclusive results and failures. Confirmation still needs independently reserved uninspected data with custody/prespecification evidence.

Stop after this report and await approval. The report itself authorizes no source fixes, attribute changes, full backups, Git mutations, experiments or provenance approval.

## Appendix A. Older staged bytes versus current working versions

| Path | Index blob SHA256 | Working SHA256 |
| --- | --- | --- |
| `publication_v2/stage2/conformal.py` | `25a39548ad0acf729a7512ebd375625da48de51dd0e74f3df55511d68ae4c784` | `5604dccd76ba9005596e4bd6bd02ebe4002ce79f35e5f7c89ac0bb67d966ddc6` |
| `publication_v2/stage2/data.py` | `f6aee0a52d6bf7840b4e1b9383a20f34849da1ae41137cbe61061d9f287e6c11` | `6faf504973cc6e942405bf981b6fc3f29e5c8ccc3d213ab6677b2305eb774d8f` |
| `publication_v2/stage2/forecasting.py` | `151a4e0a485ab28a5fe3b2b8e53cacc2b19f515fa036f4ff2132fd1951b54121` | `46d7f1a75d5fcf8a672d68e4e10b50e21fddb9a1cfb58ae7ee222a65d2d50a96` |
| `publication_v2/stage2/metrics.py` | `94d3dce42c96f4f9923ac5b985849483a47ba5b36157e8853634a006583276ad` | `9fd8fe81c17bfd63d2fbde6d64169033fe102f32af996517763834cd812feaec` |
| `publication_v2/stage2/tests/fixtures.py` | `4893c65439ab993f2c62b9e738a9d72ca322276e9cfe30adab65d26d6d9d9cdf` | `739285d602ca1c629e453711eb70db3ed419f969b0802248c4577068e71aa8df` |
| `publication_v2/stage2/tests/test_conformal.py` | `aef8387a7210a10f480c3df7a235a6b19f7792129d6dc3f02a295c79bd844f7c` | `f83bd1da57171693edd62f79e0d73fe2059069252de496785de4b9b235d9c6bf` |
| `publication_v2/stage2/tests/test_data.py` | `02c4f8e157ff01f1bbef4f2b926294a7dd4c7865715502a115bd0c7407792db5` | `3d5f4cc8f10a1e78d51ce7ccfe8b06263002b521590a0165d952da1f9163eafb` |
| `publication_v2/stage2/tests/test_forecasting.py` | `b5cf3a30295975fab7ce8979db2c458cf6ebe3211a1cb9abd89c0caf05b42288` | `6b13da81fbefd25062134f0553bcdf6d6d4e95374024913eda457dc6e40c663f` |
| `publication_v2/stage2/tests/test_metrics.py` | `c4b6d18b0be66a482f5ff360ba7551a248e575aad3fc9b6f9fb73325486a6f7c` | `a1f35f03d952d89c1bd75d20549c51a7e1b6ae0f76e9f30f4088c5d46a5f5fb9` |
| `publication_v2/stage2/workflow.py` | `25222a9e8d6688af5565e9075fbea4c54335ca03526eb81359c0d61dd6b86e28` | `39349b7ce039811bd1615257fc91cecc64f56646466fde7b493739d190857ff4` |


## Appendix B. Exact excluded staged paths — 164 retained entries

Exclusion from proposed code commits is not deletion, publication approval or a judgment that the work has no value. All entries remain staged as found.

### Current dashboard: 27

```text
.streamlit/config.toml
app/context.py
app/dashboard.py
app/platform_data.py
app/research_data.py
app/routes.py
app/screens/battery.py
app/screens/command_center.py
app/screens/digital_twin.py
app/screens/forecasting.py
app/screens/grid.py
app/screens/mpc.py
app/screens/reproducibility.py
app/screens/results.py
app/ui.py
app/views/battery.py
app/views/forecasting.py
app/views/grid.py
app/views/mpc.py
app/views/operations.py
app/views/research.py
docs/windgrid_platform_guide.md
requirements-dashboard.txt
scripts/verify_windgrid_platform.py
tests/test_dashboard.py
tests/test_platform_data.py
tests/test_windgrid_ui.py
```

### Historical audits/backups: 38

```text
audits/publication_readiness_20261029/audit_checks.py
audits/publication_readiness_20261029/chronology_and_statistics.json
audits/publication_readiness_20261029/chronology_checks.py
audits/publication_readiness_20261029/fresh_solver_replay.json
audits/publication_readiness_20261029/independent_evidence.json
audits/publication_readiness_20261029/protected_sha256_before_after.json
audits/publication_readiness_20261029/replay_checks.py
audits/publication_readiness_20261029/report.md
audits/publication_readiness_20261029/supplementary_evidence.json
audits/research_completion_20261029/immutable_baseline.json
audits/research_completion_20261029/model_metadata_summary.json
audits/research_completion_20261029/package_manifest.json
audits/research_completion_20261029/prior_documentation/.gitignore
audits/research_completion_20261029/prior_documentation/README.md
audits/research_completion_20261029/prior_documentation/methodology.md
audits/research_completion_20261029/prior_documentation/reproducibility.md
audits/research_completion_20261029/verification_evidence.json
audits/research_completion_20261029/verification_evidence_final.json
audits/research_grade_20261029/executed_sources_pilot/configs/mpc_research_v1.json
audits/research_grade_20261029/executed_sources_pilot/reconstruction_log_partial.json
audits/research_grade_20261029/executed_sources_pilot/scripts/run_controller_benchmarks_v1.py
audits/research_grade_20261029/executed_sources_pilot/src/windresearch/experiments.py
audits/research_grade_20261029/executed_sources_pilot/src/windresearch/mpc.py
audits/research_grade_20261029/executed_sources_pilot/src/windresearch/protocol.py
audits/research_grade_20261029/prior_documentation/.gitignore
audits/research_grade_20261029/prior_documentation/README.md
audits/research_grade_20261029/prior_documentation/methodology.md
audits/research_grade_20261029/prior_documentation/requirements-research.txt
audits/windgrid_dashboard_20261029/prior_version/README.md
audits/windgrid_dashboard_20261029/prior_version/app/dashboard.py
audits/windgrid_dashboard_20261029/prior_version/app/research_data.py
audits/windgrid_dashboard_20261029/prior_version/requirements-dashboard.txt
audits/windgrid_dashboard_20261029/prior_version/requirements-research.txt
audits/windgrid_dashboard_20261029/prior_version/tests/test_dashboard.py
audits/windgrid_dashboard_20261029/protected_baseline.json
audits/windgrid_dashboard_20261029/server_20261029T1954220433804Z.stderr.log
audits/windgrid_dashboard_20261029/server_20261029T1954220433804Z.stdout.log
audits/windgrid_dashboard_20261029/validation_report.json
```

### Historical research/scripts/docs/results/tests: 96

```text
docs/completion_figures/control_minus_uncontrolled_by_block.pdf
docs/completion_figures/control_minus_uncontrolled_by_block.png
docs/completion_figures/event_adaptive_one_sided_largest_improvement.pdf
docs/completion_figures/event_adaptive_one_sided_largest_improvement.png
docs/completion_figures/event_adaptive_one_sided_largest_worsening.pdf
docs/completion_figures/event_adaptive_one_sided_largest_worsening.png
docs/completion_figures/event_fixed_largest_improvement.pdf
docs/completion_figures/event_fixed_largest_improvement.png
docs/completion_figures/event_fixed_largest_worsening.pdf
docs/completion_figures/event_fixed_largest_worsening.png
docs/completion_figures/gross_ramp_changes.pdf
docs/completion_figures/gross_ramp_changes.png
docs/completion_figures/ramp_attribution_and_prediction.pdf
docs/completion_figures/ramp_attribution_and_prediction.png
docs/completion_figures/soc_inventory_diagnostic.pdf
docs/completion_figures/soc_inventory_diagnostic.png
docs/completion_tables/block_diagnostic_metrics.csv
docs/completion_tables/development_vs_evaluation.csv
docs/completion_tables/diagnostic_provenance.json
docs/completion_tables/operating_mode_diagnostics.csv
docs/completion_tables/paired_block_differences.csv
docs/completion_tables/ramp_event_summary.csv
docs/completion_tables/segment_paired_differences.csv
docs/completion_tables/temporal_dependence_descriptive.csv
docs/environment-frozen-evaluation.txt
docs/figures/battery_energy_accounting.pdf
docs/figures/battery_energy_accounting.png
docs/figures/first_block_trace.pdf
docs/figures/first_block_trace.png
docs/figures/forecast_accuracy.pdf
docs/figures/forecast_accuracy.png
docs/figures/paired_controllers.pdf
docs/figures/paired_controllers.png
docs/figures/paired_differences.pdf
docs/figures/paired_differences.png
docs/figures/uncertainty_coverage.pdf
docs/figures/uncertainty_coverage.png
docs/figures_v2/battery_energy_accounting.pdf
docs/figures_v2/battery_energy_accounting.png
docs/figures_v2/first_block_trace.pdf
docs/figures_v2/first_block_trace.png
docs/figures_v2/forecast_accuracy.pdf
docs/figures_v2/forecast_accuracy.png
docs/figures_v2/paired_controllers.pdf
docs/figures_v2/paired_controllers.png
docs/figures_v2/paired_differences.pdf
docs/figures_v2/paired_differences.png
docs/figures_v2/uncertainty_coverage.pdf
docs/figures_v2/uncertainty_coverage.png
docs/final_verification_report.md
docs/grid_ramp_diagnostic.md
docs/heldout_results.md
docs/heldout_results_v2.md
docs/limitations.md
docs/literature_review.md
docs/literature_verified.json
docs/mathematical_formulation.md
docs/paper_draft.md
docs/paper_submission_draft.md
docs/reproducibility.md
docs/tables/aggregate_metrics.csv
docs/tables/block_metrics.csv
docs/tables/forecast_metrics.csv
docs/tables/paired_differences.csv
docs/tables/paired_summary.csv
docs/tables/uncertainty_coverage.csv
docs/tables/uncontrolled_wind_baseline.csv
docs/tables_v2/aggregate_metrics.csv
docs/tables_v2/block_metrics.csv
docs/tables_v2/forecast_metrics.csv
docs/tables_v2/paired_differences.csv
docs/tables_v2/paired_summary.csv
docs/tables_v2/uncertainty_coverage.csv
docs/tables_v2/uncontrolled_wind_baseline.csv
docs/unresolved_scientific_issues.md
scripts/analyse_frozen_heldout.py
scripts/audit_frozen_reproducibility.py
scripts/build_completion_diagnostics.py
scripts/build_submission_package.py
scripts/causal_adaptive_grid_priority_mpc_development.py
scripts/causal_adaptive_uncertainty.py
scripts/causal_one_sided_grid_priority_mpc_development.py
scripts/causal_one_sided_uncertainty.py
scripts/finalise_frozen_research.py
scripts/frozen_adaptive_one_sided_heldout.py
scripts/frozen_fixed_heldout.py
scripts/heldout_support.py
scripts/prepare_frozen_heldout.py
scripts/run_frozen_heldout.py
scripts/run_matched_mpc_development_batch.py
scripts/uncertainty_grid_priority_tolerance_development.py
scripts/uncertainty_reserve_penalty_sensitivity_development.py
scripts/verify_research_completion.py
tests/test_completion_diagnostics.py
tests/test_frozen_heldout.py
tests/test_heldout_accounting.py
```

### Historical documentation backups: 2

```text
documentation_backups/README_before_frozen_heldout_20261029.md
documentation_backups/README_before_step229_20261028_160246_8307925.md
```

### Older Stage 1 extra log: 1

```text
publication_v2/evidence/stage1_tests_stdlib.log
```


## Audit evidence

Task-start inventory, working/index hashes, raw index copy, test logs/summaries, saved-table arithmetic and final preservation record are in `C:/Users/arqam/AppData/Local/Temp/wind_stage25_09bsw6iv/`. Temporary files may expire; they are not a durable backup. Original Stage 1/2.1/2.3/2.4 reports remain unchanged. This report records new validation separately.
