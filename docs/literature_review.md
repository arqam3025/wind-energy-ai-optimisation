# Literature review and bounded novelty assessment

Verified on 29 October 2026 against academic publisher pages, published papers and author/institutional repositories. Fifteen published journal or peer-reviewed conference papers are considered below. Search terms covered XGBoost wind forecasts, conformal renewable forecasts, exchangeability and distribution shift, wind–battery predictive control, lexicographic storage control, and battery losses/cycle aging. This is a focused review, not an exhaustive systematic review or a certification that no identical combination exists.

DOIs refer to the published articles, not substituted preprint identifiers. R05 has a verified NeurIPS proceedings record but no proceedings DOI was identified; none is invented. Publication-year differences between an online version and its eventual issue are explicitly noted where relevant. An inaccessible full text limits the comparison to verified abstract/method metadata; “not assessed” does not mean the original work omitted that topic.

## Comparison with the present study

The present work uses frozen direct XGBoost models at six 10–60-minute horizons; fixed absolute-error margins or causal rolling signed overprediction margins; equal-weight nominal/downside scenarios; mixed-integer battery constraints; and two objective-priority solves with a 100 kW primary allowance. It compares two controller configurations on 49 scheduled 24-hour episodes. The existing numerical totals are retained, but prior evaluation-period access and block-6/block-7 target overlap require retrospective rather than untouched-confirmatory interpretation. Neither configuration improves aggregate exceedance or violation counts over uncontrolled wind. Battery throughput and conversion losses are modeled; degradation and lifetime are not.

| Ref. | Forecasting | Uncertainty modeling | Control strategy | Battery/storage modeling | Evaluation evidenced by the source | Difference from this research |
| --- | --- | --- | --- | --- | --- | --- |
| R01 | General boosted decision-tree learning | Not a conformal forecast method | No battery controller | Not applicable | Machine-learning scalability and benchmark experiments | Establishes XGBoost; six wind horizons and control integration are applications, not a new boosting algorithm |
| R02 | Time/spatial feature fusion with XGBoost for very short-term wind | Point forecast evaluation | No MPC assessed | Not applicable | Ruoqiang wind-farm data; reported 10-fold cross-validation | Our timestamp-purged forecasting design and control accounting differ; cross-validation performance cannot be transferred directly |
| R03 | Any regression estimator | Full/split conformal prediction under the paper's sampling assumptions | No dispatch controller | Not applicable | Theory, simulations and regression applications | Grounds finite-sample calibration; does not validate our dependent rolling-window/floor procedure |
| R04 | Model-agnostic predictive inference | Weighted conformal methods addressing drift/nonexchangeability | No battery dispatch | Not applicable | Theory plus electricity/election forecasting experiments | Shows that robustness to drift requires specified methods/assumptions; our fixed-alpha window is not this algorithm |
| R05 | Black-box forecasting wrapper | Online adaptation of a miscoverage parameter | No storage MPC assessed | Not applicable | Distribution-shift theory and real-data examples | Our window updates residuals while keeping alpha fixed; ACI guarantees must not be borrowed |
| R06 | Temporal convolutional quantile networks for wind | Conformalized quantile intervals | No battery MPC assessed | Not applicable | Simulation and two geographically different wind datasets | Conformal wind forecasting predates this study; our marginal downside scenarios and control outcomes differ |
| R07 | Day-ahead multi-quantile generative Transformer | Asymmetric bounds and conformal quantile calibration | No battery dispatch assessed | Not applicable | Four wind farms; coverage/width/interval-score comparisons | Asymmetric conformal wind intervals are established; our signed lower margins are simpler and not a novelty theorem |
| R08 | Day-ahead linear/random-forest PV prediction | Weighted, local, binned and predictive-system conformal variants | No MPC assessed | Not applicable | Dutch PV/weather datasets; interval reliability and sharpness | Renewable CP is established; our contribution concerns frozen downstream battery accounting rather than a new CP family |
| R09 | Multi-step wind prediction | Forecast-error effects, not conformal calibration | Constrained MPC for wind smoothing | Battery SOC and practical operating bounds | Closed-loop simulation using real wind-farm data | Wind–battery smoothing with forecast MPC predates this work; our uncertainty wrapper and paired frozen comparison differ |
| R10 | Probabilistic wind forecasts, including non-Gaussian uncertainty | Chance-constrained stochastic formulation | Stochastic battery MPC for dispatch tracking | BESS operational constraints | Actual Chinese wind-farm data | Uncertainty-aware wind–battery MPC is established; our two discrete scenarios and ramp-priority tolerance are different approximations |
| R11 | Wind forecasts used in receding-horizon operation | Forecast disturbances in closed-loop tests | Convex reformulation for wind-power gradients | Local storage plus turbine-inertia energy flows | Closed-loop tests with real wind data | Gradient control and energy-loss trade-offs are established; our turbine is an exogenous source and has no inertia/pitch/torque control |
| R12 | Predicted substation loading | Real-time correction addresses prediction/model error | Lexicographic MPC plus lower-level correction | Experimentally identified flywheel losses and limits | Simulation and physical testbed | Priority of violations versus storage losses is established; this is flywheel peak shaving, not causal wind–battery calibration |
| R13 | Wind-power fluctuations as control input | No conformal layer assessed | MPC and improved low-pass filtering alternatives | Hybrid energy storage | Comparative wind-fluctuation mitigation study | Supplies relevant non-AI control comparisons; our study does not establish superiority to these methods |
| R14 | Not a forecasting contribution | Discusses model uncertainty and missing dynamics | Review of battery models for optimal control | SOC, thermal and degradation model families | Review with example controller designs | Explains why fixed-efficiency energy accounting cannot establish lifetime benefit or capture all battery dynamics |
| R15 | Future instruction uncertainty | Online control with incomplete future information | Cycle-aging-aware threshold policy and offline comparison | Rainflow cycle-based degradation | Theory; synthetic and real regulation traces | Demonstrates explicit cycle-depth accounting; our throughput proxy is not an implemented degradation model |

