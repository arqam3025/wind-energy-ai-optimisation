# Publication v2 — Stage 1 report

Prepared 1 November 2026. Branch: `research/publication-v2`, based on `2b49e7a`. **Stage 1 is implemented and verified; confirmatory testing is `BLOCKED_CONFIRMATORY_TEST`.** No untouched split is proposed, no new forecasting or MPC algorithm is implemented, and no new efficacy result or journal-readiness claim is made.

The starting documents were [RESEARCH_AUDIT.md](RESEARCH_AUDIT.md), [RESEARCH_GRADE_REPRODUCIBILITY.md](RESEARCH_GRADE_REPRODUCIBILITY.md), [EXPERIMENTAL_RESULTS.md](EXPERIMENTAL_RESULTS.md) and [PUBLICATION_READINESS.md](PUBLICATION_READINESS.md). They remain unchanged. The normative new contract is [PUBLICATION_V2_PROTOCOL.md](PUBLICATION_V2_PROTOCOL.md); subsequent work is gated by [PUBLICATION_V2_STAGE2_PLAN.md](PUBLICATION_V2_STAGE2_PLAN.md).

## Scope and preservation

All new implementation lives under `publication_v2/`, with three new documents under `docs/`. The original models, raw/processed data, calibration, manifests, historical scripts and original results were only read. The new [preservation baseline](../publication_v2/preservation_baseline.json) protects **2,131 pre-existing research files**, including ignored local results and previously untracked work. Before/after checks pass; no protected file changed. The original freeze digest remains:

```text
b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a
```

All **59 referenced frozen artifacts** match. Integrity checks use exceptions and remain active under `python -O`; a corruption fixture exercises that mode. No historical script was cleaned, rewritten or retrained. Stage 1 reconstructs existing timestamp/value joins and archived arithmetic, without loading a predictor or invoking an MPC study. Existing regression tests continue to test existing code, including solver fixtures.

## Available inputs and chronological inventory

The [versioned CSV inventory](../publication_v2/evidence/chronological_inventory.csv) profiles **87 CSV artifacts**, including timestamped datasets and calibration summaries with explicitly absent timestamp columns. It records hashes, origin ranges, inferred target ranges, historical roles, duplicates, gaps and missing values. There are **seven saved model artifacts**, including the six direct-horizon XGBoost files. Their hashes are recorded; no model is fitted or inferred. The completed audit authenticates **204 input artifacts** and has **zero missing required local inputs**. Public acquisition/reproduction remains incomplete because the supplied local bundle includes ignored and untracked historical artifacts.

The raw SCADA file contains **50,530 rows**, from `2018-01-01 00:00` to `2018-12-31 23:50` in an unresolved source clock: zero duplicated timestamps, **32 gaps and 2,030 absent ten-minute slots**. No gap is filled or reinterpreted as zero output. A local checksum identifies this exact file; it does not establish its upstream release version or acquisition history.

Structural reconstruction passes for:

| Check | Actual completed scope |
| --- | ---: |
| Saved feature-table rows | 50,320 ten-minute-feature rows and 50,125 six-horizon rows |
| Feature value/source-support comparisons | 1,406,230 |
| Raw target value/timestamp joins across the two feature tables | 401,195 |
| Saved forecast tables | 72 |
| Saved forecast-origin rows | 32,272 |
| Saved six-horizon target pairs | 193,632 |
| Archived controller target-alignment rows | 14,112 across 98 traces |
| Strict logged newest-residual-target checks | 7,056 adaptive decisions |

These are counts of checks, not independent statistical samples. All fourteen feature formulas are reconstructed using timestamp joins, including complete lag/mean support; no positional shift crosses a gap. Six targets join to the corresponding raw measurement at origin plus the named horizon. Prepared evaluation-block current power is clipped at zero; raw/features and the original saved forecast-table current power retain signed measurements. Persistence predictions and actual forecast targets are nonnegative. Source preparation scripts authenticate this distinction; it is not a new preprocessing choice.

Actual forecast issue, observation receipt, residual-computation and historical model-fitting availability times are not recorded. Passing structural checks therefore **does not certify operational information availability or absence of all historical leakage**. The new normative validator requires those records and rejects unknown/naive operational timestamps rather than guessing them.

## Historical exposure and boundary findings

[Exposure/provenance evidence](../publication_v2/evidence/exposure_and_provenance.json) distinguishes confirmed historical access/roles from unknown access and unestablished selection influence. Source-file existence, file modification time, absence of a saved score, and an uncovered calendar interval are not non-exposure attestations.

