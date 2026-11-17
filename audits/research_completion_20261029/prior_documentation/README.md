# Wind energy forecasting and battery optimisation

MSc Artificial Intelligence research by **Raja Arqam Abdullah**, Teesside University.

This project evaluates XGBoost wind forecasts at 10–60 minutes with causal uncertainty and two-stage lexicographic mixed-integer MPC for wind–battery grid-ramp mitigation.

## Frozen protocol

The development-selected controller is **adaptive one-sided MPC**. Development showed 43.70% lower battery throughput and 0.66% lower summed ramp exceedance than fixed margins, with **11 additional violations** (710 versus 699). These are development findings, not evidence of held-out superiority.

The freeze manifest is `results/development_controller_freeze_manifest.json`, SHA256:

```text
b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a
```

Original controller scripts, datasets and development outputs are preserved. Separate evaluation copies retain the frozen optimisation and physical execution. No models are retrained and no controller is tuned or selected on held-out performance.

**Block 6 is excluded.** Its schedule and preparation script establish development use despite the evaluation CSV filename. The 49 eligible 144-interval episodes give 7,056 controlled intervals per controller. Historic evaluation outputs already exist, so the underlying dataset is not described as wholly blinded.

## Results and documents

<!-- HELDOUT_RESULTS_START -->
The frozen comparison completed **49 paired blocks (7,056 intervals per controller)**. Relative to fixed margins, adaptive one-sided throughput changed by **-27.86%**, summed ramp exceedance by **-0.77%**, and violation count by **-16**. The development preference remains frozen; these outcomes do not trigger controller selection or re-tuning.

| Metric | Fixed margin | Adaptive one-sided | Adaptive minus fixed |
| --- | ---: | ---: | ---: |
| Ramp violations | 1,502 | 1,486 | -16 |
| Violation rate (%) | 21.29 | 21.06 | -0.23 |
| Ramp exceedance sum (kW) | 326,158.296 | 323,638.526 | -2,519.770 |
| Battery throughput (MWh) | 35.486898 | 25.598677 | -9.888221 |
| Conversion losses (MWh) | 1.821593 | 1.312916 | -0.508678 |
| Curtailment (MWh) | 0.000000 | 0.033385 | +0.033385 |
| Actual grid export (MWh) | 1,801.383303 | 1,800.395602 | -0.987701 |
| Terminal-SOC-adjusted export (MWh) | 1,799.021589 | 1,799.572818 | +0.551229 |

All 98 controller-block outputs passed independent physical and energy audits. All 42,336 horizon targets matched raw measurements. First-block replay had zero numeric difference for both controllers on the installed stack. The freeze and all 736 inventoried pre-existing research artifacts remained unchanged. Terminal-SOC-adjusted energy is hypothetical restoration accounting; actual export is reported separately.

See [the full paired results](docs/heldout_results_v2.md) and [figures](docs/figures_v2/paired_controllers.png).
<!-- HELDOUT_RESULTS_END -->

- [Research paper draft](docs/paper_draft.md)
- [Methodology and accounting](docs/methodology.md)
- [Limitations](docs/limitations.md)
- [Reproduction instructions](docs/reproducibility.md)
- [Exact installed evaluation environment](docs/environment-frozen-evaluation.txt)

## Physical assumptions

| Quantity | Value |
| --- | ---: |
| Battery capacity | 2,000 kWh |
| Charge / discharge rating | 1,000 kW |
| SOC bounds | 40–90% |
| Initial SOC per episode | 50% |
| Charge / discharge efficiency | 95% each |
| Control interval | 10 minutes |
| Forecast horizon | 6 intervals |
| Ramp threshold | 200 kW |
| Stage-two primary-objective allowance | 100 kW |

The frozen stage-two allowance makes this lexicographic optimisation **with tolerance**. Battery sizing and ramp threshold are simulation assumptions, not a commissioned-system specification or grid-code certification.

## Run the frozen comparison

From the repository root in PowerShell, with the local artifacts and existing environment:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/heldout_support.py
.venv/Scripts/python.exe scripts/run_frozen_heldout.py --run my_unique_run
.venv/Scripts/python.exe scripts/analyse_frozen_heldout.py --run my_unique_run
```

Results go into separate controller directories under `results/frozen_heldout/<run>/`. CSVs are never overwritten. Provenance records input/source hashes and installed packages; logs have unique timestamped names. The independent analysis checks physical and energy conservation, raw targets and paired comparisons. A repeated first-block run checks local numerical reproducibility.

The historical `requirements.txt` omits CVXPY/HiGHS; use the evaluation environment snapshot for the actual package set. A fresh clone alone is insufficient: datasets, models and generated results are ignored by Git. The [reproduction guide](docs/reproducibility.md) lists required artifacts and resumption instructions. Historical preparation/training scripts may overwrite outputs and are not needed for this replay.

## Validation and interpretation

Tests verify strict causal eligibility, unchanged optimisation/execution code, and rejection of power-balance, stored-energy and equal-time residual errors. Evaluation audits check SOC, battery ratings, wind-only charging, non-simultaneous charge/discharge, curtailment, nonnegative export, command caps and target alignment.

Report ramp counts and exceedance separately, alongside throughput, conversion losses, actual export and terminal-SOC-adjusted energy. Terminal adjustment is hypothetical restoration accounting. Empirical uncertainty coverage does not establish distribution-free guarantees on this dependent series. Lower throughput does not quantify battery lifetime; aggregate gains may coexist with more violations or worse individual periods.

## Repository layout

| Path | Purpose |
| --- | --- |
| `scripts/frozen_fixed_heldout.py` | Frozen fixed-margin evaluation |
| `scripts/frozen_adaptive_one_sided_heldout.py` | Frozen adaptive one-sided evaluation |
| `scripts/run_frozen_heldout.py` | Guarded resumable execution |
| `scripts/analyse_frozen_heldout.py` | Independent audit, paired metrics and PNG/PDF figures |
| `scripts/audit_frozen_reproducibility.py` | Repeated-output and development-accounting checks |
| `tests/` | Causality, preservation and accounting tests |
| `docs/` | Paper, methods, limitations and reproduction |
| `scripts/`, `src/`, `app/`, `notebooks/` | Preserved research/application history |
| `data/`, `models/`, `results/` | Local artifacts, ignored by Git |

No open-source licence has been selected. Dataset attribution and redistribution terms need author review before public release. This workspace update does not publish to GitHub.
