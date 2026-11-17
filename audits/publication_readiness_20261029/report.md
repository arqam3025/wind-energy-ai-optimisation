# Publication-readiness audit

Audit date: 29 October 2026. Scope: the complete paper draft, methodology, limitations, reproduction guide, both frozen evaluation implementations, uncertainty module, runner, finaliser, eight tests, stored traces, calibration, current models, raw measurements, Git changes and reachable Git history.

**Verdict: the numerical comparison is reproducible locally, but the study is not ready to present as an independent confirmatory held-out experiment or as demonstrated ramp mitigation. A public research release also needs preparation.** It can support a carefully qualified retrospective empirical comparison. This audit independently implemented the numerical and chronology checks; it is not external peer review or an independent-personnel replication of work previously performed in this chat.

No frozen source, model, dataset, manifest, existing result, paper or README was changed. New audit code, evidence and isolated first-block replay files are confined to this audit directory. A 1,045-file before/after inventory covers existing research artifacts, excluding caches and Git internals.

## Verified findings

| Check | Audit result |
| --- | --- |
| Freeze SHA256 | Exact match: `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a` |
| Frozen references | All 59 source/development-result hashes match |
| Main evaluation provenance and release v2 | All listed hashes match |
| Independent recomputation | All 98 controller-block traces checked; headline metrics reproduced |
| Causal uncertainty | All 42,336 decision/horizon margins independently reconstructed using targets strictly before the decision; maximum margin difference approximately 1.14e-13 kW |
| Raw targets | All 42,336 horizon-target comparisons match clipped measurements |
| Forecast features | Current/past raw lookups reproduce all 14 features; maximum discrepancy approximately 1.36e-12 |
| Current model inference | Six loaded models reproduce stored forecasts to within 0.000122 kW; no training or model saving performed |
| Fresh solver replay | First block rerun for both controllers: zero numeric difference, all nonnumeric fields identical |
| Existing tests | Eight tests pass |
| Protected artifacts | 1,045 inventoried files unchanged |

The audit recalculated all aggregate metrics from traces, rather than trusting the analysis tables or reusing the existing metric function. Fresh solver execution covered block 1 only, not all 49 blocks. Current inference agreement does not independently prove which observations were used during historical model training.

## Critical issues

### C1. Test-blind independence is not established, and the development exclusion misses target overlap

There are two distinct problems.

**Prior test inspection is documented.** Commit `bcb2c99`, dated 28 October 2026 at 15:52:17 UTC, includes `scripts/inspect_block_25_event.py` and `scripts/inspect_block_34_forecasts.py`. These investigate outcomes and forecast/SOC behaviour in evaluation blocks 25 and 34. The freeze was created on 29 October 2026 at 13:52:05 UTC, after those scripts had entered the repository. This proves pre-freeze test-period investigation code existed; it does not prove exactly which final parameter choices were influenced by those investigations. A subsequent hash freeze cannot restore a never-inspected test set. The manifest's historical declarations `held_out_test_status: untouched` and “No held-out performance has been examined” must not be treated as independent evidence of blindness. The paper already acknowledges historic access, which is appropriate, but the prominent “held-out” framing still needs tighter qualification.

**Block 6 exclusion is incomplete at target level.** Its final forecast origin is 15 November 2018 at 12:50. Its six-horizon development targets extend to 13:50. Block 7 starts at 13:00. Five measured target timestamps—13:10, 13:20, 13:30, 13:40 and 13:50—occur in both block 6's development targets and block 7's scored targets. This affects **15 block-7 horizon-target pairs and five actual h1 control outcomes**.

`scripts/heldout_support.py:26` loads only the eighteen earlier `controller_development_blocks` for its overlap check. The check at line 38 omits the schedule-designated development block 6. Thus preflight passes without establishing development/test target disjointness. Additionally, scored blocks 1–5 precede the known development period in block 6, so the full legacy development/evaluation allocation is not a strictly development-then-test chronological sequence.

**Consequence:** do not describe the 49-block result as a clean, untouched, target-disjoint confirmatory test. Distinguish researcher/model-selection exposure from runtime leakage: the audit found no runtime use of future residuals or future forecasting features. Past block-6 residuals are legitimate online history after their target times; that does not erase its separate development-use overlap.

**Required decision:** either explicitly position the existing experiment as retrospective frozen-controller evaluation, or approve a new prospective validation protocol on genuinely untouched data. Any purge/embargo or altered scored set must be a separately declared analysis with new filenames; do not silently replace the published headline numbers. An embargo alone cannot undo historical test access.

### C2. Both controllers worsen the stated aggregate ramp outcomes relative to uncontrolled wind

Independent recomputation gives:

| Strategy | Violations | Summed exceedance (kW) | Exceedance versus uncontrolled |
| --- | ---: | ---: | ---: |
| Uncontrolled wind | 1,465 | 317,210.288 | Reference |
| Frozen fixed margin | 1,502 | 326,158.296 | +2.82% |
| Frozen adaptive one-sided | 1,486 | 323,638.526 | +2.03% |

Adaptive improves on fixed, but has **21 more violations than uncontrolled wind**; fixed has 37 more. The baseline is already disclosed in the results at `docs/paper_draft.md:79`, so this is not a hidden arithmetic error. Its implication is insufficiently prominent in the abstract, discussion and conclusion.

**Consequence:** the experiment demonstrates reduced battery use relative to another battery controller; it does not demonstrate improvement over no battery in these two aggregate ramp metrics. It may remain a useful negative or mixed research finding. Mean/max ramps are different outcomes and cannot substitute for the failed exceedance/count comparison.

**Required clarification:** explicitly discuss why both forecast-informed controllers can worsen realised ramp outcomes, and restrict efficacy claims accordingly. Diagnosis or a redesigned controller would be new work requiring a declared protocol, not an audit fix.

### C3. The repository is not yet a complete reproducible public release

At the audited `main` HEAD (`2160ff3`), the new controller implementations, uncertainty modules, paper, analysis, tests and figures are untracked. A normal push of current `main` would omit them. Local Codex checkpoint refs contain additional snapshots, but they are not a substitute for a deliberate release commit/tag.

The freeze manifest, schedule, calibration, per-interval traces and datasets are ignored by Git. `heldout_support.py:8` reads an ignored schedule at import, so even the synthetic test suite cannot be imported in a fresh clone without local research artifacts. `requirements.txt` lacks CVXPY/HiGHS, although the separate environment snapshot includes them and the reproduction guide acknowledges this. There is no archival artifact bundle or documented retrieval mechanism that makes the full published result independently executable from a clone.

**Required release preparation:** curate an explicit release commit, identify the authoritative v2 documents, provide a permissible versioned artifact archive/checksums or a clearly documented restricted-access procedure, and document a clean-environment installation. Do not indiscriminately add ignored raw data or force-add results. No staging, commit, push, deletion or history rewrite was performed by this audit.

## Moderate issues

### M1. Statistical dependence is acknowledged but not accommodated by the bootstrap

`scripts/analyse_frozen_heldout.py:120–125` independently resamples the 49 daily block indices. This preserves within-day pairing but assumes exchangeable days; it is not a moving-block, stationary or dependence-aware bootstrap. Calling these intervals descriptive and declining confirmatory significance claims is appropriate. That caveat does not turn them into valid dependence-adjusted confidence intervals.

The independently reproduced intervals for **mean paired block differences** are:

| Outcome | Descriptive 2.5–97.5% resampling bounds |
| --- | ---: |
| Throughput (kWh/block) | -295.178 to -110.666 |
| Ramp exceedance (kW/block) | -140.935 to +33.772 |
| Violation count (per block) | -0.980 to +0.286 |

These are not intervals for the reported percentage reductions. Neither the 0.77% nor the 16-count reduction has demonstrated confirmatory statistical significance. The four segment-level paired violation differences are +2, +4, -5 and -17: the total benefit is not uniform over chronology. There are only four contiguous segments, so treating those as four independent clusters would also have substantial limitations.

Recommendation: keep the present analysis descriptive. A separately approved dependence-aware uncertainty analysis could supplement it, with explicit sampling unit, estimand and block-length rationale. Do not tune its design to obtain a favourable interval.

### M2. Mechanical fairness is sound, but the experiment does not isolate adaptation

Both controllers use identical forecast inputs, episodes, initial energy, power/SOC bounds, efficiencies, scenario weights, objective coefficients, solver interface and primary allowance. The optimisation/execution bodies match their frozen sources. Online use of already-observed test residuals is legitimate for a declared adaptive algorithm and is not itself unfair training on the test set.

However, the comparison changes **absolute versus signed residuals, fixed versus rolling calibration, and static floor values** together. Adaptive margins equal their static floors for approximately **86–88% of decisions at every horizon**; none of the evaluated fallback flags is active. Consequently, the throughput difference cannot be attributed specifically to rolling adaptation or the gap fallback.

The paper correctly acknowledges the bundled difference at `docs/paper_draft.md:130`. Retain that qualification in the contribution statement. Do not claim the adaptive component alone is responsible without development-designed ablations and a new evaluation protocol. Also document the derivation of the legacy adaptive floors: they are preserved constants but are not the current calibration file's signed 90% quantiles (approximately 246.724 through 491.111 kW). That discrepancy does not prove the constants are wrong or test-derived; their statistical provenance remains insufficiently documented.