- Prior raw/full-feature audits inspected the available source artifacts. Git history also records pre-freeze investigations of evaluation blocks 25 and 34. All 49 original scheduled evaluation blocks have since been scored and examined. They are retrospective.
- The first development episode starts at `2018-10-15 11:00`. Static calibration has **21 affected horizon/decision cells across six decisions**, containing **56 repeated unavailable-label/decision pairs**. Equal-time calibration labels are counted as ineligible. The historical calibration is not replaced.
- Schedule-designated development block **6** shares **15 cross-horizon target pairs and five scored h1 target timestamps** with evaluation block 7. Its evaluation-style filename does not establish test eligibility.
- The full `multistep_controller_development_split.csv` contains **2,990 origins** through `2018-11-05 15:00`, with an inferred h6 target through `16:00`. Its development-labelled tail shares another **15 pairs and five scored h1 timestamps** with evaluation block 1. This artifact's existence and role exposure are confirmed; use of that tail in frozen-controller selection is **not established**. It is distinct from the eighteen complete controller-development episodes.
- The union of these declared development sources shares **30 evaluation horizon-target pairs and ten scored h1 timestamps**. No observation is silently deleted to repair this history.

**Decision: `BLOCKED_CONFIRMATORY_TEST`; proposed untouched split: `null`.** This does not prove that every measurement was read by a human. It means no eligible local interval has affirmative, reviewable evidence of independent reservation and non-exposure. Unscored or unlisted rows remain exposure-unknown.

## Required additional data and provenance

Stage 2 confirmation needs an independently reserved, genuinely uninspected future period or different turbine/site, with verifiable custody/access records and a freeze predating outcome access. It must supply the required power, wind-speed and direction inputs at documented ten-minute cadence, **at least 60 minutes of feature lookback before the first origin and 60 minutes of target support after the last origin**. Study duration must be justified prospectively using development-only dependence/power assessment; the old 49-block count is not a prospective sample-size justification.

Required missing evidence remains explicit:

| Blocker | Evidence required to resolve it |
| --- | --- |
| `BLOCKED_CONFIRMATORY_TEST` | Disjoint source/period, custodian, access/reservation log, non-exposure attestation and preregistered release conditions |
| `UNKNOWN_DATASET_VERSION` | Exact upstream release/download identity, acquisition record and file hashes |
| `UNKNOWN_TIMEZONE` | Source timezone/offset/DST, clock synchronization, timestamp and measurement-window semantics |
| `UNKNOWN_MEASUREMENT_AVAILABILITY` | Measurement receipts, feature computation, forecast issuance and residual availability records |
| `UNKNOWN_DATA_LICENSE` | Actual acquisition/use/redistribution terms or explicit permission |
| `UNATTESTED_HISTORICAL_MODEL_FIT` | Fitting/preprocessing/selection data-access ledger and model availability, linked to hashes |
| `CLEAN_ENVIRONMENT_NOT_REPLICATED` | Reproduction from legally accessible inputs in a separate clean environment/checkout |

The repository-documented source URL/attribution is retained, without treating it as a download or licence attestation. Active power in kW, wind speed in m/s and direction in degrees are documented by source headers. The theoretical-curve header says `KWh`, its physical meaning is unresolved, and it is not used by the frozen feature set. Installed Python **3.12.5** and the ten declared research-package versions are captured and match the existing requirements. This is installed-environment evidence, not a successful fresh installation. Stage 1 itself needs only the Python 3.12 standard library.

## New protocol and runner behaviour

`publication_v2/protocol.py` requires explicit, offset-aware event/receipt/availability timestamps. Every source event precedes its receipt; every receipt precedes feature availability; features are available by the origin. Issuance follows the origin and precedes the decision, which precedes the correctly aligned target. Model training targets precede the origin and model availability must support issuance. Each record carries a declared grid anchor; calibration records must share an anchor.

Calibration requires both **`target_time < decision_time`** and actual observation/residual availability by the decision. Equal/future targets, late receipts/computations, duplicate identities and missing support fail. Horizon-specific embargo retains only targets strictly before the next role's first decision. Static partitions reject target intersections across **all** horizons. A prespecified online residual update is checked decision by decision; it does not authorize retuning or make successive test outcomes independent.

The [static experiment manifest](../publication_v2/experiment_manifest.json) fixes Stage 1/no-algorithm scope. The runner checks its exact timing rules, hashes configuration/source/inputs/models, creates unique exclusive paths and verifies preservation before/after. It publishes audit JSON with fsync plus an atomic exclusive hard link; there is no overwrite fallback on unsupported filesystems. Partial, interrupted, stale, missing or corrupt runs cannot be consumed as completed. Symlinks and Windows junctions, including ancestor redirection within the repository, are rejected before creation or reading.

