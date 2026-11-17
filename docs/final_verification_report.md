# Final research package verification report

29 October 2026. Status: implemented and ready for **supervisor review as a retrospective study**, not approved for immediate journal submission or external publication.

## Delivered

- Separate [submission draft](paper_submission_draft.md), preserving the original paper and v2 results. It contains the requested sections, actual numerical tables, nine captioned figures and a complete source-matched mathematical appendix.
- [Grid-ramp diagnostic](grid_ramp_diagnostic.md), nine CSV diagnostic tables, provenance JSON and eight new 300 dpi PNG/vector-PDF figure pairs. Original outputs are not overwritten.
- [Literature review](literature_review.md) covering fifteen published papers and a machine-readable reference register. Published DOIs are linked where identified; no DOI was fabricated for the NeurIPS ACI proceedings. R02's exact final author-order metadata remains access-limited and explicitly flagged; the R12 final issue/pages were verified against an official funder publication record.
- Updated methods, reproduction guide, Windows dependency instructions, ignore rules and README. The four authorised prior documentation/config versions are archived in `audits/research_completion_20261029/prior_documentation/`.
- A local Streamlit historical-replay dashboard with controller/block/horizon selection, all requested power/SOC/ramp/energy/forecast/uncertainty views, comparison tables and CSV exports. An isolated optional simulation action invokes the existing runner without changing parameters.
- [Unresolved scientific issues](unresolved_scientific_issues.md) and a repeatable integrity/verification command.

Fine-grained interval/event diagnostic CSVs and audit replay traces/logs are retained locally but excluded from accidental Git staging pending rights review. This does not alter their values or remove the local diagnostic evidence. A six-model metadata inspection confirms 14 features, 300 trees, squared-error objective and model serialization version 3.4.1 for every horizon; its record is in the completion audit directory.

## Tests and checks

| Check | Result |
| --- | --- |
| Original eight unit tests | Pass: causal target boundary, source-body equality, freeze/input checks, energy and power accounting |
| Two new diagnostic tests | Pass: wind-limited first requests; previous battery injection in the next transition; timestamp corruption rejection |
| Four dashboard tests | Pass: AppTest initial render and controller/block/horizon interaction; exact saved-metric accounting; block-6 exclusion; aggregate fallback without private traces |
| Total unit/smoke tests | **14 pass**, no failed tests |
| HTTP page | Local `http://127.0.0.1:8501/` returns 200 |
| HTTP health endpoint | `/_stcore/health` returns 200 and `ok` |
| Physical trace checks | All 98 original controller-block outputs pass SOC, power and energy identities and limits |
| Diagnostic source integrity | All 151 recorded original input/source paths match diagnostic provenance |
| Frozen development manifest | Exact expected SHA256; all 59 referenced sources/development outputs match |
| Immutable completion baseline | **1,041 files unchanged**, including original sources, models, datasets, calibration, manifests, results, earlier drafts and audit evidence |
| Headline metric regression | 27.8644275% throughput reduction, 0.7725606% exceedance reduction and 16 fewer violations versus fixed remain unchanged |
| Prior independent audit | Preserved evidence covers 42,336 causal margins/raw target pairs, current model/feature consistency and zero-difference fresh first-block replay |
| Git whitespace/link/credential checks | Completion verifier checks whitespace, required local links and bounded credential patterns; findings are recorded in its evidence JSON |

Streamlit emits a benign bare-mode `missing ScriptRunContext` warning in AppTest; it did not cause test failures. No missing runtime dependency was encountered in the existing environment. The full local solver experiment was not rerun: the original traces and independent first-block replay were preserved, and the new analysis is read only. Optional replay-button solving was not separately run as an additional scientific experiment.

The portable Sites local-only workflow guided the dashboard checks. No user-facing browser automation was available: AppTest exercises the app and controls, HTTP checks verify serving, and diagnostic figures were visually inspected. A browser visual/accessibility review and a clean-machine dependency installation remain unverified. The temporary test server is stopped after verification; the documented launch command starts it again.

## Scientific findings and claim boundaries

The extra diagnostic found no transition-counting or physical-balance bug explaining deterioration. Fixed introduces 166 violations and removes 129; adaptive introduces 134 and removes 113. Exact injection-change attribution explains realised grid transitions. First-step scenario reconstruction shows some actual violations even when both planned first ramps are safe, but cannot recover unavailable six-step stage objectives or identify individual penalty effects.

Both controllers worsen total exceedance, violation count and mean absolute ramp relative to uncontrolled wind. Both reduce the maximum absolute ramp. Adaptive saves throughput and modelled conversion loss relative to fixed, with a small heterogeneous ramp improvement. Actual and hypothetical terminal-adjusted export remain separate. The development preference is unchanged; no new controller selection, hyperparameter tuning, model fitting, embargo, resampling estimator or scored-set modification was introduced.

The original “held-out” artifact names are preserved. The new manuscript explicitly rejects untouched-confirmatory language because prior test-period inspection and block-6/block-7 development-target overlap remain. These are scientific-design limitations, not evidence of runtime access to future residuals. Original model/floor provenance and dependence limits are not repaired by documentation alone.

## Readiness and release decisions

The package is ready for supervisor/author review of a qualified retrospective empirical study and its local demonstration. Immediate submission is premature pending scientific framing and novelty review, resolution or disclosure of historical provenance, final bibliographic export and venue formatting, data/code licensing and a permissible reproducibility archive/access route. If confirmatory superiority is required, genuinely new data and a separately approved protocol are needed. A post-hoc scored-set change cannot undo historical exposure.

No journal acceptance, publication DOI, field deployment, battery-life improvement, guaranteed coverage or universal grid-stability benefit is claimed. Nothing was staged, committed, pushed, hosted or submitted externally by this task. The repository still needs a curated release commit; untracked deliverables are not automatically part of `main`.

## Re-run verification and demonstration

```powershell
.venv/Scripts/python.exe -B scripts/verify_research_completion.py
.venv/Scripts/python.exe -m streamlit run app/dashboard.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Use `--check-http` only while that local server is running. The verifier normally reads and prints checks without writing research outputs. `--record new_name.json` exclusively records evidence in the completion audit directory. HTTP smoke results are in `audits/research_completion_20261029/verification_evidence.json`; the final post-configuration check is `verification_evidence_final.json` in that directory. The prior four-file documentation archive explains authorised live-path hash changes in older release snapshots. Frozen manifests themselves are unchanged.