Each row is supported by its linked primary record below. No cross-paper numerical performance ranking is appropriate: sites, horizons, constraints, baselines and outcomes differ.

## Established methods and the defensible research gap

XGBoost itself and its use for wind forecasting are established [R01–R02]. Conformal wind forecasting, asymmetric intervals and renewable calibration also predate this project [R03–R08]. Forecast-driven and stochastic wind–battery MPC, gradient constraints, and storage losses have a substantial prior literature [R09–R14]. Cycle-aging-aware control requires more than a throughput total [R15]. These facts rule out a defensible claim that the project invented XGBoost wind forecasting, conformal renewable uncertainty, battery MPC, lexicographic storage control, or degradation-aware dispatch.

The potentially original contribution is narrower: an executable and auditable integration of (i) strict target-time eligibility for six rolling signed-error margins, (ii) shared first-command mixed-integer scenario MPC with a frozen primary allowance, and (iii) paired trace-level comparisons separating throughput, conversion losses, actual export, terminal inventory and ramp counts/magnitudes. Its value includes reporting the negative uncontrolled-baseline comparison and preserving the development-selection trade-off. This is an empirical engineering contribution whose originality must be assessed against additional close implementations and the final manuscript; this review does not establish a first-ever combination.

The design compares complete controller configurations, not a controlled ablation of rolling adaptation alone. Different score direction, static margins and updating rules change together. Existing audit evidence finds margins at their static floors for roughly 86–88% of decisions and no active fallback flags during evaluation. Therefore, attributing the 27.86% throughput reduction specifically to adaptation or to gap fallback is not supported. A component-level causal claim would require development-designed ablations and a new evaluation protocol.

## Causal, one-sided and statistical qualifications

For the implemented lower bound, an overprediction residual is forecast minus later actual generation. Selecting only residual targets strictly before a decision establishes an operational information boundary. It does not establish exchangeability or make all historical development/test use independent. A signed one-sided quantile is a standard score/calibration construction rather than a new general uncertainty theorem [R03–R05]. Claims about conditional, simultaneous multi-horizon or arbitrary-shift coverage would need separate theory and a matching implementation.

The current study may report empirical horizon-wise coverage and paired descriptive differences. It must not transfer finite-sample or long-run guarantees from R03–R05 to its static floors, hard-coded gap fallback and dependent rolling windows. Likewise, ordinary independent daily resampling does not correct serial dependence merely because its intervals are labeled descriptive. The historical test exposure and development-target overlap should remain visible in the experimental design.

## Verified reference register

### R01 — XGBoost foundation

