# Reproducing the frozen evaluation

## Current research package and local demonstration

This package supports retrospective frozen-output reproduction and a historical dashboard. It does not establish an untouched confirmatory test. Block-6 development targets overlap five scored block-7 target times, and previous test-period investigation predates the freeze. No scored set, model, calibration, controller or original result is changed. Prior versions of this document, the methodology, README and ignore file are archived under `audits/research_completion_20261029/prior_documentation/`. Historical release manifests refer to their historical live-path versions; the completion verification report distinguishes authorised documentation changes from immutable research artifacts.

On Windows with Python 3.12, a separate environment avoids replacing the existing working environment:

```powershell
py -3.12 -m venv .venv_review
.venv_review/Scripts/python.exe -m pip install -r requirements-research.txt -c docs/environment-frozen-evaluation.txt
.venv_review/Scripts/python.exe -m streamlit run app/dashboard.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

The existing verified `.venv` can be used instead. Direct dependencies are pinned in `requirements-research.txt`; the preserved full snapshot constrains transitive versions. The existing environment was tested; a new network installation is a documented reproduction path, not a clean-machine installation certified during this task. `requirements-dashboard.txt` supports the smaller saved-summary dashboard, without optional CVXPY/HiGHS replay dependencies.

Open `http://127.0.0.1:8501` after launch. The dashboard offers all 49 eligible blocks, both controllers, power/SOC/ramp/uncertainty plots, paired tables, forecast metrics and CSV downloads. If local interval traces are missing, Git-visible `docs/tables_v2/` still supports aggregate exploration. Without those summary tables it shows an explicit missing-data message. It issues no physical commands. The optional replay button invokes the existing frozen runner with a UTC/UUID directory name; it does not replace the historical view, change parameters or claim a one-block replay is a complete new evaluation. It requires the original local input/calibration/development files.

Available checks and new diagnostics, using the existing environment:

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
.venv/Scripts/python.exe -B scripts/verify_research_completion.py
```

`scripts/build_completion_diagnostics.py` computes the additional analysis solely from the frozen traces. Its current outputs already exist in `docs/completion_tables/`, `docs/completion_figures/` and `docs/grid_ramp_diagnostic.md`; **do not rerun it into those same locations**. It exclusively creates artifacts and refuses to overwrite them. To regenerate, use a separate reproduction checkout with those new diagnostic outputs absent and all required original artifacts present. The resulting diagnostic includes all 49 original blocks, including the disclosed overlap; it does not implement a revised embargo or another uncertainty estimator. It creates no new tuned controller or confirmatory confidence interval.

The immutable manifest and prior independent evidence remain at their original paths. New literature, manuscript and diagnostic files are additions. See [final_verification_report.md](final_verification_report.md) for tests, integrity, limitations and current review status, and [unresolved_scientific_issues.md](unresolved_scientific_issues.md) for decisions requiring supervisor review. Do not run the old finaliser to regenerate the new manuscript: it writes earlier documents and contains outcome-specific narrative assumptions. The new submission draft is a separately named document.

Fine-grained `interval_ramp_attribution.csv`, `representative_intervals.csv` and audit solver-replay traces/logs remain local and are now ignored by Git because they contain measured interval data or local execution details. This preserves the files and does not delete or change results. Summary exports, figures and the manuscript still require author review of redistribution permissions before public release. Do not force-add ignored diagnostic files merely to make a clone appear self-contained.

## Original evaluation replay procedure (preserved with qualifications)

Run from the repository root in PowerShell. Use the existing `.venv` for this workspace; its actual package versions are captured in each run's provenance. The historical `requirements.txt` is preserved and omits CVXPY and HiGHS, so it is not a sufficient environment specification for the MPC evaluation. An exact installed environment snapshot accompanies the evaluation release.

Required private/local inputs are the raw `data/raw/T1.csv`, all `data/processed/evaluation_block_*.csv`, the eighteen `data/processed/controller_development_blocks/*.csv`, both calibration CSVs, the evaluation schedule, the freeze manifest and every artifact referenced by it. Models need not be loaded to replay control from frozen forecasts. These data/results/models are excluded by the repository's existing `.gitignore`; a fresh clone alone cannot reproduce the numerical results. Obtain permitted copies separately and match provenance hashes. Do not run historical preparation or training scripts: some overwrite existing artifacts.

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/heldout_support.py
.venv/Scripts/python.exe scripts/run_frozen_heldout.py --run my_unique_run
.venv/Scripts/python.exe scripts/analyse_frozen_heldout.py --run my_unique_run
```

The two evaluation implementations already exist. `prepare_frozen_heldout.py` documents their generation and refuses to overwrite them; run it only in a fresh workspace where the copies do not yet exist. It changes input selection, frozen invocation arguments, history loading, diagnostics and output routing. Optimisation and physical execution are preserved. Both implementations always use risk 0.5, battery-ramp weight 0.1, reserve 1,000, reserve penalty 100 and primary tolerance 100.

The runner uses separate `fixed/` and `adaptive_one_sided/` directories under `results/frozen_heldout/<run>/`. Each file is exclusively created. On resumption, provenance hashes must match, but **any existing CSV is skipped by existence alone**: the runner does not authenticate its completeness. Independently verify existing outputs before resuming. Subsequent analysis checks physical consistency and pairing but cannot by itself prove which solver run created a pre-existing file. Writes are not atomic. Solver logs have timestamped exclusive names. Do not edit implementation or input files during a run. Use a new run name for a changed implementation. The runner's `COMPLETE` message means the requested subset completed; only a validated 49-pair analysis represents the original full scope. The analysis requires all 49 paired blocks and refuses to reuse its output directory; use a genuinely unused `--output` name for a fresh analysis. A partial analysis directory indicates failure and is not a completed release. Integrity checks using Python `assert` require ordinary execution; do not use `python -O`.

For a repeated first-block solver check:

```powershell
.venv/Scripts/python.exe scripts/run_frozen_heldout.py --run independent_replay --blocks 1
```

Compare all numeric columns and timestamps against the corresponding main run, with absolute tolerance 1e-5 and zero relative tolerance, and report maximum differences. Mixed-integer solvers may select different equally optimal actions across solver versions, platforms or settings. Hashes establish artifact identity, not universal bitwise determinism.

For the supplied completed release, the automated replay audit is:

```powershell
.venv/Scripts/python.exe scripts/audit_frozen_reproducibility.py --main-run my_unique_run --replay-run independent_replay
```

Use a new `--output` filename if an audit already exists. This also reconstructs frozen development throughput, conversion losses, actual export and terminal adjustment and checks them against the manifest. The manifest's `held_out_test_status` remains its historical freeze-time declaration; the new run's validation and release manifests describe subsequent evaluation completion.

Artifacts: `provenance.json` records inputs, implementation SHA256 and library versions; `block_metrics.csv`, `aggregate_metrics.csv`, `paired_differences.csv`, `paired_summary.csv`, `forecast_metrics.csv`, `uncertainty_coverage.csv`, `raw_target_audit.csv` and `validation.json` are analysis outputs. Figures are exported as 300 dpi PNG and vector PDF. `paired_controllers` and `paired_differences` show all blocks; `first_block_trace` uses the first eligible block by pre-specified order, not a favourable example.

Publication and GitHub upload are separate actions. No remote publication is performed by these scripts. Review dataset redistribution rights and repository licensing before making local data artifacts public.
