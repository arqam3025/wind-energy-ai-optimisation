# Mathematical formulation of the frozen implementation

This appendix specifies the implemented controllers, not a redesigned controller. Equations correspond to `scripts/frozen_fixed_heldout.py`, `scripts/frozen_adaptive_one_sided_heldout.py` and the hash-verified uncertainty module. The archived 49-block results are retrospective: pre-freeze test-period access and development block 6's overlap with block 7 preclude an untouched confirmatory-test interpretation.

## 1. Time, notation and assumptions

Let a decision origin be \(t\), the interval length \(\Delta=1/6\) hour, and the horizon \(H=6\). Forecast index \(h=1,\ldots,6\) targets \(t+h\Delta\); optimisation index \(k=0,\ldots,5\) corresponds to \(h=k+1\). All timestamps use the dataset's unconfirmed, timezone-naive clock. The simulator treats each target power sample as the representative power for the ten-minute control interval ending at that target; continuous intra-interval dynamics are not modelled.

| Symbol | Definition / frozen value |
| --- | --- |
| \(y_t,w_t\) | Measured power, and its nonnegative simulation value \(w_t=\max(0,y_t)\), kW |
| \(\hat w_{t,h}\) | Nonnegative XGBoost forecast, kW |
| \(E_t\) | Battery stored energy at the decision, kWh |
| \(g_t^-,b_t^-\) | Previous realised grid export and net battery injection, kW |
| \(c,d,u,g\) | Charge, discharge, curtailment and grid-export power, kW |
| \(b=d-c\) | Net battery injection, kW |
| \(C,P\) | Battery capacity 2,000 kWh; charge/discharge rating 1,000 kW |
| \(E_{\min},E_{\max}\) | 800 and 1,800 kWh; SOC bounds 40–90% |
| \(E_{\rm ref},E_{\rm res}\) | Terminal reference and soft reserve target, both 1,000 kWh |
| \(\eta_c,\eta_d\) | Charge and discharge efficiency, both 0.95 |
| \(R,\varepsilon\) | Ramp threshold 200 kW; aggregate primary allowance 100 kW |
| \(s,\pi_s\) | Nominal/downside scenario, each with weight 0.5 |

Episodes start with \(E_t=1000\), \(b_t^-=0\) and \(g_t^-=\max(0,y_t)\). Later decisions use the preceding actual export and battery injection. Battery state resets between episodes; uncertainty history does not. The reset does not simulate replenishment between consecutive episodes. A 200 kW change over ten minutes corresponds to 20 kW/min; the implementation penalises power differences, not a time-normalised ramp derivative.

## 2. Multi-horizon forecasts

Six separately fitted historical regressors supply

\[
\hat w_{t,h}=\max\{0,f_h(x_t)\},\qquad
f_h(x)=b_h+\sum_{m=1}^{300}T_{h,m}(x),\quad h=1,\ldots,6.
\tag{1}
\]

Here \(b_h\) denotes the fitted base score and \(T_{h,m}\) the stored tree contribution including shrinkage; this is a representation of the fitted predictor, not a new training objective. Inputs are current power, wind speed/direction, timestamp-joined 10/20/30/60-minute power and wind-speed lags, ten-minute power/wind changes and the mean of current/10/20/30-minute power. Historical settings are depth 4, learning rate 0.05, subsample 0.8, column subsample 0.9, squared-error objective and seed 42. The historical training script keeps 60-minute targets strictly before 9 September 2018 02:50. Current control evaluation reads stored predictions and never fits \(f_h\). Persistence is \(\max(0,y_t)\) at every horizon.

## 3. Causal one-sided uncertainty

For forecast origin \(a\), define the signed overprediction residual

\[
r_{a,h}=\hat w_{a,h}-\max(0,y_{a+h\Delta}),\qquad
\mathcal I_{t,h}=\{a:a+h\Delta<t\}.
\tag{2}
\]

The strict inequality excludes targets equal to the current decision. Select the most recent \(n=144\) eligible residuals in chronological origin order, denoted \(\mathcal W_{t,h}\). Fewer than 144 causes an error, not a shortened window. With \(\alpha=0.10\),

\[
\ell=\lceil(n+1)(1-\alpha)\rceil=131,\qquad
q_{t,h}=r_{(\ell)}(\mathcal W_{t,h}).
\tag{3}
\]

There is no quantile interpolation. Let \(a_0\) be 31 October 2018 16:50 and \(N_{t,h}=\sum_{a\in\mathcal W_{t,h}}\mathbf1[a\ge a_0]\). With static floors

\[
F=(358.379810,504.728717,571.614234,630.176420,690.977755,731.661882),
\]

the adaptive margin is

\[
m_{t,h}=\begin{cases}
F_h,&t\ge a_0\ \text{and}\ N_{t,h}<72,\\
\max(F_h,q_{t,h}),&\text{otherwise}.
\end{cases}\tag{4}
\]

