"""Assemble a separately named review manuscript from unchanged research tables."""
from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def table(frame, digits=3):
    rows=['| '+' | '.join(map(str,frame.columns))+' |','| '+' | '.join(['---']*len(frame.columns))+' |']
    for values in frame.itertuples(index=False,name=None):
        formatted=[f'{v:,.{digits}f}' if isinstance(v,float) else str(v) for v in values]
        rows.append('| '+' | '.join(formatted)+' |')
    return '\n'.join(rows)

def main():
    totals=pd.read_csv(ROOT/'docs/tables_v2/aggregate_metrics.csv').set_index('controller')
    baseline=pd.read_csv(ROOT/'docs/tables_v2/uncontrolled_wind_baseline.csv')
    outcomes=[]
    for label,kind in [('Fixed-margin MPC','fixed'),('Adaptive one-sided MPC','adaptive_one_sided')]:
        r=totals.loc[kind]
        outcomes.append([label,int(r.ramp_violations),r.ramp_exceedance_kw,r.throughput_kwh/1000,r.conversion_losses_kwh/1000])
    outcomes.insert(0,['Uncontrolled wind',int(baseline.ramp_violations.sum()),baseline.ramp_exceedance_kw.sum(),0.,0.])
    control_table=table(pd.DataFrame(outcomes,columns=['Strategy','Violations','Exceedance sum (kW)','Throughput (MWh AC)','Conversion losses (MWh)']))
    energy=[]
    for kind in ['fixed','adaptive_one_sided']:
        r=totals.loc[kind]
        energy.append([kind,r.export_kwh/1000,r.terminal_adjusted_export_kwh/1000,r.curtailment_kwh/1000,r.terminal_energy_delta_kwh/1000])
    energy_table=table(pd.DataFrame(energy,columns=['Controller','Actual export (MWh)','Adjusted export (MWh)','Curtailment (MWh)','Stored inventory change (MWh)']),6)
    accuracy=pd.read_csv(ROOT/'docs/tables_v2/forecast_metrics.csv').pivot(index='horizon_minutes',columns='model')
    forecast_table=table(pd.DataFrame([[h,accuracy.loc[h,('mae_kw','xgboost')],accuracy.loc[h,('mae_kw','persistence')],accuracy.loc[h,('rmse_kw','xgboost')],accuracy.loc[h,('rmse_kw','persistence')]] for h in accuracy.index],columns=['Horizon (min)','XGBoost MAE (kW)','Persistence MAE (kW)','XGBoost RMSE (kW)','Persistence RMSE (kW)']))
    cov=pd.read_csv(ROOT/'docs/tables_v2/uncertainty_coverage.csv').groupby(['horizon_minutes','controller']).lower_bound_coverage.mean().unstack()*100
    coverage_table=table(pd.DataFrame([[h,cov.loc[h,'fixed'],cov.loc[h,'adaptive_one_sided']] for h in cov.index],columns=['Horizon (min)','Fixed lower coverage (%)','Adaptive lower coverage (%)']),2)
    segment=pd.read_csv(ROOT/'docs/completion_tables/segment_paired_differences.csv')
    segment_table=table(segment)
    paper=r'''# Wind–battery predictive control with causal one-sided uncertainty: a retrospective comparison and diagnosis of realised ramp deterioration

**Raja Arqam Abdullah** — MSc Artificial Intelligence, Teesside University

Supervisor-review submission draft, 29 October 2026. No journal submission or external publication has occurred. The archived experiment and its numerical results are unchanged.

## Abstract

Forecast-informed battery dispatch can reduce predicted wind-power fluctuations without improving realised grid ramps. This study evaluates six direct XGBoost wind forecasts at 10–60-minute horizons and compares frozen fixed-margin and rolling one-sided uncertainty configurations within mixed-integer model predictive control (MPC). Residual targets are eligible only when strictly earlier than the decision. Two objective-priority solves minimise predicted ramp exceedance and then operational penalties subject to a frozen 100 kW primary allowance. Forty-nine scheduled episodes yield 7,056 controlled ten-minute intervals per controller; development block 6 is excluded. However, earlier evaluation-period inspection and five block-7 target times shared with development prevent an untouched confirmatory interpretation. Adaptive one-sided MPC reduces battery throughput by 27.86%, modelled conversion losses by 27.92%, summed exceedance by 0.77%, and violations by 16 relative to fixed margins. Both controllers nevertheless exceed uncontrolled wind in violation count: 1,502 fixed and 1,486 adaptive versus 1,465 uncontrolled. Summed exceedance is 326,158.296, 323,638.526 and 317,210.288 kW, respectively. Trace-level attribution shows that changing battery injection introduces more threshold violations than it removes. Both controllers reduce the maximum ramp but increase the mean absolute ramp. XGBoost improves RMSE while worsening MAE relative to persistence. The results support a reproducible retrospective comparison and failure diagnosis, not guaranteed coverage, net aggregate ramp mitigation, extended battery lifetime or universal controller superiority.

**Keywords:** wind-power forecasting; XGBoost; causal uncertainty; one-sided residual calibration; battery storage; mixed-integer MPC; lexicographic optimisation with tolerance; ramp exceedance.

## 1. Introduction and research gap

Short-horizon wind forecasts can inform battery dispatch, yet point-forecast accuracy and predicted control cost do not establish realised operational benefit. A controller can alter stored-energy inventory, conversion losses and export ramps in different directions. An empirical assessment therefore needs an uncontrolled reference, explicit battery accounting and separate treatment of violation frequency and exceedance magnitude.

Forecast-driven wind–battery MPC and probabilistic dispatch are established [R09–R11]. Conformal and asymmetric renewable forecasts are also established [R03–R08]. The research gap considered here is consequently not the invention of those components. It is the reproducible evaluation of a particular frozen integration, including strict residual timing, mixed-integer physical execution, a development-selected uncertainty policy and an explicit diagnosis when realised aggregate ramp outcomes worsen. Publication value rests on transparent implementation and evidence, including negative findings; a first-ever combination is not asserted.

## 2. Related work

Chen and Guestrin introduced the scalable XGBoost framework [R01], and wind applications such as TS_XGB demonstrate that using boosted trees for short-horizon power forecasting is not itself novel [R02]. Split-conformal regression supplies a model-agnostic calibration framework under its sampling assumptions [R03]. Nonexchangeable extensions and adaptive conformal inference address different forms of drift using specified procedures [R04,R05]. Their guarantees do not automatically apply to a fixed-alpha rolling window with static floors.

Conformal temporal-convolutional wind intervals [R06], asymmetric multi-quantile wind prediction [R07] and conformal PV calibration [R08] precede the present implementation. They motivate reporting empirical calibration and sharpness rather than treating a nominal level as proof of reliability. This work implements a simpler signed lower-margin construction and evaluates downstream control rather than a new interval-prediction architecture.

Constrained battery MPC for smoothing [R09], non-Gaussian stochastic wind–battery MPC [R10] and forecast-informed wind-gradient control [R11] establish the main control context. Lexicographic storage control has also prioritised operating-limit violations over storage losses in a different application [R12]. Wind-fluctuation MPC and filtering alternatives provide additional relevant baselines [R13], but this study does not claim superiority to those implementations. Battery-model reviews and cycle-aging control studies show why fixed-efficiency throughput is not a degradation or lifetime model [R14,R15]. A detailed, source-linked comparison of all fifteen papers is provided in [literature_review.md](literature_review.md). Full-text and bibliographic access limitations are retained there.

## 3. Research contributions and scope

The contributions are: (i) an executable six-horizon uncertainty/control integration with strict target-time eligibility and preserved first-command physical semantics; (ii) paired trace-level accounting of throughput, conversion losses, curtailment, actual export and terminal inventory; and (iii) a reproducible diagnostic separating forecast mismatch, injection changes, objective trade-offs and unidentifiable mechanisms when control worsens aggregate ramps. These are empirical engineering contributions. The study neither supplies a conformal theorem nor isolates the causal effect of adaptation alone, since score direction, static floors and updating rules change together.

## 4. Data and forecasting methodology

The local source is the 2018 turbine SCADA file `T1.csv`, containing timestamps, active power, wind speed, wind direction and a theoretical power curve. Dataset attribution is the [Wind Turbine SCADA Dataset](https://www.kaggle.com/datasets/berkerisen/wind-turbine-scada-dataset). Exact download version, measurement aggregation convention, timezone and redistribution rights require author verification. Negative power is clipped to zero for physical generation/target simulation. Contiguous episodes retain ten-minute observations; gaps and incomplete episode tails are not filled.

Fourteen current/past features comprise power, wind speed and direction; timestamp-based 10/20/30/60-minute power and wind-speed lags; ten-minute power/wind changes; and the mean of current/10/20/30-minute power. Six separately fitted XGBoost models predict the next 10–60 minutes. Historical settings are 300 estimators, depth 4, learning rate 0.05, subsample 0.8, column subsample 0.9, squared-error objective and seed 42. Training retains 60-minute targets strictly before 9 September 2018 02:50. Validation origins begin at that boundary with last targets strictly before 5 November 2018 15:10. No model is fitted or selected during the present evaluation.

The evaluation reuses stored predictions. Independent audit inference with the existing models agrees within 0.000122 kW, consistent with stored numeric precision; raw feature lookup matches current/past measurements. This establishes current artifact consistency, not independently attested provenance of the historical training run. Persistence repeats nonnegative current power at every horizon.

## 5. Causal uncertainty estimation

For origin (a) and horizon (h), the score is (r_{a,h}=hat w_{a,h}-w_{a+hDelta}). At decision (t), only (a+hDelta<t) is eligible. The newest 144 eligible scores form the rolling window; targets equal to the decision are excluded. The finite-sample rank is (lceil145(1-0.10)ceil=131), without interpolation. The adaptive margin is the larger of this signed order statistic and a frozen horizon-specific floor, except for the inherited post-gap fallback rule. The rule uses the floor until 72 selected origins follow 31 October 2018 16:50.

Adaptive floors range from 358.380 to 731.662 kW; fixed absolute-error calibration margins range from 400.014 to 786.613 kW. The complete six-vectors and exact rule appear in Appendix A. The calibration file's latest 60-minute target is 15 October 2018 11:50, before the first scheduled evaluation decision. The adaptive floor values are legacy constants whose derivation is not reproduced by the current calibration file's signed 90th percentiles; no new derivation or calibration claim is invented.

The nominal path is the nonnegative forecast; the downside path is (max(0,hat w-m)). All scheduled observations can be stored in memory, but the strict target filter determines eligibility. Already observed block-6 residuals may enter later windows even though block 6 is not scored. History carries across battery episode resets. The method is rolling conformal-style score calibration with fixed alpha, not the adaptive-alpha algorithm of [R05]. Serial dependence, floors and fallback prevent an asserted distribution-free or joint six-horizon coverage guarantee.

## 6. Battery and scenario model

The battery has 2,000 kWh capacity, 1,000 kW charge/discharge ratings, 800–1,800 kWh stored-energy bounds and 0.95 charging/discharging efficiencies. Decisions use a six-interval horizon with (Delta=1/6) hour. For scenario (s), export and energy satisfy

[
g_{s,k}=w_{s,k}-u_{s,k}-c_{s,k}+d_{s,k},qquad
E_{s,k+1}=E_{s,k}+eta_c c_{s,k}Delta-d_{s,k}Delta/eta_d.
]

Binary modes prohibit simultaneous charging/discharging. Charging uses available wind only, curtailment cannot exceed remaining wind, export is nonnegative, and all planned energy states remain within hard SOC bounds. No additional grid-export cap, grid charging or hard 1,000 kWh reserve is implemented. The reserve is a soft objective target, distinct from the 800 kWh hard lower bound.

Nominal/downside paths receive equal weights. Requested first charge, discharge, curtailment and mode are common; realised first scenario charge and curtailment are exact wind-limited minima implemented with binary selectors. Subsequent planned actions are scenario dependent. This scenario-fan recourse approximation does not constitute a general multistage information tree. Actual h1 generation is accessed only after both optimisation solves commit their requests. The physical simulation applies power, wind-availability and SOC caps before updating actual export and energy.

## 7. Objective priorities and computational settings

The first mixed-integer solve minimises weighted six-step predicted exceedance,

[
J_1^*=minsum_spi_ssum_k e_{s,k},qquad
e_{s,k}ge |g_{s,k}-g_{s,k-1}|-200,quad e_{s,k}ge0.
]

The second solve restricts (J_1le J_1^*+100), then minimises absolute grid ramps, battery-power changes, exceedance, throughput, terminal-energy deviation, curtailment and reserve shortfall. The respective frozen coefficients are 1, 0.1, 20, (0.1Delta), 2, 50 and 100. The terminal and reserve energy references are both 1,000 kWh. Absolute values use linear epigraphs. The mixed-unit weights are not financial prices.

The 100 kW allowance applies to the weighted sum across the horizon, not independently to each interval and not to actual realised ramps. This is lexicographic optimisation with tolerance, not strict primary preservation. Both CVXPY solves call HiGHS and require `optimal` status; an additional guard checks achieved primary cost within the allowance plus 0.001. No explicit thread, seed, time-limit or MIP-gap override is supplied. The recorded environment uses Python 3.12.5, CVXPY 1.9.3 and highspy 1.15.1. Original CSVs omit full planned trajectories, stage costs, optimality gaps and per-decision solve times, limiting retrospective optimisation-certificate and runtime claims. Appendix A specifies all implemented equations, including Big-M selectors and execution caps.

## 8. Experimental design and information limitations

Audited validation predictions were split chronologically into calibration and controller development; eighteen complete development episodes informed the frozen preference for adaptive one-sided MPC. The development comparison showed 43.70% lower throughput, approximately 43.75% lower modelled conversion losses and 0.66% lower exceedance, but eleven more violations (710 versus 699). These were development observations, not confirmatory estimates.

The preserved evaluation schedule identifies fifty complete episodes and explicitly labels block 6 development. The archived scores retain the other 49 episodes, 144 ten-minute intervals each, from November–December 2018. Every episode starts with 1,000 kWh, zero previous battery injection and initial export equal to current nonnegative wind. There are 144 scored transitions, including the initial origin-to-first-output transition, and no cross-episode transition. Both controllers use identical inputs, initial conditions, physical constraints, coefficients and solver interface.

Two qualifications preclude a clean confirmatory holdout interpretation. First, repository history contains evaluation-period event investigations before the freeze. Second, block 6's last development origin is 15 November 2018 12:50 and its six-horizon targets extend to 13:50. Block 7 starts at 13:00; measured target times 13:10–13:50 are shared, comprising fifteen horizon-target pairs and five scored h1 outcomes. The old preflight checks only the eighteen earlier development files and misses this schedule-designated development overlap. Excluding block 6 alone therefore does not establish target-disjoint development/testing. The current package discloses this problem without silently altering the scored set or replacing official totals.

## 9. Mathematical methodology and scoring

Appendix A gives the complete source-matched formulation: notation, forecasting, causal eligibility/order statistic, scenario paths, binary operating modes, first-command minimum selectors, soft reserve, two optimisation priorities, execution and terminal accounting. No unimplemented constraint is added.

A violation is an absolute ten-minute grid change greater than 200.001 kW. Summed exceedance is (sum_imax(0,|g_i-g_{i-1}|-200)), with units kW, not energy. The uncontrolled baseline uses the same target wind, episode boundary and transition count. Mean and maximum ramps are separate metrics.

AC-side throughput is (Deltasum(c+d)). Losses equal (0.05Q_c+(1/0.95-1)Q_d). Energy conservation is checked as wind = actual export + curtailment + conversion loss + stored-inventory change. Terminal adjustment adds (0.95delta E) for surplus or (delta E/0.95) for deficit relative to the initial 1,000 kWh. It is hypothetical inventory restoration, not additional realised export, a feasible future dispatch or revenue.

All differences pair adaptive and fixed within the same episode. Existing 10,000-draw day-bootstrap intervals are retained only as descriptive IID-day resampling outputs; they do not accommodate serial dependence. The new analysis reports within-segment lag correlations and segment totals without changing the bootstrap estimator, tuning block lengths, assigning p-values or selecting controllers. Seven thousand intervals and forty-two thousand horizon comparisons are dependent observations, not independent replications.

## 10. Results

### 10.1 Controller outcomes and the uncontrolled reference

**Table 1.** Original aggregate outcomes on identical 7,056 transitions. Battery energies are AC-side; no-battery throughput/losses are zero.

@@CONTROL_TABLE@@

Adaptive reduces throughput by 27.8644%, modelled conversion losses by 27.9249%, exceedance by 0.7726% and violations by sixteen relative to fixed margins. Nevertheless, fixed and adaptive exceed uncontrolled summed exceedance by 2.82% and 2.03%, respectively, with 37 and 21 more violations. Mean absolute ramp rises from 120.122 kW uncontrolled to 124.344 fixed and 123.654 adaptive. Maximum ramp improves from 2,318.176 kW uncontrolled to 2,174.275 fixed and 2,132.655 adaptive. Thus the direction of benefit depends on the ramp outcome.

![Figure 1. Paired controller outcomes by episode. Each point is one retained block; the dashed line denotes equality. The figure does not imply independent observations.](figures_v2/paired_controllers.png)

### 10.2 Battery use and inventory

**Table 2.** Actual and hypothetical adjusted export, curtailment and inventory. Negative inventory indicates depletion of the episode's initial energy.

@@ENERGY_TABLE@@

Adaptive exports 0.987701 MWh less in the physical simulation but has 0.551229 MWh more hypothetical adjusted export. Fixed also consumes more initial stored inventory, explaining why actual export alone does not identify improved wind capture. Neither terminal adjustment nor throughput establishes battery lifetime benefit.

![Figure 2. Battery AC throughput and conversion/curtailment accounting for both frozen controllers.](figures_v2/battery_energy_accounting.png)

### 10.3 Forecast accuracy and lower-bound coverage

**Table 3.** Point-forecast errors over the same retained origins at each horizon.

@@FORECAST_TABLE@@

XGBoost has higher MAE but lower RMSE at every horizon; its predictive benefit is not uniform across error metrics. **Table 4** reports empirical marginal lower-bound coverage, without a conditional, simultaneous or distribution-free guarantee.

@@COVERAGE_TABLE@@

![Figure 3. MAE and RMSE by horizon against persistence.](figures_v2/forecast_accuracy.png)

![Figure 4. Empirical lower-bound coverage; nominal 90% is a reference, not a proven guarantee.](figures_v2/uncertainty_coverage.png)

Adaptive margins equal their static floors in approximately 86–88% of decisions at each horizon, and none of the evaluated fallback flags is active. The comparison therefore cannot attribute gains specifically to rolling updating or gap fallback.

### 10.4 Block differences and temporal dependence

Exceedance improves in 22 blocks, worsens in 21 and ties in six; the median paired difference is zero. Violation counts improve in 21, worsen in 14 and tie in 14. Throughput decreases in 32 blocks, increases in twelve and ties in five. The existing descriptive resampling bounds for mean paired exceedance are -140.935 to +33.772 kW/block and for violation count -0.980 to +0.286 per block; both span zero and neither is a dependence-adjusted confidence interval for the headline percentage or count difference.

**Table 5.** Chronological segment totals, adaptive minus fixed. These four segments are not assured independent replications.

@@SEGMENT_TABLE@@

Within-segment lag-one correlation of paired exceedance differences is -0.201 using 45 adjacent-day pairs. Other outcomes/lags and the limited pair counts appear in the diagnostic tables; this is descriptive dependence investigation, not validation of an IID resampling model. Development and evaluation also show different relative throughput reductions (43.70% versus 27.86%) and opposite violation-count directions. Unequal exposure and weather prevent raw cross-period totals from identifying distribution-shift effects.

![Figure 5. Control-minus-uncontrolled outcomes by original block. All original episodes remain included.](completion_figures/control_minus_uncontrolled_by_block.png)

## 11. Diagnostic of realised ramp deterioration

For net battery injection (b=d-c), define total controlled injection (j=b-u). Every stored transition satisfies the identity

[
Delta g_i=Delta w_i+Delta j_i,qquad j_0=0 	ext{at episode initialisation}.
]

Here the zero refers to the pre-first-output injection, not the first controlled output. Injection changes can cancel or reinforce wind changes. Fixed introduces 166 threshold violations absent in uncontrolled wind and removes 129, giving net +37. Adaptive introduces 134 and removes 113, giving net +21. Gross added versus removed exceedance is 40,241.350 versus 31,293.343 kW for fixed and 33,187.114 versus 26,758.877 kW for adaptive. Identical timestamps, transition counts and initial references rule out a ramp-accounting mismatch as the explanation in these checks.

The deliberately selected largest fixed deterioration is block 19 at 28 November 2018 07:00: a +0.095 kW wind change becomes a -706.980 kW grid change while net injection changes from +512.363 to -194.712 kW. Adaptive's largest deterioration is block 44 at 25 December 2018 00:30: a -692.038 kW wind change combines with a -531.450 kW injection change. The largest improvement for both occurs in block 25 at 5 December 2018 13:30, where charging of approximately 809.46 kW reduces a +2,148.607 kW wind ramp to approximately +1,339.15 kW. These are labelled diagnostic extremes, not representative independent estimates or favourable controller-selection examples.

![Figure 6. Fixed controller's largest worsening event, including surrounding actual trajectory.](completion_figures/event_fixed_largest_worsening.png)

![Figure 7. Adaptive controller's largest worsening event. Discharging at the current interval does not imply smoothing if discharge decreases sharply relative to the previous interval.](completion_figures/event_adaptive_one_sided_largest_worsening.png)

![Figure 8. Adaptive controller's largest improving event, selected by an explicit diagnostic rule.](completion_figures/event_adaptive_one_sided_largest_improvement.png)

Saved requests and forecast paths permit reconstruction of first-step scenario exports relative to actual previous controlled export. Both first scenarios predict a safe ramp yet an actual violation occurs in 38 fixed and 59 adaptive intervals. This is evidence of scenario/realisation mismatch, not recovery of the unavailable six-step stage objectives. No discharge safety clipping is observed; realised charging is below requested charging in 152 fixed and 85 adaptive intervals. Neither trajectory reaches a hard SOC bound within 0.01 kWh. End-of-interval energy is below the 1,000 kWh soft reserve in 4,186 fixed and 2,281 adaptive intervals.

![Figure 9. SOC range and episode inventory changes. Hard physical feasibility is distinct from ramp performance and the soft reserve objective.](completion_figures/soc_inventory_diagnostic.png)

The code confirms expected trade-offs: forecast-based rather than actual-ramp optimisation, a 100 kW aggregate primary allowance, battery-ramp regularisation, terminal/reference penalties and strongly weighted reserve shortfall. These design properties can affect dispatch, but existing traces cannot identify their separate causal contributions. Claims that the reserve weight or allowance specifically caused the deterioration remain hypotheses requiring a new predeclared experiment. No serious physical-balance or transition-counting implementation error was found by the diagnostic. The confirmed overlap/pre-freeze exposure is instead a scientific-design limitation.

## 12. Discussion

The strongest supported operational result is reduced battery activity and modelled conversion loss relative to another frozen battery controller. The aggregate ramp change is small and heterogeneous. More importantly, both battery controllers worsen count, summed exceedance and mean absolute ramp versus no battery, despite reducing the maximum ramp. A general claim of improved grid stability or net aggregate ramp mitigation would therefore contradict the present evidence.

The negative outcome is consistent with the distinction between planned scenarios and realised wind. Scenario-fan recourse, downwards-only uncertainty paths, a six-step horizon and episode inventory resets can favour actions that are locally plausible in the planning model but create actual injection reversals. These are explanations of possible mechanisms, not experimentally separated effects. The exact injection identity establishes what happened in each realised transition; only controlled, development-designed ablations or genuinely new evaluation data could establish why a particular objective design is preferable.

The comparison is mechanically paired and preserves development selection. It nevertheless bundles score direction, static margins and window updating, so it is not an isolated treatment effect of adaptation. High empirical lower coverage, frequent floor activation and worse MAE than persistence further argue against a simple narrative of more accurate AI forecasts producing universally better control.

## 13. Limitations

The single-turbine, limited-season record, omitted gaps and complete-episode sampling constrain generalisation. Historic model-training provenance cannot be independently certified from source alone. Prior evaluation inspection and development-target overlap invalidate untouched confirmatory language; removing a few targets now would not erase historical exposure. Ordinary day resampling does not correct chronology. The battery is fixed-efficiency and omits temperature, degradation, auxiliary consumption, self-discharge and state-estimation error. Its daily resets and hypothetical terminal restoration do not represent continuous annual operation. Two scenarios do not model a verified joint distribution, recourse is approximate, and soft ramps offer no grid-code or network-flow guarantee. Solver success offline does not establish embedded real-time feasibility. Missing stage trajectories, gaps and timing constrain causal attribution and computational claims. Adaptive floor provenance, exact dataset licence/version and some final bibliographic export details remain author-review items. See [unresolved_scientific_issues.md](unresolved_scientific_issues.md).

## 14. Conclusion

A frozen adaptive one-sided uncertainty configuration uses less battery throughput and incurs fewer modelled conversion losses than the fixed-margin configuration while slightly reducing their aggregate exceedance and violation count. This relative result survives independent trace recomputation and a first-block solver replay. It does not establish untouched generalisation or net ramp mitigation relative to uncontrolled wind: both controllers worsen aggregate exceedance and violations, although the maximum ramp decreases. The study's defensible contribution is an auditable retrospective comparison, explicit inventory accounting and a reproducible negative-outcome diagnostic. Any redesigned controller or revised confirmatory evaluation requires a new freeze and appropriate independent data.

## 15. Reproducibility, software and data availability

The frozen development manifest SHA256 is `b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a`. Frozen sources, models, calibration, datasets, original results and earlier paper/results drafts are preserved. The local audit reconstructs all 42,336 decision/horizon margins and verifies 42,336 raw-target comparisons and 98 physical traces. Existing eight tests and additional dashboard/diagnostic tests are described in the verification report; there is no claim of an independent-personnel or full-platform replication.

The implementation uses CVXPY ([Diamond and Boyd, 2016](https://www.jmlr.org/papers/v17/15-408.html)) and HiGHS ([official solver/citation record](https://highs.dev/)); their software references supplement the fifteen domain/method references below. The local Streamlit app displays historical replay, not a live wind-farm interface. Optional new-directory replay invokes the existing frozen controller runner without parameter changes. Setup, file requirements, limitations and commands appear in [reproducibility.md](reproducibility.md).

Datasets, models and full traces are local ignored artifacts; a fresh clone alone cannot reproduce numerical control results. Summary tables and figures accompany the draft. Before public release the author must establish a permitted versioned artifact-access route, dataset attribution/redistribution terms and project licensing. No data repository DOI or journal acceptance is asserted. Source code and prose should receive author/supervisor review, including institutional requirements for disclosure of computational and AI assistance. The paper has not been submitted or published by this task.

## 16. Verified references

Reference identifiers R01–R15 correspond to the source-linked comparison in `literature_review.md`. Verification used publisher, author or institutional primary records; limitations remain explicit rather than inventing metadata or DOIs.

@@REFERENCES@@

## Appendix A. Complete source-matched mathematical formulation

@@APPENDIX@@
'''
    refs=json.loads((ROOT/'docs/literature_verified.json').read_text(encoding='utf-8'))['references']
    references='\n\n'.join(f"**[{r['id']}]** {r['reference_markdown']}" for r in refs)
    appendix=(ROOT/'docs/mathematical_formulation.md').read_text(encoding='utf-8').split('\n',1)[1]
    appendix=appendix.replace('\n## ','\n### ')
    for token,value in {'@@CONTROL_TABLE@@':control_table,'@@ENERGY_TABLE@@':energy_table,'@@FORECAST_TABLE@@':forecast_table,'@@COVERAGE_TABLE@@':coverage_table,'@@SEGMENT_TABLE@@':segment_table,'@@REFERENCES@@':references,'@@APPENDIX@@':appendix}.items():
        paper=paper.replace(token,value)
    target=ROOT/'docs/paper_submission_draft.md'
    with target.open('x',encoding='utf-8') as handle:handle.write(paper)
    print('Created separate supervisor-review manuscript:',target)

if __name__=='__main__':main()
