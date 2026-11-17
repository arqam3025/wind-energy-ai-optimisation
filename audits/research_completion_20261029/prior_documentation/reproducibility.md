# Reproducing the frozen evaluation

Run from the repository root in PowerShell. Use the existing `.venv` for this workspace; its actual package versions are captured in each run's provenance. The historical `requirements.txt` is preserved and omits CVXPY and HiGHS, so it is not a sufficient environment specification for the MPC evaluation. An exact installed environment snapshot accompanies the evaluation release.

Required private/local inputs are the raw `data/raw/T1.csv`, all `data/processed/evaluation_block_*.csv`, the eighteen `data/processed/controller_development_blocks/*.csv`, both calibration CSVs, the evaluation schedule, the freeze manifest and every artifact referenced by it. Models need not be loaded to replay control from frozen forecasts. These data/results/models are excluded by the repository's existing `.gitignore`; a fresh clone alone cannot reproduce the numerical results. Obtain permitted copies separately and match provenance hashes. Do not run historical preparation or training scripts: some overwrite existing artifacts.

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/heldout_support.py
.venv/Scripts/python.exe scripts/run_frozen_heldout.py --run my_unique_run
.venv/Scripts/python.exe scripts/analyse_frozen_heldout.py --run my_unique_run
```

The two evaluation implementations already exist. `prepare_frozen_heldout.py` documents their generation and refuses to overwrite them; run it only in a fresh workspace where the copies do not yet exist. It changes input selection, frozen invocation arguments, history loading, diagnostics and output routing. Optimisation and physical execution are preserved. Both implementations always use risk 0.5, battery-ramp weight 0.1, reserve 1,000, reserve penalty 100 and primary tolerance 100.

The runner uses separate `fixed/` and `adaptive_one_sided/` directories under `results/frozen_heldout/<run>/`. Each file is exclusively created. Resume the same run after interruption: provenance hashes must match and existing complete outputs are skipped. Independent analysis is still required to validate those outputs. Solver logs have timestamped exclusive names. Do not edit implementation or input files during a run. Use a new run name for a changed implementation. The analysis requires all 49 paired blocks and refuses to reuse its output directory; use `--output analysis_v2` for a fresh analysis. A partial analysis directory indicates failure and is not a completed release.

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
