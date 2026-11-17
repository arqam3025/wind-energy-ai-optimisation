# Limitations and interpretation

- One turbine, one 2018 record and a limited seasonal held-out period do not establish transfer across sites, weather regimes or years. Scheduled complete episodes omit gaps and tails and may favour data-rich operation.
- Legacy evaluation results already exist. The freeze establishes separation for this controller comparison; it cannot prove that every historic investigator was blind to the reserved periods. Block 6 is explicitly development and excluded.
- Rolling signed residual calibration is causal but temporally dependent. Finite-sample exchangeability-based coverage guarantees are not established. Static floors and the hard-coded gap rule are inherited decisions; neither is re-tuned here.
- Stored-energy resets every 24-hour episode are idealisations. Boundary ramps are scored against current wind rather than the preceding episode's controlled export; there is no continuous year-long battery trajectory.
- A fixed 100 kW allowance in stage 2 permits primary-objective degradation. Describe the controller as two-stage lexicographic with tolerance, not exact lexicographic optimisation.
- Point forecasts and two scenarios provide a limited uncertainty representation. Scenario-dependent later decisions are planning recourse, not knowledge of future outcomes. Actual h1 outcomes only enter after commands are committed.
- A simplified battery has fixed efficiencies and no temperature, degradation, replacement cost, auxiliary loads, self-discharge, inverter dynamics or measured state-estimation error. Lower throughput suggests lower cycling exposure, not a quantified lifetime benefit.
- Grid ramp exceedance is softened in the objective, so violations remain possible. There is no certified grid-code compliance claim or network-power-flow validation. The ramp threshold and battery sizing are research assumptions.
- Terminal-SOC adjustment is hypothetical and may require future imported charging energy, export opportunity or additional operating time. It is not realised export or revenue. Report actual export, curtailment, conversion losses and inventory change as well.
- Descriptive paired bootstrap intervals assume exchangeable blocks for resampling; actual temporal dependence limits their interpretation. No confirmatory p-values or superiority claims follow from them.
- Frozen model and forecast provenance is historical. Replaying stored forecasts is reproducible control evaluation, not independent reproduction of every original training decision. No retraining was performed.
- Runtime and solver stability are assessed on the local software stack. Offline successful optimisation does not demonstrate ten-minute real-time feasibility on an embedded deployment platform.
- Development throughput improved 43.70% and exceedance 0.66%, while violation count increased by 11. This trade-off must remain visible even if aggregate held-out metrics favour the development-selected controller.
