# Methods — sanitized development-code summary

This is a new public summary of implemented contracts, not the original private
methods/audit record. Original source and scientific measurements remain unchanged.

The target is nonnegative measured electrical generation in kW,
`y = max(0, raw_power_kw)`. SCADA generation does not establish unconstrained
available wind potential under outages or curtailment. Signed raw input features
are retained according to the declared feature definitions.

Persistence, XGBoost and LightGBM adapters share fourteen feature definitions,
six 10–60-minute horizons, chronological train/calibration/development partitions
and scoring observations. No outcome-based model selection, tuning or early
stopping is authorized. All effective parameters and model/data identities must
be recorded in any later independently admitted experiment.

Every input requires source/event/available-at support. Model-fitting labels and
preprocessing must be available by the declared fit cutoff. Replay decision time,
actual protocol creation/approval, wall-clock fitting and historical receipt times
are distinct. Unknown operational latency requires a reviewed assumed-latency
scenario and forbids claims of verified historical deployability.

For each model and horizon, residuals have score `s_i = abs(y_i - prediction_i)`.
Calibration requires `target_time < decision_time` and observation/residual
availability no later than decision. Equal-time and future labels are rejected;
invalid metadata is validated before eligible-record filtering.

Static and rolling unweighted calibration use
`k = ceil((n + 1) * (1 - alpha))`, without interpolation. Unsupported finite
quantiles fail explicitly. Rolling calibration applies its declared eligible
window; static calibration uses its separately declared fixed history.
Recency weights are `2 ** (-(decision_time - target_time) / half_life)` with times
in minutes, including unit test-point mass at positive infinity. Weighted history
without sufficient finite mass fails explicitly. Weighted/rolling adaptation is
a development heuristic under temporal dependence, not a coverage guarantee.

Two-sided intervals are `[max(0, prediction - q), prediction + q]` with any
predeclared floor recorded separately. Current shipped ablations use a zero floor;
zero floor-binding rates would be by configuration, not an empirical advantage.
Interval comparisons require common observations and equal nominal alpha unless
explicitly designated sensitivity analyses.

Implemented scoring includes per-horizon MAE, RMSE, bias and rapid-event errors;
empirical marginal/rapid-event coverage, interval width, chronological drift,
floor-binding and denominators. Rapid-event membership is offline scoring only.
Serial dependence and overlapping targets prevent treating every forecast as
an independent replicate. No significance or simultaneous/conditional coverage
guarantee is asserted by this release.

All tests shipped here are synthetic software checks. Complete lineage/workflow
integration requires private historical evidence; it has not been replaced by
invented provenance. No real-data experiment was run for this release.
