# Frozen retrospective evaluation methodology

## Current publication interpretation

The original `heldout` filenames and 49-block scores are preserved as historical artifact identifiers. They are **not** evidence of untouched confirmatory evaluation: Git history documents pre-freeze evaluation-period investigation, and development block 6's six-horizon targets overlap five block-7 measured target times (15 horizon-target pairs and five scored h1 outcomes). The original preflight checks only the eighteen earlier development files and therefore misses this schedule-designated development overlap. No observations, controller parameters or published totals have been silently removed or changed.

Both controllers worsen aggregate ramp violation counts and summed exceedance relative to uncontrolled wind. Adaptive improves on fixed margins, reducing battery throughput 27.86%, modelled conversion losses 27.92%, summed exceedance 0.77% and violation count by 16. These results describe a retrospective comparison of two configurations, not demonstrated net mitigation over no battery or an isolated causal effect of rolling adaptation.

The complete source-matched formulation is in [mathematical_formulation.md](mathematical_formulation.md), including binary minimum constraints, first-stage requests, soft reserve, the 100 kW aggregate primary allowance, physical fallback, and terminal restoration accounting. The [grid-ramp diagnostic](grid_ramp_diagnostic.md) examines unchanged traces and distinguishes confirmed identities, expected trade-offs, modelling limitations and hypotheses. The current manuscript is [paper_submission_draft.md](paper_submission_draft.md); the earlier draft and v2 tables remain preserved.

## Question and protocol

Does a development-selected rolling one-sided uncertainty controller reduce battery use while retaining ramp-mitigation performance relative to the frozen fixed-margin controller? Both use six existing XGBoost forecasts at 10–60 minutes and the same two-stage mixed-integer receding-horizon optimisation. This evaluation does not train models, search parameters, or select controllers using test outcomes.

The authoritative freeze is `results/development_controller_freeze_manifest.json`, SHA256 `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a`. Every invocation verifies its five source hashes and 54 development-result hashes. Development preference remains adaptive one-sided regardless of held-out performance. Development showed 43.70% lower throughput and 0.66% lower exceedance, but 11 more violations (710 versus 699). These are development observations, not confirmatory evidence.

## Data and split provenance

The local input is `data/raw/T1.csv`, a 2018 turbine SCADA series with ten-minute measurements. Dataset timestamps have no established timezone; plots retain the dataset clock. Negative generation is clipped at zero in simulation and target verification. Missing periods are not interpolated into contiguous control episodes.

The existing training script uses targets strictly before 9 September 2018 02:50 for training and validation origins from that boundary with last targets strictly before 5 November 2018 15:10. It specifies six separate XGBoost regressors, 300 trees, depth 4, learning rate 0.05, row sampling 0.8, column sampling 0.9, seed 42. These describe historical implementation, not a newly executed training experiment. Features contain current power, wind speed/direction, timestamp-joined power/wind lags, recent changes and a past/current power mean. No future weather is supplied.

The calibration file contains 4,484 origins; its latest 60-minute target is 15 October 2018 11:50, strictly before the first held-out decision. The scheduled evaluation runs from 5 November through 31 December 2018 across four contiguous segments. Missing-data boundaries are respected.

The audited validation predictions were split chronologically 60% for calibration and 40% for controller development. Eighteen complete development blocks informed the frozen comparison. The test schedule contains fifty 144-origin blocks; 49 are labelled `evaluation`.

**Block 6 is excluded.** `prepare_evaluation_schedule.py` explicitly identifies 14 November 2018 13:00 through 15 November 2018 12:50 as development. `prepare_development_block_6.py` deliberately writes those observations to `evaluation_block_6.csv` while requiring the development role. The filename therefore does not establish held-out status. Historical test-period analyses already exist in the repository: describe this as a frozen-controller evaluation on reserved scheduled blocks, not an independently blinded or never-inspected dataset. No new controller selection uses these outcomes.

Each held-out episode resets stored energy to 1,000 kWh, previous battery power to zero and previous export to the origin's clipped current generation. Adjacent episodes do not carry battery state. There are 7,056 controlled intervals and 7,056 scored transitions per controller. Each episode's first transition is included; cross-episode export transitions are not scored.

## Uncertainty and causality

The fixed controller reads its existing horizon-specific absolute-error calibration margins: approximately 400.014, 536.120, 608.362, 673.969, 727.957 and 786.613 kW. The adaptive controller uses signed overprediction residuals `forecast - actual`, a 144-residual window and alpha 0.10. Its order statistic has rank `ceil((n+1)*(1-alpha))`, without interpolation. Static floors are 358.379810, 504.728717, 571.614234, 630.176420, 690.977755 and 731.661882 kW.

