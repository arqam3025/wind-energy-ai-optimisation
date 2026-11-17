# WindGrid AI — Wind–Battery Digital Twin

This is an eight-page **historical research platform** over the preserved `final_20261029` outputs. No controller, forecasting model, dataset, calibration, manifest, scored set or original result is modified. It is not live telemetry, inverter software, certified grid compliance or a battery lifetime model.

## Launch and navigation

```powershell
.venv/Scripts/python.exe -m streamlit run app/dashboard.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Open `http://127.0.0.1:8501` and keep the server running. A separate installation can use Python 3.12 and `pip install -r requirements-dashboard.txt`. Full scientific replay additionally needs `requirements-research.txt` and the ignored local artifacts. The current environment already contains Plotly 7.1.0 and Streamlit 1.65.0; no dependency download was required for this upgrade. A clean-machine installation was not tested.

The app uses real `st.navigation` file pages in `app/screens/`, with Operations, Analysis and Evidence groups. Page entry files are intentionally outside Streamlit's reserved legacy `pages/` directory so navigation always executes the shared shell. The dark theme is defined in `.streamlit/config.toml`; Plotly charts offer hover, legend filtering, zoom and export controls. Native layout columns collapse on small screens; browser visual/responsive automation was unavailable, so that presentation check remains a limitation.

Shared sidebar controls select one of three cases, one of 49 eligible episodes, a forecast horizon and a zero-based interval cursor (0–143). The UI also labels that cursor as interval 1–144. Changing controller or block resets playback; manual scrubbing pauses it. Block 6 is never offered. State is local to the user's Streamlit session.

## Page capabilities and artifact dependencies

| Page | Implemented behaviour | Missing-data behaviour |
| --- | --- | --- |
| Command Center | Real recorded state, power-flow Sankey, wind/export profile, violation timeline and jump-to-event selector | Shows an explicit interval-artifact message and available aggregate comparison |
| Digital Twin | Real play/pause/step/back/reset; timer-driven ten-minute cursor; speed changes viewing frequency only; recorded SOC/power/curtailment, exact power residual, prefix energy accounting and CSV | Requires local input and paired traces; no fabricated replacement |
| AI Forecasting Lab | Forecasts/actual/persistence aligned at all six horizons, lower bound and nominal shading, selected decision path, aggregate MAE/RMSE and coverage | Aggregate charts work from tables alone. Fixed decision paths need the fixed calibration file; absent calibration is reported without a made-up bound |
| MPC Decision Explorer | Six-step nominal/downside input paths, optional retrospective actual-target overlay, logged first requests/realised actions, constraints, first-step algebraic ramp reconstruction and all-case table | Detailed decisions require input/traces; aggregate block table remains available. Unlogged solver plans/objectives are explicitly unavailable |
| Battery Analytics | SOC/distribution, AC throughput and conversion loss, explicit EFC proxy, energy-conservation waterfall, export/inventory tables and per-block aggregate charts | Aggregate tables work without traces; no-battery SOC and stored energy are N/A |
| Grid Stability Lab | All three cases, signed/absolute ramps, exceedance differences, introduced/removed violation filters, real event windows and exact injection-change identity | Aggregate baseline comparisons remain available without interval traces |
| Research Results | All 49 original pairs, baseline comparison, paired difference/scatter charts, coverage, descriptive statistical limitations and table downloads | Requires the validated `docs/tables_v2/` summaries |
| Reproducibility | Exact freeze verification before following manifest references, 59 source/development-output checks, environment, prior/current evidence, document downloads and commands | Explicit missing/hash-mismatch statuses. Prior validation is labelled as historical, not proof of current UI testing |

No archived six-step planned battery actions, SOC plans, stage-one optimum, stage-two achieved cost, solver gaps or per-decision times exist. The six-step explorer shows forecast **inputs**, and only the recorded first command/execution is shown as a decision. Reconstructed first-step scenarios are labelled derived, not logged solver internals. A one-sided lower bound is not a two-sided prediction interval.