The fixed controller instead uses the pre-existing absolute-error calibration order statistics, approximately
\((400.013625,536.120393,608.362375,673.969433,727.956806,786.612838)\) kW. It does not apply Eq. (4). The legacy adaptive floor values are frozen constants, not recomputed signed 90th percentiles of the current calibration file. Their derivation remains an unresolved provenance item. These rolling scores/floors do not establish exchangeability-based or adaptive-alpha coverage guarantees.

The scenario forecasts are

\[
w^{(0)}_{t,k}=\hat w_{t,k+1},\qquad
w^{(1)}_{t,k}=\max(0,\hat w_{t,k+1}-m_{t,k+1}).\tag{5}
\]

Both scenarios are heuristic planning paths, not an asserted joint predictive distribution. Full scheduled history is preloaded, but only Eq. (2)'s eligible residuals influence Eq. (3). Past block-6 observations may become causal history; this does not remove block 6's separate development/test-overlap issue.

## 4. Mixed-integer scenario constraints

At each decision, nonnegative requested first actions \(\bar c,\bar d,\bar u\) and binary mode \(\bar z\) satisfy

\[
0\le\bar c\le P\bar z,\quad
0\le\bar d\le P(1-\bar z),\quad
\bar c\le\frac{E_{\max}-E_t}{\eta_c\Delta},\quad
\bar d\le\frac{(E_t-E_{\min})\eta_d}{\Delta}.
\tag{6}
\]

For each scenario, variables \(c_{s,k},d_{s,k},u_{s,k}\ge0\), \(z_{s,k}\in\{0,1\}\) and \(E_{s,k}\) obey

\[
g_{s,k}=w^{(s)}_{t,k}-u_{s,k}-c_{s,k}+d_{s,k}\ge0,\tag{7}
\]
\[
E_{s,0}=E_t,\quad E_{\min}\le E_{s,k}\le E_{\max}\ (k=0,\ldots,H),
\tag{8}
\]
\[
0\le c_{s,k}\le Pz_{s,k},\quad
0\le d_{s,k}\le P(1-z_{s,k}),\quad
0\le u_{s,k}\le w^{(s)}_{t,k},\quad
c_{s,k}\le w^{(s)}_{t,k}-u_{s,k},\tag{9}
\]
\[
E_{s,k+1}=E_{s,k}+\eta_c c_{s,k}\Delta-d_{s,k}\Delta/\eta_d.\tag{10}
\]

The first discharge and mode satisfy \(d_{s,0}=\bar d\), \(z_{s,0}=\bar z\). Realised first charging and curtailment are scenario-dependent wind-limited versions of the shared requests. Define \(M_s=P+\max(w^{(s)}_{t,0},P)\) and selectors \(\sigma_s,\chi_s\in\{0,1\}\). The exact implemented inequalities are

\[
\begin{aligned}
c_{s,0}&\le\bar c,&c_{s,0}&\le w^{(s)}_{t,0},\\
c_{s,0}&\ge\bar c-M_s\sigma_s,&
c_{s,0}&\ge w^{(s)}_{t,0}-M_s(1-\sigma_s),
\end{aligned}\tag{11}
\]
\[
\begin{aligned}
u_{s,0}&\le\bar u,&u_{s,0}&\le w^{(s)}_{t,0}-c_{s,0},\\
u_{s,0}&\ge\bar u-M_s\chi_s,&
u_{s,0}&\ge w^{(s)}_{t,0}-c_{s,0}-M_s(1-\chi_s).
\end{aligned}\tag{12}
\]

These implement minima for feasible requests. There is no additional explicit rating bound on requested curtailment in the code; the Big-M inequalities restrict its feasible range indirectly. No grid-export upper bound, grid charging, battery-ramp hard constraint or hard 1,000 kWh reserve is introduced. Later actions may depend on the entire scenario path: this is a scenario-fan recourse approximation, not a general fully nonanticipative multistage tree.

## 5. Two optimisation priorities

Define differences using \(g_{s,-1}=g_t^-\) and \(b_{s,-1}=b_t^-\), where \(b_{s,k}=d_{s,k}-c_{s,k}\). Introduce nonnegative epigraphs \(A_{s,k},B_{s,k},e_{s,k},v_{s,k}\):

\[
A_{s,k}\ge\pm(g_{s,k}-g_{s,k-1}),\quad
B_{s,k}\ge\pm(b_{s,k}-b_{s,k-1}),\tag{13}
\]
\[
e_{s,k}\ge A_{s,k}-R,\qquad E_{s,k+1}+v_{s,k}\ge E_{\rm res}.\tag{14}
\]

First solve the mixed-integer linear problem

\[
J_1^*=\min\sum_s\pi_s\sum_{k=0}^{H-1}e_{s,k}.\tag{15}
\]

Then solve over the same variables and constraints

