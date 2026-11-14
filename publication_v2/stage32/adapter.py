"""Fail-closed synthetic bridge from Stage 2 numerical arrays to Stage 3.1 MPC.

This authenticates consistency with trusted *synthetic fixture* registrations,
not a real dataset, fitted model, operational clock, or scientific provenance.
The underlying Stage 2 ndarray has no such metadata; none is inferred here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import copy
import hashlib
import json
import math
from numbers import Real
import re

from publication_v2.protocol import HORIZONS, Residual, validate_residual
from publication_v2.stage2.conformal import CalibrationConfig, calibrate
from publication_v2.stage31.forecast import ForecastBundle

SCHEMA = 'stage32.synthetic_forecast.v1'
TARGET_SEMANTICS = 'mean_power_over_interval_ending_at_target'
CUTOFF_SEMANTICS = 'SIMULATED_RULE_SPECIFICATION_CUTOFF_NOT_TRAINING'
IDENTITY_KIND = 'SYNTHETIC_RULE_DESCRIPTOR'
MODEL_KEYS = set('id version identity_kind rule parameters required_inputs access_mode source_id cohort_id scenario_sha256 units quantity target_semantics available_at rule_specification_cutoff fitting_status actual_fitting_cutoff residual_cutoff_semantics'.split())
MODEL_PACKET_KEYS = set('id version descriptor_sha256 identity_kind available_at rule_specification_cutoff fitting_status actual_fitting_cutoff residual_cutoff_semantics'.split())
COHORT_KEYS = set('cohort_id source_id scenario_sha256 study_role admission data_kind units quantity target_semantics'.split())
CONFIG_KEYS = set('config_id version method parameters source_id cohort_id model_id model_version model_descriptor_sha256 available_at'.split())
ARTIFACT_KEYS = set('config_id version method generated_at available_at result residuals source_id cohort_id model_id model_version model_descriptor_sha256'.split())
PACKET_KEYS = set('schema packet_id study_role source_id cohort_id scenario_sha256 admission data_kind units quantity target_semantics clock_assumption forecast_origin issue_time generated_at available_at model feature_inputs horizons alpha'.split())
HORIZON_KEYS = set('horizon_minutes target_time point_kw lower_kw upper_kw calibration'.split())
INPUT_KEYS = set('name value source_times source_available_ats available_at'.split())
RESIDUAL_KEYS = set(Residual.__dataclass_fields__)
RESIDUAL_TIMES = ('origin_time', 'issued_at', 'target_time', 'observation_available_at',
                  'residual_available_at', 'model_latest_training_target',
                  'model_available_at', 'grid_anchor')


class AdapterError(ValueError):
    def __init__(self, code, detail):
        super().__init__(detail)
        self.code = code


def canonical_sha256(value):
    """Hash portable JSON bytes; a digest is not independent provenance."""
    try:
        body = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                          allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, OverflowError) as error:
        raise AdapterError('INVALID_JSON', 'Metadata must be finite, serializable JSON') from error
    return hashlib.sha256(body).hexdigest()


def _keys(value, expected, name):
    if not isinstance(value, dict) or set(value) != expected:
        missing = sorted(expected - set(value)) if isinstance(value, dict) else sorted(expected)
        unknown = sorted(set(value) - expected) if isinstance(value, dict) else []
        raise AdapterError('METADATA_SCHEMA', f'{name}: missing={missing}; unsupported={unknown}')


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise AdapterError('METADATA_VALUE', f'{name} requires explicit nonempty text')
    return value


def _sha(value, name):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise AdapterError('IDENTITY_INVALID', f'{name} requires lower-case SHA256')
    return value


def _time(value, name):
    if not isinstance(value, str):
        raise AdapterError('TIMESTAMP_INVALID', f'{name} requires an explicit ISO offset-aware string')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError('naive')
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError) as error:
        raise AdapterError('TIMESTAMP_INVALID', f'{name} has no valid explicit timezone') from error


def _decision_time(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise AdapterError('TIMESTAMP_INVALID', 'decision_time requires an aware datetime')
    return value.astimezone(timezone.utc)


def _number(value, name):
    # Conversion is deliberate at this adapter boundary. Stage 3.1 itself stays unchanged.
    if isinstance(value, bool) or not isinstance(value, Real):
        raise AdapterError('NUMERIC_INVALID', f'{name} must be a finite real number')
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise AdapterError('NUMERIC_INVALID', f'{name} is not representable') from error
    if not math.isfinite(result):
        raise AdapterError('NUMERIC_INVALID', f'{name} must be finite')
    return result


def _same(actual, expected, name, code='IDENTITY_MISMATCH'):
    if actual != expected:
        raise AdapterError(code, f'{name} does not match the trusted synthetic fixture registration')


def _synthetic(value):
    for key, expected in (('study_role', 'SYNTHETIC_DEVELOPMENT'),
                          ('admission', 'SYNTHETIC_ONLY'), ('data_kind', 'SYNTHETIC'),
                          ('units', 'kW'), ('quantity', 'measured_wind_generation'),
                          ('target_semantics', TARGET_SEMANTICS)):
        _same(value[key], expected, key, 'SOURCE_OR_SEMANTICS_REJECTED')


class SyntheticRegistry:
    """Defensive snapshot of trusted synthetic fixture expectations.

    The caller must construct this independently of a received/fault-mutated
    packet. Registering a caller's asserted SHA would provide no trust boundary.
    This registry cannot admit any real dataset or establish non-exposure.
    """
    def __init__(self, models, cohorts, configs, artifacts):
        for name, value in (('models', models), ('cohorts', cohorts),
                            ('configs', configs), ('artifacts', artifacts)):
            if not isinstance(value, dict):
                raise AdapterError('REGISTRY_INVALID', f'{name} must be a dictionary')
            canonical_sha256(value)
            setattr(self, '_' + name, copy.deepcopy(value))
        for key, value in self._artifacts.items():
            _sha(key, 'artifact registration')
            _same(canonical_sha256(value), key, 'artifact registration', 'REGISTRY_INVALID')

    def resolve(self, category, identity):
        if category not in ('models', 'cohorts', 'configs', 'artifacts'):
            raise AdapterError('REGISTRY_INVALID', 'Unknown registry category')
        try:
            return copy.deepcopy(getattr(self, '_' + category)[identity])
        except (KeyError, TypeError) as error:
            raise AdapterError('UNREGISTERED_IDENTITY', f'Unknown trusted synthetic {category} identity') from error

    def inventory(self):
        return {name: sorted(getattr(self, '_' + name))
                for name in ('models', 'cohorts', 'configs', 'artifacts')}


@dataclass(frozen=True)
class AdapterPolicy:
    max_calibration_age_minutes: float = 1440.0
    max_artifact_age_minutes: float = 60.0
    allow_preannounced_forcing: bool = True

    def __post_init__(self):
        for name in ('max_calibration_age_minutes', 'max_artifact_age_minutes'):
            if _number(getattr(self, name), name) <= 0:
                raise AdapterError('POLICY_INVALID', f'{name} must be positive')
        if type(self.allow_preannounced_forcing) is not bool:
            raise AdapterError('POLICY_INVALID', 'allow_preannounced_forcing must be boolean')


@dataclass(frozen=True)
class Adaptation:
    accepted: bool
    bundle: ForecastBundle | None
    rejection_code: str | None
    detail: str
    audit: dict


def _model(document, registry, decision, policy):
    model = document['model']
    _keys(model, MODEL_PACKET_KEYS, 'model')
    model_id = _text(model['id'], 'model.id')
    descriptor = registry.resolve('models', model_id)
    _keys(descriptor, MODEL_KEYS, 'registered model')
    _same(descriptor['id'], model_id, 'model id')
    _same(canonical_sha256(descriptor), _sha(model['descriptor_sha256'], 'descriptor_sha256'), 'model descriptor SHA')
    for key in MODEL_PACKET_KEYS - {'descriptor_sha256'}:
        _same(model[key], descriptor[key], f'model.{key}')
    for key in ('source_id', 'cohort_id', 'scenario_sha256', 'units', 'quantity', 'target_semantics'):
        _same(descriptor[key], document[key], f'model.{key}')
    for key in ('id', 'version', 'rule'):
        _text(descriptor[key], f'model.{key}')
    _same(descriptor['identity_kind'], IDENTITY_KIND, 'identity kind')
    _same(descriptor['fitting_status'], 'NOT_FITTED_SYNTHETIC_RULE', 'fitting status')
    _same(descriptor['actual_fitting_cutoff'], None, 'actual fitting cutoff')
    _same(descriptor['residual_cutoff_semantics'], CUTOFF_SEMANTICS, 'residual cutoff semantics')
    if not isinstance(descriptor['parameters'], dict):
        raise AdapterError('METADATA_SCHEMA', 'Synthetic rule parameters require an explicit mapping')
    cutoff = _time(descriptor['rule_specification_cutoff'], 'rule_specification_cutoff')
    available = _time(descriptor['available_at'], 'model.available_at')
    if not cutoff <= available <= decision or not cutoff < decision:
        raise AdapterError('MODEL_UNAVAILABLE', 'Rule cutoff/availability must precede or reach decision causally')
    mode = descriptor['access_mode']
    if mode not in ('PAST_RELEASED_OBSERVATIONS_ONLY', 'PREANNOUNCED_DETERMINISTIC_FORCING'):
        raise AdapterError('INPUT_ACCESS_REJECTED', 'Unsupported synthetic rule access mode')
    if mode == 'PREANNOUNCED_DETERMINISTIC_FORCING' and not policy.allow_preannounced_forcing:
        raise AdapterError('INPUT_ACCESS_REJECTED', 'Privileged known-forcing benchmark disabled by policy')
    required = descriptor['required_inputs']
    if (not isinstance(required, list) or len(set(required)) != len(required)
            or any(not isinstance(name, str) or not name for name in required)):
        raise AdapterError('METADATA_SCHEMA', 'An explicit unique required-input list is mandatory')
    if mode == 'PAST_RELEASED_OBSERVATIONS_ONLY' and not required:
        raise AdapterError('FEATURE_SUPPORT', 'Past-only synthetic rules require explicit input support')
    if mode == 'PREANNOUNCED_DETERMINISTIC_FORCING' and not descriptor['parameters']:
        raise AdapterError('FEATURE_SUPPORT', 'Preannounced forcing requires an explicit registered recipe')
    inputs = document['feature_inputs']
    if not isinstance(inputs, list) or len(inputs) != len(required):
        raise AdapterError('FEATURE_SUPPORT', 'Every declared synthetic rule input is required')
    names = []
    for feature in inputs:
        _keys(feature, INPUT_KEYS, 'feature_inputs')
        names.append(_text(feature['name'], 'feature name'))
        _number(feature['value'], 'feature value')
        available = _time(feature['available_at'], 'feature available_at')
        events, receipts = feature['source_times'], feature['source_available_ats']
        if not isinstance(events, list) or not events or not isinstance(receipts, list) or len(events) != len(receipts):
            raise AdapterError('FEATURE_SUPPORT', 'Feature support and receipts must be explicit paired lists')
        events = [_time(t, 'feature source_time') for t in events]
        receipts = [_time(t, 'feature source_available_at') for t in receipts]
        if len(set(events)) != len(events):
            raise AdapterError('FEATURE_SUPPORT', 'Duplicate feature support is not repaired')
        if available > decision or any(not event <= receipt <= available for event, receipt in zip(events, receipts)):
            raise AdapterError('FEATURE_UNAVAILABLE', 'Future or unavailable feature input')
        if mode == 'PREANNOUNCED_DETERMINISTIC_FORCING' and (available > cutoff or max(events) > cutoff):
            raise AdapterError('FEATURE_UNAVAILABLE', 'Known forcing must have been preannounced by rule specification')
    if len(set(names)) != len(names) or set(names) != set(required):
        raise AdapterError('FEATURE_SUPPORT', 'Feature names differ from the registered input contract')
    return descriptor, cutoff


def _calibration(raw, document, model, cutoff, horizon, point, issue, registry, alpha, policy):
    _keys(raw, ARTIFACT_KEYS | {'artifact_sha256'}, 'calibration')
    payload = {key: value for key, value in raw.items() if key != 'artifact_sha256'}
    artifact_sha = _sha(raw['artifact_sha256'], 'calibration artifact_sha256')
    _same(canonical_sha256(payload), artifact_sha, 'calibration artifact SHA', 'CALIBRATION_IDENTITY')
    _same(canonical_sha256(payload), canonical_sha256(registry.resolve('artifacts', artifact_sha)), 'trusted calibration artifact', 'CALIBRATION_IDENTITY')
    config = registry.resolve('configs', payload['config_id'])
    _keys(config, CONFIG_KEYS, 'registered calibration config')
    for key in ('config_id', 'version', 'method', 'source_id', 'cohort_id',
                'model_id', 'model_version', 'model_descriptor_sha256'):
        _same(payload[key], config[key], f'calibration.{key}', 'CALIBRATION_IDENTITY')
    for key in ('source_id', 'cohort_id'):
        _same(payload[key], document[key], f'calibration.{key}', 'CALIBRATION_IDENTITY')
    _same(payload['model_id'], model['id'], 'calibration model id', 'CALIBRATION_IDENTITY')
    _same(payload['model_version'], model['version'], 'calibration model version', 'CALIBRATION_IDENTITY')
    _same(payload['model_descriptor_sha256'], document['model']['descriptor_sha256'],
          'calibration model descriptor SHA', 'CALIBRATION_IDENTITY')
    if _time(config['available_at'], 'calibration config available_at') > issue:
        raise AdapterError('CALIBRATION_UNAVAILABLE', 'Calibration config was unavailable at issuance')
    generated = _time(payload['generated_at'], 'calibration generated_at')
    available = _time(payload['available_at'], 'calibration available_at')
    if not generated <= available <= issue:
        raise AdapterError('CALIBRATION_UNAVAILABLE', 'Calibration artifact clocks are unavailable or inverted')
    if (issue - generated).total_seconds() > policy.max_artifact_age_minutes * 60:
        raise AdapterError('CALIBRATION_STALE', 'Calibration artifact exceeds declared maximum age')
    parameters = config['parameters']
    if not isinstance(parameters, dict) or set(parameters) != set(CalibrationConfig.__dataclass_fields__):
        raise AdapterError('CALIBRATION_SCHEMA', 'Complete explicit native calibration parameters required')
    native_config = CalibrationConfig(**parameters)
    _same(native_config.alpha, alpha, 'nominal alpha', 'UNEQUAL_ALPHA')
    result = payload['result']
    if not isinstance(result, dict) or 'decision_time' not in result:
        raise AdapterError('CALIBRATION_SCHEMA', 'Native CalibrationResult.as_dict() is required')
    information_cutoff = _time(result['decision_time'], 'calibration decision_time')
    if information_cutoff > generated:
        raise AdapterError('CALIBRATION_UNAVAILABLE', 'Calibration result generated before its information cutoff')
    records_raw = payload['residuals']
    if not isinstance(records_raw, list) or not records_raw:
        raise AdapterError('CALIBRATION_SCHEMA', 'Explicit nonempty selected-candidate residual ledger required')
    records = []
    for raw_record in records_raw:
        _keys(raw_record, RESIDUAL_KEYS, 'calibration residual')
        record_values = dict(raw_record)
        for key in RESIDUAL_TIMES:
            record_values[key] = _time(raw_record[key], f'residual.{key}')
        for key in ('prediction_kw', 'observed_kw'):
            record_values[key] = _number(raw_record[key], f'residual.{key}')
        record = Residual(**record_values)
        # Validate every supplied candidate, before any model/horizon eligibility filtering.
        validate_residual(record, information_cutoff)
        if record.target_time >= issue or record.residual_available_at > generated:
            raise AdapterError('CALIBRATION_LEAKAGE', 'Calibration target or availability reaches issuance')
        _same(record.model_sha256, document['model']['descriptor_sha256'], 'residual model SHA', 'CALIBRATION_IDENTITY')
        _same(record.horizon_minutes, horizon, 'residual horizon', 'CALIBRATION_IDENTITY')
        _same(record.model_latest_training_target, cutoff, 'simulated rule cutoff', 'CALIBRATION_IDENTITY')
        _same(record.model_available_at, _time(model['available_at'], 'rule available_at'),
              'residual rule availability', 'CALIBRATION_IDENTITY')
        records.append(record)
    recomputed = calibrate(records, information_cutoff, horizon, payload['method'],
                           document['model']['descriptor_sha256'], native_config)
    _same(canonical_sha256(recomputed.as_dict()), canonical_sha256(result),
          'native calibration result replay', 'CALIBRATION_RESULT_MISMATCH')
    if not recomputed.newest_target_time < issue:
        raise AdapterError('CALIBRATION_LEAKAGE', 'Selected calibration target must strictly precede issue')
    if (issue - recomputed.newest_target_time).total_seconds() > policy.max_calibration_age_minutes * 60:
        raise AdapterError('CALIBRATION_STALE', 'Selected calibration history exceeds declared maximum age')
    lower, upper = recomputed.interval(point)
    summary = dict(horizon_minutes=horizon, artifact_sha256=artifact_sha,
                   config_id=payload['config_id'], config_version=payload['version'],
                   method=payload['method'], alpha=alpha,
                   selected_count=recomputed.selected_count,
                   newest_target_time=recomputed.newest_target_time.isoformat(),
                   artifact_available_at=available.isoformat(),
                   residual_ledger_sha256=canonical_sha256(records_raw),
                   residual_cutoff_semantics=CUTOFF_SEMANTICS)
    return lower, upper, recomputed.newest_target_time, available, summary


def _adapt(document, decision_time, registry, policy):
    _keys(document, PACKET_KEYS, 'packet')
    _same(document['schema'], SCHEMA, 'packet schema', 'SCHEMA_UNSUPPORTED')
    _synthetic(document)
    for key in ('packet_id', 'source_id', 'cohort_id'):
        _text(document[key], key)
    _sha(document['scenario_sha256'], 'scenario_sha256')
    decision = _decision_time(decision_time)
    for name in ('forecast_origin', 'issue_time', 'generated_at', 'available_at'):
        value = _time(document[name], name)
        if value != decision:
            raise AdapterError('FORECAST_CLOCK_ALIGNMENT', 'Full six-step panel requires explicit zero-latency origin/issue/generation/availability=decision')
    _same(document['clock_assumption'], 'SYNTHETIC_ZERO_LATENCY', 'clock assumption', 'CLOCK_ASSUMPTION')
    cohort = registry.resolve('cohorts', document['cohort_id'])
    _keys(cohort, COHORT_KEYS, 'registered cohort')
    for key in COHORT_KEYS:
        _same(document[key], cohort[key], f'cohort.{key}')
    _synthetic(cohort)
    model, cutoff = _model(document, registry, decision, policy)
    alpha = _number(document['alpha'], 'alpha')
    if not 0 < alpha < 1:
        raise AdapterError('ALPHA_INVALID', 'Miscoverage alpha must lie strictly between zero and one')
    rows = document['horizons']
    if not isinstance(rows, list) or len(rows) != len(HORIZONS):
        raise AdapterError('HORIZON_MAPPING', 'Exactly six ordered forecast horizon records required')
    points, lowers, uppers, targets, newest, available_ats, summaries = [], [], [], [], [], [], []
    for expected, row in zip(HORIZONS, rows):
        _keys(row, HORIZON_KEYS, 'horizon')
        if type(row['horizon_minutes']) is not int or row['horizon_minutes'] != expected:
            raise AdapterError('HORIZON_MAPPING', 'Horizon order must be exactly 10,20,30,40,50,60 minutes')
        target = _time(row['target_time'], 'target_time')
        if target != decision + timedelta(minutes=expected):
            raise AdapterError('HORIZON_MAPPING', 'Target is not the corresponding future interval end')
        point, lower, upper = (_number(row[key], key) for key in ('point_kw', 'lower_kw', 'upper_kw'))
        if not 0 <= lower <= point <= upper:
            raise AdapterError('INTERVAL_INVALID', 'Require 0 <= lower <= point <= upper')
        computed_l, computed_u, last, ready, summary = _calibration(
            row['calibration'], document, model, cutoff, expected, point, decision, registry, alpha, policy)
        if lower != computed_l or upper != computed_u:
            raise AdapterError('INTERVAL_CALIBRATION_MISMATCH', 'Bounds differ from the verified native calibration result')
        points.append(point); lowers.append(lower); uppers.append(upper); targets.append(target)
        newest.append(last); available_ats.append(ready); summaries.append(summary)
    audit = dict(schema=SCHEMA, packet_id=document['packet_id'], source_id=document['source_id'],
                 cohort_id=document['cohort_id'], scenario_sha256=document['scenario_sha256'],
                 study_role=document['study_role'], admission=document['admission'],
                 model_id=model['id'], model_version=model['version'],
                 model_descriptor_sha256=document['model']['descriptor_sha256'],
                 identity_kind=IDENTITY_KIND, fitting_status=model['fitting_status'],
                 residual_cutoff_semantics=CUTOFF_SEMANTICS, access_mode=model['access_mode'],
                 clock_assumption=document['clock_assumption'], units='kW',
                 quantity='measured_wind_generation', target_semantics=TARGET_SEMANTICS,
                 alpha=alpha, coverage_interpretation='marginal descriptive; not joint trajectory coverage',
                 calibrations=summaries)
    provenance = json.dumps(audit, sort_keys=True, separators=(',', ':'), allow_nan=False)
    bundle = ForecastBundle(decision, tuple(points), tuple(lowers), tuple(uppers), alpha,
                            provenance, decision, tuple(targets),
                            _time(model['available_at'], 'model.available_at'),
                            tuple(newest), tuple(available_ats), 'CONFORMAL_MARGINAL')
    bundle.validate(decision)
    return Adaptation(True, bundle, None, 'Accepted trusted synthetic fixture metadata; no real-data admission', audit)


def adapt_forecast(document, decision_time, registry, *, policy=None):
    """Validate a packet or return a structured rejection; never fabricate a fallback forecast."""
    try:
        if not isinstance(registry, SyntheticRegistry):
            raise AdapterError('REGISTRY_INVALID', 'An explicit trusted SyntheticRegistry is mandatory')
        actual_policy = AdapterPolicy() if policy is None else policy
        if not isinstance(actual_policy, AdapterPolicy):
            raise AdapterError('POLICY_INVALID', 'AdapterPolicy required')
        return _adapt(document, decision_time, registry, actual_policy)
    except AdapterError as error:
        return Adaptation(False, None, error.code, str(error), {})
    except (TypeError, ValueError, KeyError, OverflowError) as error:
        return Adaptation(False, None, 'CALIBRATION_OR_METADATA_INVALID', str(error), {})


def adapt_stage2_points(points, *, metadata, decision_time, registry, policy=None):
    """Bridge a six-value Stage 2 row only with complete independently supplied metadata.

    metadata is the full envelope except each horizon must OMIT point_kw. Native
    ndarray scalars are explicitly normalized here, not in the unchanged MPC.
    No model is fitted or loaded. Bounds, identities and all clocks remain mandatory.
    """
    try:
        if hasattr(points, 'tolist'):
            points = points.tolist()
        if not isinstance(points, (list, tuple)) or len(points) != 6:
            raise AdapterError('POINT_SHAPE', 'Exactly one six-horizon prediction row is required')
        document = copy.deepcopy(metadata)
        if not isinstance(document, dict) or not isinstance(document.get('horizons'), list) or len(document['horizons']) != 6:
            raise AdapterError('METADATA_SCHEMA', 'Six complete horizon metadata records required')
        for index, row in enumerate(document['horizons']):
            _keys(row, HORIZON_KEYS - {'point_kw'}, 'point-row horizon metadata')
            row['point_kw'] = _number(points[index], 'Stage 2 prediction')
        return adapt_forecast(document, decision_time, registry, policy=policy)
    except AdapterError as error:
        return Adaptation(False, None, error.code, str(error), {})
    except (TypeError, ValueError, OverflowError) as error:
        return Adaptation(False, None, 'CALIBRATION_OR_METADATA_INVALID', str(error), {})