## Meaning of the three cases and energy quantities

Adaptive and fixed traces are loaded unchanged. The uncontrolled reference repeats measured generation as grid export and has zero charge/discharge/curtailment by definition; no nonexistent battery state is assigned. Power is in kW; stored and integrated energy is in kWh or explicitly converted MWh. Physical time stays ten minutes even when a recording is viewed faster.

Each episode contributes 144 transitions, including origin current wind to the first output, with no transition across episode resets. A violation exceeds 200.001 kW; exceedance sums `max(abs(change)-200,0)` in kW, not energy. Prefix energy metrics include the selected interval exactly once. AC throughput is charge plus discharge energy; the EFC **proxy** is throughput/(2 × 2,000 kWh). It is not rainflow cycles, degradation or lifetime.

Actual export is integrated physical simulated output. Terminal-adjusted export hypothetically restores initial inventory using efficiency; it is neither additional realised export nor a feasible future restoration simulation. The dashboard keeps both quantities separate. The research caveat is visible on every page: both controllers worsen aggregate violations/exceedance versus uncontrolled wind, and the comparison is retrospective because of pre-freeze test access and block-6/block-7 target overlap.

## Data validation and efficiency

`app/platform_data.py` validates allowed blocks, summary schemas, finite numbers, duplicate/aligned ten-minute timestamps, all six within-block targets, source/actual/forecast agreement, power balance, stored-energy transitions and SOC bounds, rating limits, no simultaneous operation, wind-only charging/curtailment, execution caps and strictly earlier adaptive residual targets. Cache keys contain root/path plus modification time and size, with bounded entries and expiry. Data changes therefore invalidate cached reads. `WINDGRID_DATA_ROOT` selects a separate artifact root, primarily for missing/corruption tests; it cannot change the frozen controller algorithm.

The platform performs no forecast fitting or optimisation during ordinary browsing. Optional exploratory simulation is not mixed into the saved view. The Reproducibility page gives the original command with a new run name; any such rerun remains a separately stored experiment. Only the selected page renders, limiting chart work during playback. Playback uses Streamlit timer fragments, not a blocking sleep loop or simulated telemetry.

## Testing and failures encountered

The first integrated navigation test run reported three historical-context assertions failing and two errors. The shared entry point was bypassed when test navigation encountered the reserved legacy `pages/` folder. Moving the registered file pages to `screens/` fixed the missing global controls/context. The other error was a test attempting to click a deliberately disabled end-of-episode Step button; the test now verifies that Step and Play are disabled at the end. No frozen research files were involved in either correction.

The suite additionally tests all eight page renders, three-case selection, block/horizon changes, playback controls and timer advancement, end clamping, reset on block change, prefix accounting, aggregate-only mode, completely missing summaries, malformed SOC traces, missing fixed calibration, schema rejection, cache invalidation and manifest mismatch handling. Benign Streamlit bare-mode context/cache warnings can occur during AppTest; they are recorded separately from failures.

Run:

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
```

Final test counts, physical traversal, preservation hashes and HTTP smoke statuses are recorded in `audits/windgrid_dashboard_20261029/validation_report.json` after verification. AppTest validates application execution and interactions, while HTTP checks validate serving. Neither substitutes for a human visual/accessibility review. No automated browser installation or external hosting was performed.

## Preservation and release

The previous dashboard, helper, original dashboard tests, README and dependency files are archived under `audits/windgrid_dashboard_20261029/prior_version/`. The research baseline in that audit directory covers 1,078 files; it is checked after implementation. Original eight research tests and the earlier dashboard/data accounting tests remain in the suite. The protected data/models/controller/results/manifests remain unchanged. New app, view, screen, test and guide files are additions; README and direct UI dependency declarations are authorised updates. Previous research package manifests describe their historical versions, not the upgraded UI.

No Git commit, push, paper submission or external deployment is performed. Original data-access, licensing, retrospective evaluation and publication-readiness limitations still apply.
