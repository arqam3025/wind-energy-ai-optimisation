"""Descriptive, paired development scoring after outcome availability only.

Rapid-event membership uses the realized target and its preceding ten-minute
observation. These are offline scoring data, never forecast/calibration inputs.
No statistical significance or independent-test interpretation is produced.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
import math
import re

from publication_v2.protocol import finite, horizon, timestamp


class MetricError(ValueError):
    """Missing, incomparable, duplicated, or unavailable scoring observation."""


def _time(value, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else value
        return timestamp(parsed)
    except (ValueError, TypeError, AttributeError) as error:
        raise MetricError(f"Missing/invalid offset-aware scoring timestamp: {field}") from error


def _number(row: Mapping, field: str) -> float:
    value = row.get(field)
    try:
        finite(value)
    except ValueError as error:
        raise MetricError(f"Missing/nonfinite scoring value: {field}") from error
    return float(value)


def _validated(records: Sequence[Mapping], *, intervals: bool = False) -> list[dict]:
    if not records:
        raise MetricError("No scoring records; no metrics can be claimed")
    output, seen = [], set()
    for original in records:
        if not isinstance(original, Mapping):
            raise MetricError("Scoring rows must be explicit mappings")
        row = dict(original)
        for field in ('model','origin_time','decision_time','target_time','horizon_minutes','actual_available_at',
                      'scored_at','previous_target_time','previous_actual_available_at'):
            if field not in row:
                raise MetricError(f"Missing scoring field: {field}")
        if not isinstance(row['model'],str) or not row['model']:
            raise MetricError("Nonempty model identity label required")
        try:
            horizon(row['horizon_minutes'])
        except ValueError as error:
            raise MetricError(str(error)) from error
        for field in ('origin_time','decision_time','target_time','actual_available_at','scored_at',
                      'previous_target_time','previous_actual_available_at'):
            row[field] = _time(row[field],field)
        origin, decision, target = row['origin_time'], row['decision_time'], row['target_time']
        if target != origin+timedelta(minutes=row['horizon_minutes']) or not origin <= decision < target:
            raise MetricError("Scored forecast origin/decision/target does not align")
        if row['previous_target_time'] != target-timedelta(minutes=10):
            raise MetricError("Rapid-event preceding target timestamp is misaligned")
        if not target <= row['actual_available_at'] <= row['scored_at']:
            raise MetricError("Scoring outcome was not available, or receipt precedes target")
        if not row['previous_target_time'] <= row['previous_actual_available_at'] <= row['scored_at']:
            raise MetricError("Preceding scoring outcome availability is invalid")
        for field in ('prediction_kw','actual_kw','previous_actual_kw'):
            row[field] = _number(row,field)
            if row[field] < 0:
                raise MetricError("Scoring uses declared nonnegative generation support")
        method = row.get('method') if intervals else None
        if intervals:
            if not isinstance(method,str) or not method:
                raise MetricError("Interval method label required")
            for field in ('lower_kw','upper_kw','alpha'):
                row[field] = _number(row,field)
            if not 0 <= row['lower_kw'] <= row['prediction_kw'] <= row['upper_kw'] or not 0 < row['alpha'] < 1:
                raise MetricError("Malformed two-sided nonnegative-power interval")
            if type(row.get('floor_binding')) is not bool:
                raise MetricError("Explicit boolean floor_binding is required")
            newest = _time(row.get('calibration_newest_target_time'),'calibration_newest_target_time')
            if not newest < decision:
                raise MetricError("Interval uses an equal-time/future calibration target")
            row['calibration_newest_target_time'] = newest
        key = (row['model'],method,origin,row['horizon_minutes'])
        if key in seen:
            raise MetricError("Duplicate model/method/origin/horizon scoring identity")
        seen.add(key)
        period = row.get('period_id', target.date().isoformat())
        if not isinstance(period,str) or not period:
            raise MetricError("Explicit nonempty period_id required when supplied")
        row['period_id'] = period
        output.append(row)
    return output


def _identity(row: dict) -> tuple:
    return tuple(row[field] for field in ('decision_time','target_time','actual_kw','actual_available_at',
        'scored_at','previous_target_time','previous_actual_kw','previous_actual_available_at','period_id'))


def _require_common_observations(rows: Sequence[dict], expected_models: Sequence[str]) -> None:
    if not expected_models or len(set(expected_models)) != len(expected_models):
        raise MetricError("Distinct expected model labels must be declared")
    by_model = defaultdict(dict)
    for row in rows:
        by_model[row['model']][(row['origin_time'],row['horizon_minutes'])] = _identity(row)
    if set(by_model) != set(expected_models):
        raise MetricError("Observed model set differs from the declared comparison")
    reference = by_model[expected_models[0]]
    for model in expected_models[1:]:
        if by_model[model] != reference:
            raise MetricError("Models do not share identical scoring keys/observations/timestamps")


def _require_horizon_panel(rows: Sequence[dict], expected_horizons: Sequence[int]) -> None:
    if not expected_horizons or len(set(expected_horizons))!=len(expected_horizons):
        raise MetricError("Distinct expected horizons must be declared")
    for h in expected_horizons:
        try: horizon(h)
        except ValueError as error: raise MetricError(str(error)) from error
    panels={h:{r['origin_time'] for r in rows if r['horizon_minutes']==h} for h in expected_horizons}
    if {r['horizon_minutes'] for r in rows}!=set(expected_horizons) or any(not p for p in panels.values()):
        raise MetricError("Scoring horizon set differs from the declared panel")
    reference=panels[expected_horizons[0]]
    if any(panel!=reference for panel in panels.values()):
        raise MetricError("Every horizon must use identical forecast origins")


def _error_summary(rows: Sequence[dict], rapid_threshold_kw: float) -> dict:
    errors = [r['prediction_kw']-r['actual_kw'] for r in rows]
    rapid = [r for r in rows if abs(r['actual_kw']-r['previous_actual_kw']) > rapid_threshold_kw]
    def mean_error(part, square=False):
        if not part:
            return None
        values = [(r['prediction_kw']-r['actual_kw'])**2 if square else abs(r['prediction_kw']-r['actual_kw']) for r in part]
        mean=math.fsum(values)/len(values)
        return math.sqrt(mean) if square else mean
    return {'n':len(rows),'mae_kw':mean_error(rows),'rmse_kw':mean_error(rows,True),
            'bias_forecast_minus_actual_kw':math.fsum(errors)/len(errors),
            'rapid_event_n':len(rapid),'rapid_event_mae_kw':mean_error(rapid),
            'rapid_event_rmse_kw':mean_error(rapid,True)}


def evaluate_forecasts(records: Sequence[Mapping],
                       expected_models: Sequence[str] = ('persistence','xgboost','lightgbm'),
                       rapid_threshold_kw: float = 200.001,
                       expected_horizons: Sequence[int] = (10,20,30,40,50,60)) -> dict:
    finite(rapid_threshold_kw)
    if rapid_threshold_kw < 0:
        raise MetricError("Rapid-event threshold must be nonnegative")
    rows = _validated(records)
    _require_common_observations(rows,expected_models)
    _require_horizon_panel(rows,expected_horizons)
    if 'persistence' not in expected_models:
        raise MetricError("Persistence comparison must be retained")
    groups, periods = defaultdict(list), defaultdict(list)
    for row in rows:
        groups[(row['model'],row['horizon_minutes'])].append(row)
        periods[(row['model'],row['horizon_minutes'],row['period_id'])].append(row)
    summaries = [{'model':key[0],'horizon_minutes':key[1],**_error_summary(part,rapid_threshold_kw)}
                 for key,part in sorted(groups.items())]
    reference = {r['horizon_minutes']:r for r in summaries if r['model']=='persistence'}
    for row in summaries:
        baseline = reference[row['horizon_minutes']]
        row['mae_minus_persistence_kw'] = row['mae_kw']-baseline['mae_kw']
        row['rmse_minus_persistence_kw'] = row['rmse_kw']-baseline['rmse_kw']
        row['mae_skill_vs_persistence'] = 1-row['mae_kw']/baseline['mae_kw'] if baseline['mae_kw'] else None
        row['rmse_skill_vs_persistence'] = 1-row['rmse_kw']/baseline['rmse_kw'] if baseline['rmse_kw'] else None
    drift = [{'model':k[0],'horizon_minutes':k[1],'period_id':k[2],**_error_summary(v,rapid_threshold_kw)}
             for k,v in sorted(periods.items())]
    return {'scope':'descriptive development scoring; no significance/confirmatory claim',
            'scoring_records':len(rows),'shared_origin_horizon_keys':len(rows)//len(expected_models),
            'rapid_event_definition':f'abs(actual target minus actual target-10min) > {rapid_threshold_kw} kW; offline only',
            'per_horizon':summaries,'per_period':drift}


def _coverage_summary(rows: Sequence[dict], rapid_threshold_kw: float) -> dict:
    alphas={r['alpha'] for r in rows}
    if len(alphas)!=1:
        raise MetricError("A coverage group cannot silently mix alpha levels")
    alpha=next(iter(alphas))
    rapid=[r for r in rows if abs(r['actual_kw']-r['previous_actual_kw'])>rapid_threshold_kw]
    covered=lambda r:r['lower_kw']<=r['actual_kw']<=r['upper_kw']
    coverage=sum(covered(r) for r in rows)/len(rows)
    return {'n':len(rows),'alpha':alpha,'nominal_coverage_reference':1-alpha,
            'marginal_coverage':coverage,'coverage_minus_reference_pp':100*(coverage-(1-alpha)),
            'absolute_calibration_error_pp':100*abs(coverage-(1-alpha)),
            'rapid_event_n':len(rapid),'rapid_event_coverage':sum(covered(r) for r in rapid)/len(rapid) if rapid else None,
            'mean_interval_width_kw':math.fsum(r['upper_kw']-r['lower_kw'] for r in rows)/len(rows),
            'floor_binding_rate':sum(r['floor_binding'] for r in rows)/len(rows)}


def evaluate_intervals(records: Sequence[Mapping],
                       expected_models: Sequence[str] = ('persistence','xgboost','lightgbm'),
                       expected_methods: Sequence[str] = ('static','rolling','weighted'),
                       rapid_threshold_kw: float = 200.001,
                       expected_horizons: Sequence[int] = (10,20,30,40,50,60), *,
                       sensitivity_experiment: str | None = None) -> dict:
    """Compare common-alpha intervals, or explicitly label a named sensitivity.

    Differing nominal levels change the coverage/width tradeoff. They are not a
    fair uncertainty-method comparison, even on identical scoring observations.
    A named sensitivity remains descriptive and retains each group's alpha.
    """
    finite(rapid_threshold_kw)
    if rapid_threshold_kw<0 or not expected_methods or len(set(expected_methods))!=len(expected_methods):
        raise MetricError("Distinct interval methods and nonnegative rapid threshold required")
    if sensitivity_experiment is not None and (
            not isinstance(sensitivity_experiment, str) or
            re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', sensitivity_experiment) is None):
        raise MetricError("Sensitivity experiment requires an explicit name (1-128 letters, digits, _, . or -)")
    rows=_validated(records,intervals=True)
    alpha_levels = sorted({row['alpha'] for row in rows})
    if len(alpha_levels) != 1 and sensitivity_experiment is None:
        raise MetricError("Interval method/model comparisons require equal nominal alpha; declare a named sensitivity experiment")
    if {r['method'] for r in rows}!=set(expected_methods):
        raise MetricError("Observed uncertainty methods differ from the declared comparison")
    by_method={method:[r for r in rows if r['method']==method] for method in expected_methods}
    for part in by_method.values():
        _require_common_observations(part,expected_models)
        _require_horizon_panel(part,expected_horizons)
    method_reference={(r['model'],r['origin_time'],r['horizon_minutes']):(_identity(r),r['prediction_kw'])
                      for r in by_method[expected_methods[0]]}
    for part in list(by_method.values())[1:]:
        identity={(r['model'],r['origin_time'],r['horizon_minutes']):(_identity(r),r['prediction_kw']) for r in part}
        if identity!=method_reference:
            raise MetricError("Uncertainty methods must score identical point forecasts and observations")
    groups,periods=defaultdict(list),defaultdict(list)
    for row in rows:
        key=(row['model'],row['method'],row['horizon_minutes'])
        groups[key].append(row);periods[(*key,row['period_id'])].append(row)
    per_horizon=[{'model':k[0],'method':k[1],'horizon_minutes':k[2],**_coverage_summary(v,rapid_threshold_kw)}
                 for k,v in sorted(groups.items())]
    per_period=[{'model':k[0],'method':k[1],'horizon_minutes':k[2],'period_id':k[3],**_coverage_summary(v,rapid_threshold_kw)}
                for k,v in sorted(periods.items())]
    scope = ('descriptive development nominal-alpha sensitivity experiment; not a common-alpha method comparison; '
             'no dependent-time coverage guarantee' if sensitivity_experiment is not None else
             'descriptive development uncertainty; no dependent-time coverage guarantee')
    return {'scope':scope,
            'comparison_design':('nominal_alpha_sensitivity_experiment' if sensitivity_experiment is not None else
                                 'common_nominal_alpha_method_comparison'),
            'sensitivity_experiment':sensitivity_experiment,'nominal_alpha_levels':alpha_levels,
            'scoring_records':len(rows),'per_horizon':per_horizon,'per_period':per_period,
            'drift_definition':'coverage/calibration error by predeclared period_id, default UTC target calendar day; no fitted change point'}