For an origin s and horizon h, residual eligibility is **s + 10h minutes < t**, where t is the current decision time. Targets equal to t are excluded. Frozen post-gap logic begins at 31 October 2018 16:50: use the static floor until 72 of the selected origins are post-gap; otherwise take the maximum of the rolling quantile and floor. Nominal and lower scenarios are clipped at zero.

The held-out history extends the frozen calibration/development history with all fifty scheduled block files. Excluded block 6 can supply already-observed past residuals, but is never scored. Preloading files does not make future targets eligible: the frozen module strictly filters each horizon before selecting residuals. Incomplete unscheduled episode tails are not added to history. History is not reset with battery state. Intervention tests replace equal/future target outcomes with extreme values and confirm unchanged margins; output diagnostics record the newest eligible target.

This is rolling conformal-style calibration, not the adaptive-alpha algorithm of Gibbs and Candes. Serial dependence, distribution shift, floors and fallback mean that nominal 90% distribution-free coverage is not established. Empirical lower-bound coverage is reported separately by horizon and controller. It is not simultaneous six-horizon coverage.

## Optimisation and physical execution

Battery capacity is 2,000 kWh, charge and discharge ratings 1,000 kW, energy bounds 800–1,800 kWh (40–90% SOC), charge/discharge efficiencies 0.95, and interval length 1/6 hour. For each scenario j, grid export is `g = w - curtail - charge + discharge`, constrained nonnegative, and energy evolves as `E_next = E + 0.95*charge/6 - discharge/(6*0.95)`. Charging is wind-only. Binary modes prevent simultaneous charge/discharge. Curtailment is bounded by available wind. No independent grid interconnection upper limit is introduced.

Both controllers weight nominal and downside scenarios equally. The first discharge and mode are shared. First-step scenario charging is exactly the minimum of committed requested charging and available scenario wind; curtailment is similarly capped after charging using binary selectors. Later actions are scenario dependent. This prevents scenario-specific first-stage commands from anticipating the realised wind.

Stage 1 minimises weighted predicted exceedance `sum(max(abs(grid ramp)-200,0))`. Stage 2 restricts this objective to the stage-1 optimum **plus 100 kW**, then minimises the frozen weighted operational cost. This is a tolerance-constrained two-stage lexicographic formulation, not strict preservation of the primary optimum. The 100 kW tolerance was frozen on development data.

Per scenario the secondary cost is the sum of absolute grid ramps, plus 0.1 times absolute battery-power changes, 20 times exceedance, 0.1 times interval-weighted battery throughput, twice absolute terminal energy deviation from 1,000 kWh, 50 times curtailment power, and 100 times reserve shortfall below 1,000 kWh. These mixed-unit weights are research objective coefficients, not monetary prices.

HiGHS solves both mixed-integer stages via CVXPY, requiring `optimal` status. Commands are committed before actual h1 wind is read. Simulation reduces charging for wind/power/SOC availability, caps discharge at the lower-SOC safety limit and caps curtailment at wind remaining after charging. Actual export and SOC then determine the next decision state. The optimisation and execution bodies in evaluation copies are AST-tested against the frozen sources.

## Metrics and independent checks

For each episode, absolute ramps include origin current power to first controlled export. A violation is `ramp > 200.001 kW`; exceedance is `max(ramp-200,0)` summed across transitions. The summed exceedance has units kW and is not energy. Report counts, rates, sums, mean and maximum ramps without treating these as interchangeable outcomes.

AC-side throughput is `sum(charge+discharge)/6`. Conversion losses are `0.05*charge_kWh + (1/0.95-1)*discharge_kWh`. Independently verify `wind = export + curtailment + losses + final_energy - initial_energy`. Actual exported energy is reported alongside terminal-adjusted export: add `0.95*delta_E` for surplus storage and `delta_E/0.95` for deficit storage. This reproduces development accounting. It represents hypothetical restoration to the initial inventory and does not simulate feasible restoration, price, subsequent ramps or extra time.

Independent audits verify all SOC transitions and bounds, nonnegative export, power balance, power limits, wind-only charging, curtailment, absence of simultaneous charging/discharging, committed-command caps, target timestamps and strict causal diagnostic targets. Raw SCADA lookup verifies all six targets for all eligible origins, including boundaries. Equal-sized episodes allow aggregation of forecast MAE and mean squared error before taking aggregate RMSE; errors are also compared with persistence.

Controller differences are paired by block, adaptive minus fixed. Report both aggregate totals and block-level signs/medians. Seeded 10,000-draw paired block bootstrap intervals are descriptive only: adjacent blocks and common weather create temporal dependence. They do not justify independent-sample significance claims. No graph, diagnostic or comparison may be used to tune or replace the frozen controller.
