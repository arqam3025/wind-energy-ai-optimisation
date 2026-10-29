# Reproduce the research-grade extension

This is a retrospective audit and exploratory experiment. It does not replace the original frozen study or restore untouched testing. Read [RESEARCH_AUDIT.md](RESEARCH_AUDIT.md), [EXPERIMENTAL_RESULTS.md](EXPERIMENTAL_RESULTS.md) and [RESEARCH_LIMITATIONS.md](RESEARCH_LIMITATIONS.md).

## Environment and inputs

Executed with Python 3.12.5, CVXPY 1.9.3 and HiGHS 1.15.1 on Windows. The pinned direct requirements were already installed; a fresh isolated installation was not tested. From the repository root:

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-research.txt -c docs/environment-frozen-evaluation.txt
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
```

Required local inputs: `data/raw/T1.csv`, fourteen-feature/six-target processed tables, six `models/wind_xgboost_h*.json` predictors, calibration predictions/margins, eighteen development blocks, fifty scheduled blocks and original frozen traces. The manifest and all five referenced frozen sources and 54 development traces are also required. Much of this pre-existing local work is ignored or still untracked; a clone alone is insufficient. Obtain the [SCADA dataset from its original author](https://www.kaggle.com/datasets/berkerisen/wind-turbine-scada-dataset) and request the matching source/model/data/result bundle from the project author, subject to confirmed redistribution rights. Verify exact hashes; another download version is not an exact reproduction. Dataset version, timezone, aggregation semantics and redistribution terms remain unresolved.

Historical preparation/training scripts document provenance, but can overwrite historical destinations. Use a separate checkout and new artifact version to regenerate inputs. The new commands below never train a model. Missing inputs produce errors; synthetic fixtures only verify code and are never research observations.

## Integrity and chronology

Required manifest SHA256:

```text
b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a
```

Every benchmark verifies the manifest and 59 references. New output directories must not exist. Partial runs are retained as incomplete; the runner never resumes or reuses a CSV. Choose another run name after a failure. Analysis requires `completion.json` to describe the complete requested cohort with zero failures.

`scripts/audit_protocol_boundaries_v1.py` created the separate `results/research_grade_v1_20261029/protocol_corrections/` projection: 4,478 calibration origins retained, six excluded. This projection is a demonstrated causal correction, not a replacement calibration used for frozen scores. New development studies use predeclared later blocks 2, 10 and 18; all existing static calibration targets already precede these decisions. Rolling residual targets must be strictly before decision time. Equal-time/future-target interventions are tested.

## Forecasting and uncertainty

Choose unused result and figure directories:

```powershell
.venv/Scripts/python.exe -B scripts/run_forecast_uncertainty_audit_v1.py --output results/research_repeat/forecast_uncertainty --figures figures/research_repeat/forecast_uncertainty
```

This reconstructs features, targets, saved model inference and frozen adaptive margins. It evaluates persistence, existing XGBoost and a parameter-free two-point local trend. It saves MAE, RMSE, residual distributions, horizon/block/segment/rapid-event coverage, interval width and margin diagnostics. The trend lacks an established turbine-rating cap and can extrapolate implausibly. No preprocessing or predictor is fitted. Outcome-defined rapid events are offline strata, never decision inputs.

## Controller comparisons and development studies

Parameters are declared in `configs/mpc_research_v1.json`; the overall audit/statistics plan is `configs/research_audit_v1.json`. HiGHS uses one thread per process, seed 20261029, zero declared relative MIP gap, a 30-second per-stage limit and requires optimal status. At most three workers:

```powershell
.venv/Scripts/python.exe -B scripts/run_controller_benchmarks_v1.py --mode pilot --output results/research_repeat/pilot --workers 3 --retrospective
.venv/Scripts/python.exe -B scripts/run_controller_benchmarks_v1.py --mode benchmark --output results/research_repeat/benchmark --workers 3 --retrospective
.venv/Scripts/python.exe -B scripts/run_controller_benchmarks_v1.py --mode sensitivity --output results/research_repeat/sensitivity --workers 3 --retrospective
.venv/Scripts/python.exe -B scripts/run_controller_benchmarks_v1.py --mode ablations --output results/research_repeat/ablations --workers 3 --retrospective
```

Pilot: six cases on development block 2. Benchmark: six cases on 49 scheduled evaluation blocks; development block 6 excluded. Sensitivity: nineteen configurations including baseline on three full 144-step development episodes. Ablations: nine configurations including baseline on those episodes. No outcome selects a new preferred controller. Runtime depends on hardware and integer difficulty; measured time is not a latency guarantee.

Episodes reset SOC, previous battery injection to zero and previous export to observed origin power. First scored ramps are included; cross-episode transitions are excluded. Nominal and persistence MPC remove the downside scenario while retaining the other objectives/physical constraints. The perfect-forecast case alone receives future actual wind; it is nondeployable and is not an unconditional upper bound for every metric under a finite horizon/mixed objective.

New logs include six-step scenario plans, both stage objectives/statuses, constraint residuals, available MIP diagnostics, requested/realised actions, timing and causal margin diagnostics. A failed solve fails the case/block; it never becomes zero cost. Original-versus-versioned trajectory differences are saved because deterministic solver settings/canonicalization can choose different tied optima. Original frozen totals remain authoritative. Actual export and hypothetical terminal-restoration export stay separate.

## Tables, uncertainty and figures

After all three full studies complete:

```powershell
.venv/Scripts/python.exe -B scripts/analyse_research_grade_v1.py --studies results/research_repeat --output results/research_repeat/analysis --figures figures/research_repeat/analysis
.venv/Scripts/python.exe -B scripts/run_dependent_statistics_v1.py --output results/research_repeat/statistics_original --figures figures/research_repeat/statistics_original
```

Analysis rejects missing/duplicate pairs and incomplete studies. Outputs include controller/energy/ablation/sensitivity tables, paired intervals, introduced/removed violations, original-trajectory differences and runtime. Figures are 300-dpi PNG and vector PDF. The export/SOC example uses predeclared evaluation block 1.

Resampling uses paired daily metrics, 10,000 draws and non-circular block lengths 2, 3 and 7 within four original calendar segments. All lengths are reported. Recentered basic intervals are conditional approximations under unverified within-segment stationarity/dependence assumptions. A five-day segment supplies no variation at length seven; blocks never bridge calendar gaps. Multiple exploratory comparisons do not have a familywise significance interpretation. Intervals cannot reverse historical evaluation exposure.

## Review and release

Work belongs on branch `research/grade-audit-20261029`. Full generated logs remain ignored; curate small aggregate tables/figures separately. Exact executed source snapshots and hashes are retained when validation is strengthened after experiments. Review an intended release commit/tag, artifact availability and licensing before publication. No push is authorised.

The existing dashboard continues to show the archived frozen study. Launch with `.venv/Scripts/python.exe -m streamlit run app/dashboard.py`. New experimental logs never silently replace its research tables or fabricate original solver internals.

Final saved-artifact verification, using a new JSON filename:

```powershell
.venv/Scripts/python.exe -B scripts/verify_research_grade_v1.py --output audits/my_research_verification.json
```

The completed v2 report verifies the 1,024-file protected baseline, manifest/59 references, all three complete studies, their executed-source snapshots and independent power/SOC/ramp/plan/energy checks. The v1 failure is retained: three future oracle plan rows have at most 0.392 W numerical charge/discharge overlap. The planning check now uses the engine's predeclared 1 W power tolerance; executed-action checks remain strict. This numerical validation correction changes no result. The six-case pilot has verified physics but lacks complete historical forecast-audit source bytes; only the three full studies claim complete executed-source authentication.