\[
\min J_2,\qquad \sum_s\pi_s\sum_ke_{s,k}\le J_1^*+100,\tag{16}
\]

where

\[
\begin{aligned}
J_2=\sum_s\pi_s\bigg[&\sum_k A_{s,k}+0.1\sum_k B_{s,k}
+20\sum_ke_{s,k}+0.1\Delta\sum_k(c_{s,k}+d_{s,k})\\
&+2|E_{s,H}-1000|+50\sum_ku_{s,k}+100\sum_kv_{s,k}\bigg].
\end{aligned}\tag{17}
\]

All sums over \(k\) run from 0 to 5. The terminal absolute value is represented by CVXPY's linear epigraph conversion. Mixed-unit objective coefficients are empirical research weights, not money. The 100 kW allowance is a substantive bound on a **weighted sum over six horizon steps**, not 100 kW independently at each step or a negligible numerical epsilon. It is tolerance-constrained lexicographic optimisation.

Both stages call `problem.solve(solver=cp.HIGHS)` and require status `optimal`. The implementation additionally checks that achieved primary epigraph cost is at most \(J_1^*+100+10^{-3}\). Original traces do not retain either stage's objective values, solver gaps or per-decision times; these cannot be recovered from one-step dispatch traces. No explicit solver seed, thread count, time limit or MIP-gap override is supplied. The recorded stack is Python 3.12.5, CVXPY 1.9.3 and highspy 1.15.1; see the preserved full environment snapshot for other packages.

## 6. Committed actions and physical execution

After both solves, requested actions are committed as \(C=\max(0,\bar c^*)\), \(D=\max(0,\bar d^*)\), \(U=\max(0,\bar u^*)\). Only then is actual next-target wind \(w^+=\max(0,y_{t+\Delta})\) read. Execution is

\[
c^a=\min\left(C,w^+,P,\frac{\max(0,E_{\max}-E_t)}{\eta_c\Delta}\right),\tag{18}
\]
\[
d^a=\min\left(D,P,\frac{\max(0,E_t+\eta_c c^a\Delta-E_{\min})\eta_d}{\Delta}\right),\tag{19}
\]
\[
u^a=\min(U,\max(0,w^+-c^a)),\quad
g^a=w^+-c^a-u^a+d^a,\quad
E^+=E_t+\eta_c c^a\Delta-d^a\Delta/\eta_d.\tag{20}
\]

The next state uses \(g_t^-\leftarrow g^a\), \(b_t^-\leftarrow d^a-c^a\), \(E_t\leftarrow E^+\). This ideal wind-availability limiter is part of the simulator, not evidence of implemented real-time inverter control. The stored output timestamp is the decision time plus ten minutes.

## 7. Scoring and inventory accounting

For episode output \(i=1,\ldots,144\), let \(g_0\) be the initial origin's clipped wind. The exact metrics are

\[
V=\sum_{i=1}^{144}\mathbf1[|g_i-g_{i-1}|>200.001],\qquad
X=\sum_{i=1}^{144}\max(0,|g_i-g_{i-1}|-200).\tag{21}
\]

The uncontrolled baseline replaces \(g_i\) with the same actual target wind and uses the same initial value. The threshold tolerance affects the count, not the exceedance sum. \(X\) has units kW; it is not energy. There are no cross-episode export transitions in the score.

\[
Q_c=\Delta\sum_ic_i^a,\quad Q_d=\Delta\sum_id_i^a,\quad
T=Q_c+Q_d,\quad L=(1-\eta_c)Q_c+(\eta_d^{-1}-1)Q_d.\tag{22}
\]
\[
W=G+U_E+L+\delta E,\quad
\delta E=E_{144}-1000,\quad G=\Delta\sum_i g_i^a,\quad U_E=\Delta\sum_i u_i^a.\tag{23}
\]
\[
G_{\rm adj}=G+\begin{cases}\eta_d\delta E,&\delta E\ge0,\\\delta E/\eta_c,&\delta E<0.\end{cases}\tag{24}
\]

Equation (24) values inventory restoration hypothetically; no feasible restoration trajectory, future wind, time, ramp consequence or price is simulated. It is reported alongside, not in place of, actual export. MAE and RMSE use all equally weighted retained origins at each horizon. Empirical lower-bound coverage is \(N^{-1}\sum_t\mathbf1[w_{t+h\Delta}\ge\max(0,\hat w_{t,h}-m_{t,h})]\), without a joint or conditional coverage guarantee.

## Implementation checks and unresolved issues

The original eight tests verify frozen optimisation/execution body equality, causal target exclusion and physical-accounting checks. The independent audit reconstructs all adaptive margins and raw targets and reproduces stored predictions with the current models. This appendix does not establish historic test blindness or independently attest original training inputs. The six-step block-6 development horizon overlaps five block-7 scored target times. Neither the scored set nor the controller is changed in this package. Original results and manifest remain the authoritative archived experiment.