Chen, T., and Guestrin, C. (2016). **XGBoost: A Scalable Tree Boosting System.** Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, 785–794. [Published DOI: 10.1145/2939672.2939785](https://doi.org/10.1145/2939672.2939785). [Author manuscript and published-DOI record](https://arxiv.org/abs/1603.02754).

### R02 — XGBoost wind forecasting

Jiang, J., Wang, F., Tang, R., Zhang, L., and Xu, X. (2022). **TS_XGB: Ultra-Short-Term Wind Power Forecasting Method Based on Fusion of Time-Spatial Data and XGBoost Algorithm.** Procedia Computer Science, 199, 1103–1111 (ITQM conference proceedings). [Published DOI: 10.1016/j.procs.2022.01.140](https://doi.org/10.1016/j.procs.2022.01.140). [Publisher record](https://www.sciencedirect.com/science/article/pii/S1877050922001417). [Official ITQM 2020/2021 programme, corroborating author set and conference context](https://www.hse.ru/data/2021/08/25/1414853066/ITQM%20Program.pdf). The programme and final indexed article use different author ordering; the bibliography here follows the final article's Jiang-first record, corroborated in published citations. Full publisher PDF access was restricted during verification; no unobserved implementation detail is asserted.

### R03 — Split-conformal regression

Lei, J., G'Sell, M., Rinaldo, A., Tibshirani, R. J., and Wasserman, L. (2018). **Distribution-Free Predictive Inference for Regression.** Journal of the American Statistical Association, 113(523), 1094–1111. [Published DOI: 10.1080/01621459.2017.1307116](https://doi.org/10.1080/01621459.2017.1307116). [Author-hosted published article](https://www.stat.cmu.edu/~ryantibs/papers/conformal-jasa.pdf). Online-first records can show 2017; 2018 is the journal-issue year.

### R04 — Nonexchangeable conformal inference

Barber, R. F., Candès, E. J., Ramdas, A., and Tibshirani, R. J. (2023). **Conformal prediction beyond exchangeability.** The Annals of Statistics, 51(2), 816–845. [Published DOI: 10.1214/23-AOS2276](https://doi.org/10.1214/23-AOS2276). [Publisher article](https://projecteuclid.org/journals/annals-of-statistics/volume-51/issue-2/Conformal-prediction-beyond-exchangeability/10.1214/23-AOS2276.pdf).

### R05 — Adaptive conformal inference

Gibbs, I., and Candès, E. (2021). **Adaptive Conformal Inference Under Distribution Shift.** Advances in Neural Information Processing Systems, 34. [Official peer-reviewed proceedings record and paper](https://papers.nips.cc/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html). No proceedings DOI identified. The arXiv DOI identifies a preprint and is intentionally not presented as the published DOI.

### R06 — Conformal wind intervals

Hu, J., Luo, Q., Tang, J., Heng, J., and Deng, Y. (2022). **Conformalized temporal convolutional quantile regression networks for wind power interval forecasting.** Energy, 248, 123497. [Published DOI and publisher record: 10.1016/j.energy.2022.123497](https://doi.org/10.1016/j.energy.2022.123497). Author roles are visible in the publisher's credit statement; the abstract and experimental description support the comparison above.

### R07 — Asymmetric conformal wind intervals

Wang, W., Feng, B., Huang, G., Guo, C., Liao, W., and Chen, Z. (2023). **Conformal asymmetric multi-quantile generative transformer for day-ahead wind power interval prediction.** Applied Energy, 333, 120634. [Published DOI: 10.1016/j.apenergy.2022.120634](https://doi.org/10.1016/j.apenergy.2022.120634). [Author-institution metadata](https://vbn.aau.dk/en/publications/conformal-asymmetric-multi-quantile-generative-transformer-for-da/), [publisher abstract/method record](https://www.sciencedirect.com/science/article/abs/pii/S0306261922018918). The DOI contains 2022; the journal issue is 2023.

### R08 — Renewable conformal calibration

Renkema, Y., Visser, L., and AlSkaif, T. (2024). **Enhancing the reliability of probabilistic PV power forecasts using conformal prediction.** Solar Energy Advances, 4, 100059. [Published DOI: 10.1016/j.seja.2024.100059](https://doi.org/10.1016/j.seja.2024.100059). [Author-institution published PDF](https://dbc.library.uu.nl/bitstream/handle/1874/451621/1-s2.0-S2667113124000093-main.pdf?isAllowed=y&sequence=1), [publisher record](https://www.sciencedirect.com/science/article/pii/S2667113124000093).

### R09 — Wind smoothing with battery MPC

Khalid, M., and Savkin, A. V. (2010). **A model predictive control approach to the problem of wind power smoothing with controlled battery storage.** Renewable Energy, 35(7), 1520–1526. [Published DOI: 10.1016/j.renene.2009.11.030](https://doi.org/10.1016/j.renene.2009.11.030). [Author-institution record](https://pure.kfupm.edu.sa/en/publications/a-model-predictive-control-approach-to-the-problem-of-wind-power-/). The DOI contains 2009; the issue is July 2010.

### R10 — Stochastic wind–battery MPC

Kou, P., Gao, F., and Guan, X. (2015). **Stochastic predictive control of battery energy storage for wind farm dispatching: Using probabilistic wind power forecasts.** Renewable Energy, 80, 286–300. [Published DOI: 10.1016/j.renene.2015.02.001](https://doi.org/10.1016/j.renene.2015.02.001). [Publisher record](https://www.sciencedirect.com/science/article/pii/S0960148115000919). The retrieved publisher abstract supports chance constraints, non-Gaussian forecasts and constrained BESS dispatch; it does not establish applicability to this project's exact ramp objective.

### R11 — Forecast-informed wind gradients

Hovgaard, T. G., Boyd, S., and Jørgensen, J. B. (2015). **Model predictive control for wind power gradients.** Wind Energy, 18(6), 991–1006. [Published DOI: 10.1002/we.1742](https://doi.org/10.1002/we.1742). [Author-institution record](https://orbit.dtu.dk/en/publications/model-predictive-control-for-wind-power-gradients/), [author manuscript](https://stanford.edu/~boyd/papers/pdf/wind_gradients_cvx.pdf). Do not confuse this three-author journal article with the four-author 2013 ECC paper of a related title.

### R12 — Lexicographic predictive storage control

Tziovani, L., Hadjidemetriou, L., Charalampous, C., Tziakouri, M., Timotheou, S., and Kyriakides, E. (2021). **Energy Management and Control of a Flywheel Storage System for Peak Shaving Applications.** IEEE Transactions on Smart Grid, 12(5), 4195–4207. [Published DOI: 10.1109/TSG.2021.3084814](https://doi.org/10.1109/TSG.2021.3084814). [Author-deposited published-version record](https://zenodo.org/records/4888894), [European Commission OneNet project publication record](https://cordis.europa.eu/project/id/957739/results). The author deposit establishes the method and author set; the project's official funder record independently confirms the final 2021 volume/issue, pages, full author order and DOI. The Crossref API and direct IEEE export were inaccessible to this browsing tool; those failures are not represented as successful verification.

### R13 — MPC and filtering baselines

Sun, Y., Tang, X., Sun, X., Jia, D., Cao, Z., Pan, J., and Xu, B. (2019). **Model predictive control and improved low-pass filtering strategies based on wind power fluctuation mitigation.** Journal of Modern Power Systems and Clean Energy, 7, 512–524. [Published DOI and publisher record: 10.1007/s40565-018-0474-5](https://doi.org/10.1007/s40565-018-0474-5). Online publication was 26 December 2018; 2019 is the issue year.

### R14 — Battery models and losses

Rosewater, D. M., Copp, D. A., Nguyen, T. A., Byrne, R. H., and Santoso, S. (2019). **Battery Energy Storage Models for Optimal Control.** IEEE Access, 7, 178357–178391. [Published DOI: 10.1109/ACCESS.2019.2957698](https://doi.org/10.1109/ACCESS.2019.2957698). [Author's Sandia dissertation, identifying the article and its model-review contribution](https://www.sandia.gov/ess-ssl/wp-content/uploads/2020/09/DM_Rosewater_Dissertation.pdf), [author laboratory publication record](https://energy.sandia.gov/staff/ray-byrne/). The IEEE DOI endpoint was not fully accessible to the browsing tool; the primary author/laboratory records corroborate the publication.

### R15 — Explicit cycle-aging control

Shi, Y., Xu, B., Tan, Y., Kirschen, D. S., and Zhang, B. (2019). **Optimal Battery Control Under Cycle Aging Mechanisms in Pay for Performance Settings.** IEEE Transactions on Automatic Control, 64(6), 2324–2339. [Published DOI: 10.1109/TAC.2018.2867507](https://doi.org/10.1109/TAC.2018.2867507). [Author manuscript and publication-status record](https://arxiv.org/abs/1709.05715), [IEEE Control Systems Society's 2019 journal index](https://ieeecss.org/sites/ieeecss/files/2020-08/Index_2019.pdf), [author implementation](https://github.com/Yuanyuan-Shi/Cycle-based-Battery-Controller). The manuscript appeared earlier online; 2019 is the volume year.

## Remaining literature tasks before submission

Use the final target journal's reference manager export to normalise names, diacritics, proceedings metadata and any issue/page fields not required above. Obtain institutionally accessible full texts for records limited to publisher abstracts before claiming finer mathematical equivalence. Expand the search to close one-sided scenario-MPC implementations and independent experimental validation. None of these checks warrants changing frozen parameters, selecting a different controller, or replacing the existing numerical comparison.