### M3. Originality is plausible as an empirical MSc integration study, not established as a new algorithm

The actual contribution statement is appropriately narrow: a traceable empirical comparison rather than a new coverage theorem. However, the six-item bibliography has no substantive review of prior wind–battery MPC, probabilistic dispatch or lexicographic storage control. The combination of established components is not enough to establish algorithmic novelty.

Relevant primary sources found in this audit include:

- [Khalid and Savkin, wind-power smoothing with controlled battery MPC (2010)](https://www.sciencedirect.com/science/article/abs/pii/S0960148109005175), including multi-step predictions, SOC and ramp constraints.
- [Kou, Gao and Guan, probabilistic wind forecasts in stochastic battery MPC (2015)](https://www.sciencedirect.com/science/article/pii/S0960148115000919).
- [Tziovani and colleagues, lexicographic predictive storage control (2021)](https://zenodo.org/records/4888894), prioritising constraint violations and losses in a different storage application.
- [Physics-Informed Adaptive Conformal Prediction for Wind Power Under Dynamic Weather Regimes (2026)](https://ieeexplore.ieee.org/document/11353259/), relevant to claims about conformal wind forecasting.

These sources establish that the component ideas predate this work; they do not establish that every detail of this exact implementation has appeared before. The search is bounded, not an exhaustive novelty or plagiarism certification. Add a related-work comparison specifying what is reused, modified and empirically contributed. Avoid “first”, new distribution-free guarantees, or a generally superior new MPC algorithm without stronger evidence.

### M4. Equations are consistent with the code but incomplete for publication

The reported power balance, energy update, conversion losses, terminal restoration accounting and rank `ceil(145*0.9)=131` are mathematically consistent with the implementation. No correction to those reported equations or headline totals was identified.

The paper needs a self-contained formulation or formal appendix: indexed primary/secondary objectives; exceedance and reserve-shortfall constraints; charge/discharge binaries; shared requested versus realised first actions; exact minimum/Big-M relations and their bounds; scenario probabilities; boundary export; and all coefficient units. Methods prose and a link to code do not fully specify the mixed-integer model for a journal reader.

Explain that the six-step **optimisation horizon** and two **objective-priority solves** are different notions of stages. Later scenario-dependent actions also imply a scenario-fan recourse assumption; they should not be described as a fully nonanticipative multistage policy. This is optimistic planning recourse, not evidence that the simulator reads future actuals.

The 100 kW aggregate primary allowance is substantive, not merely solver numerical tolerance. Frozen comments calling it “numerical tolerance” are misleading, although the current paper explains the allowance correctly. A 200 kW ten-minute power change is a discrete ramp threshold, equivalent to 20 kW/min under that averaging convention—not 200 kW/min. Document the interpretation of SCADA timestamps/ten-minute samples when integrating power into energy, and the ideal wind-limited intra-interval fallback.

### M5. Reporting and runner safeguards are weaker than the completion claims suggest

- At `scripts/run_frozen_heldout.py:40`, any existing CSV is skipped without checking row count, output hash or completeness. Partial/stale files can therefore be skipped. Subsequent analysis catches many physical errors but does not authenticate that every existing output came from the recorded run. Exclusive file creation does not make CSV writes atomic.
- `COMPLETE` is printed even for a one-block `--blocks` run. It means the requested subset finished, not necessarily all 49 pairs.
- Many freeze, eligibility and physical checks use Python `assert`, which is disabled under `python -O`. The documented default invocation does not disable them, but they are not robust production integrity guards.
- The finaliser writes README and copies artifacts before all of its checks complete. Its assertions at lines 96–98 require specific observed MAE/RMSE ordering and a zero-spanning ramp interval. Those are result-contingent narrative assumptions, not scientific validity checks. They do not invalidate the current arithmetic, but prevent neutral report generation for contrary future outcomes.
- Solver stage objectives, optimality gaps, solve times and detailed per-decision solver diagnostics are not stored in the CSVs. Successful guarded execution is useful evidence, but does not support a deployment-runtime claim or an independent audit of every optimisation certificate.

Recommend separate, versioned engineering changes after approval; none were made here.

### M6. Tests and provenance are useful but not a complete leakage or reproducibility proof

The eight tests check the intended causal boundary, frozen-body equality and selected accounting errors. They do not test block-6 target overlap, complete end-to-end future-outcome intervention, window/fallback boundary cases, corrupted resume files, or clean-clone execution. The body-equality test begins at nominal-forecast construction and excludes initialization/history loading; manual inspection and independent reconstruction are needed in addition.

Current models reproduce stored forecasts and causal feature lookups. The historical training script uses the intended early cutoff. Nevertheless, no independently attested training run record proves those weights were fitted only on that split. Record model/source/input hashes and training metadata without retraining the frozen study. The adaptive floors and original data acquisition/version also need explicit provenance.

The v2 release manifest verifies completely. The v1 release manifest has four stale live-path hashes: paper, README, analysis script and finaliser. This is consistent with later v2 revisions, not evidence of altered frozen controllers. Label v1 as superseded and preserve version-specific source/document snapshots rather than expecting old manifests to verify against evolving live paths.

### M7. Git publication safety is conditional

No AWS-access-key, GitHub-token, OpenAI-key or private-key pattern matches were found in scanned text candidates or reachable Git history. No raw data/models/results are tracked in current `main`, and none of the inspected historical object paths indicates raw-data/model/credential exposure. This is a bounded pattern scan, not a guarantee that no secret or sensitive information exists. Git author metadata and deliberately public author identity were not anonymised.

The ignore rules cover `.env`, data, models and results, but do not cover example credential-bearing names `.env.local`, `.aws/credentials` or `sample.pem`. No such actual exposed credential file was identified; add suitable preventative rules only as a separately reviewed change. Do not rely on `.gitignore` to remove anything already in history. Publish a curated branch/tag rather than blindly mirroring custom internal refs.

There is no project licence, and dataset version/redistribution terms remain unverified in the paper. The [dataset landing page](https://www.kaggle.com/datasets/berkerisen/wind-turbine-scada-dataset) is reachable but did not expose sufficient machine-readable licence/version information during this audit. Do not claim clearance to redistribute the raw data. Review rights for source, figures, derived tables and any artifact bundle before release.

## Reference and result checks

The XGBoost, conformal tutorial, Gibbs–Candes ACI and CVXPY references resolve to matching primary titles/authors. The [HiGHS site](https://highs.dev/) supports its requested Huangfu–Hall citation; that article concerns LP simplex rather than the whole MIP solver, as the paper already explains. The preprint-style tutorial citation is valid but can be normalised to the chosen venue's bibliography format. No fabricated reference was identified among the six entries. The larger problem is missing domain-related work, not nonexistent citations.

Reproduced official results, unchanged by this audit:

| Metric | Fixed | Adaptive one-sided |
| --- | ---: | ---: |
| Throughput (kWh) | 35,486.897869 | 25,598.676938 |
| Ramp exceedance sum (kW) | 326,158.295976 | 323,638.525601 |
| Violations | 1,502 | 1,486 |
| Conversion losses (kWh) | 1,821.593485 | 1,312.915942 |

The reductions are **27.8644275%**, **0.7725606%**, and **16 violations**, respectively. Adaptive actual export is **0.987701 MWh lower**, while hypothetical terminal-adjusted export is **0.551229 MWh higher**. The latter is not realised export, free energy, or a feasible simulated restoration schedule. XGBoost has lower RMSE but higher MAE than persistence at all six horizons; the paper correctly reports this mixed result.

## Recommended order of work

1. Resolve the scientific positioning: retrospective comparison versus a new genuinely untouched evaluation. Document the block-6/block-7 overlap before any revised experiment is approved.
2. Make the worse-than-uncontrolled ramp outcome explicit in the abstract/discussion/conclusion; retain actual versus adjusted export and the mixed forecast result.
3. Add domain-related work and a formal optimisation appendix; limit novelty to demonstrated empirical contributions.
4. Keep current bootstrap intervals descriptive, or separately approve a dependence-aware analysis. Do not retroactively tune controllers, splits or statistics for a favourable outcome.
5. Prepare a curated release with artifact access, dependency instructions, rights review and an authoritative versioned manifest. Extend tests and runner/reporting guards in new versions, preserving this freeze and result set.

This is a report and evidence-only audit. No methodological issue was silently fixed, no official metric was changed, and no publication action was taken.

## Audit evidence and replay

- [Independent numerical/model/feature/hash evidence](independent_evidence.json)
- [Chronology overlap and statistical reconstruction](chronology_and_statistics.json)
- [Fresh solver replay evidence](fresh_solver_replay.json)
- [Protected-file inventory](protected_sha256_before_after.json)
- [Independent check implementation](audit_checks.py), [chronology check](chronology_checks.py), [isolated replay harness](replay_checks.py)

Audit scripts exclusively create their own evidence files and will refuse to overwrite an existing audit output. To repeat them, first choose a new audit directory and keep its parent depth or adjust the root resolution explicitly. The replay harness changes only output routing; it does not patch optimisation, data, uncertainty, parameters or solver settings.