The authoritative local run is `publication_v2/runs/stage1_20261101_002/`. Its authenticated completion records `AUDIT_COMPLETED`, `BLOCKED_CONFIRMATORY_TEST` and `experiment_executed: false`. Confirmatory preflight exits **2** and lists the seven blockers. The earlier `_001` audit remains local; subsequent junction hardening changed its source identity, and the current verifier correctly rejects it as stale. It is not reused or overwritten. Local runs are ignored by Git; the smaller evidence files retain the final manifest digest and findings.

## Tests, commands and failure history

| Executed suite | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| Stage 1, with site-packages disabled (`-S`) | **58** | **0** | **1** |
| Existing research/dashboard regressions | **71** | **0** | **0** |

The skip is a real Windows symlink-creation fixture: this account lacks the required OS privilege. Separate privilege-free mocked symlink, dangling-marker and junction checks pass. Atomic interruption, existing/partial run, changed configuration, missing input, corrupted model/input/output, wrong environment, foreign-root source identity and blocked-versus-completed semantics are tested. Synthetic fixtures never become research observations.

The first development test run had one failing fixture: it removed a raw timestamp that was not actually required by the chosen feature window. The fixture was corrected to remove a required timestamp; the missing-source check now passes. Initial structural smoke checks also exposed the need to distinguish signed saved current power from clipped prepared evaluation current power. Only the new checker was corrected, with a signed-feature regression fixture; no historical data or score changed. Final evidence is [stage1_validation.json](../publication_v2/evidence/stage1_validation.json), [Stage 1 test log](../publication_v2/evidence/stage1_tests_stdlib_final.log) and [existing regression log](../publication_v2/evidence/regression_tests.log).

From the repository root, choose an unused run ID:

```powershell
.venv/Scripts/python.exe -S -B -m unittest discover -s publication_v2/tests -v
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
.venv/Scripts/python.exe -B -m publication_v2.runner audit --run-id my_unique_stage1_run
.venv/Scripts/python.exe -B -m publication_v2.runner preflight --run publication_v2/runs/my_unique_stage1_run
```

The `-S` run demonstrates standard-library-only fixtures in this interpreter; it is not a fresh OS/clone reproduction. Missing historical bundle files fail explicitly rather than being synthesized. Completed audit consumption rechecks identities and the environment. No runner command trains, forecasts, optimizes or evaluates a new controller.

## Archived negative comparison retained

Recomputation uses the original 49 episodes, 144 transitions per episode, initial origin-to-first-output ramp, no cross-episode transition, 200 kW exceedance threshold and `>200.001 kW` violation convention:

| Original retrospective case | Violations | Summed exceedance (kW) |
| --- | ---: | ---: |
| Uncontrolled wind | 1,465 | 317,210.288 |
| Frozen fixed-margin MPC | 1,502 | 326,158.296 |
| Frozen adaptive one-sided MPC | 1,486 | 323,638.526 |

Both controllers have worse aggregate counts/exceedance than uncontrolled wind. This remains visible and unchanged; Stage 1 claims no improved metrics, compliance or efficacy.

## Changed files and next stage

Only Stage 1 paths are committed. Existing untracked dashboard/research work is retained without staging it.

| New path | Purpose |
| --- | --- |
| `publication_v2/protocol.py` | Typed causal chronology, feature/receipt lineage, calibration, embargo and split checks |
| `publication_v2/temporal_audit.py` | Read-only feature/target/archived-timestamp and arithmetic reconstruction |
| `publication_v2/inventory.py`, `metadata.json` | Chronological artifact/exposure inventory and explicitly incomplete provenance |
| `publication_v2/integrity.py`, `preservation_baseline.json` | Original freeze and complete pre-existing workspace preservation |
| `publication_v2/runner.py`, `experiment_manifest.json` | Versioned fail-closed audit lifecycle; no Stage 2 execution |
| `publication_v2/tests/` | Five standard-library test modules |
| `publication_v2/evidence/` | Final aggregate inventory, exposure/provenance, test/preflight logs and validation summary |
| `publication_v2/__init__.py`, `.gitattributes`, `.gitignore`, `requirements.txt` | Isolated package, byte-stable provenance, local-run exclusion and dependency scope |
| Three `docs/PUBLICATION_V2_*.md` files | Stage 1 report, normative protocol and gated Stage 2 plan |

Stage 2 must first resolve custody/non-exposure and provenance, then freeze a lawful data/split/analysis plan before access. Only a separately authorized implementation may add forecast/control adapters and evaluate them. Existing retrospective evidence may support development and diagnostics; it cannot supply independent confirmation. No merge to `main` or push is part of Stage 1.
