"""Stage 2.3 study clocks and reviewed retrospective replay admission.

Evidence hashes bind records; they do not authenticate their authors or dates.
Real admission still requires the separately trusted lineage review registry.
This module supplies no confirmation execution path and never repairs clocks.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math

from publication_v2.integrity import digest, inside
from publication_v2.protocol import timestamp

RETROSPECTIVE_DEVELOPMENT = 'RETROSPECTIVE_DEVELOPMENT'
PROSPECTIVE_CONFIRMATION = 'PROSPECTIVE_CONFIRMATION'
STUDY_ROLES = (RETROSPECTIVE_DEVELOPMENT, PROSPECTIVE_CONFIRMATION)
CALIBRATION_RULE = 'target_time < decision_time'
AVAILABILITY_RULE = 'observation_available_at <= decision_time and residual_available_at <= decision_time'


class StudyError(ValueError):
    """Missing, inconsistent or unsupported scientific study metadata."""


def _time(value):
    if not isinstance(value, str):
        raise StudyError('Study timestamps must be explicit offset-aware strings')
    try:
        return timestamp(datetime.fromisoformat(value))
    except (TypeError, ValueError) as error:
        raise StudyError(f'Invalid study timestamp: {value!r}') from error


def _keys(value, names, label):
    if not isinstance(value, dict) or set(value) != set(names):
        raise StudyError(f'Unsupported or missing {label} metadata')


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or value.strip() != value:
        raise StudyError(f'Explicit {label} is required')


def _artifact(root, reference, hashes, *, json_record=True):
    _keys(reference, ('path', 'sha256'), 'study evidence reference')
    path = inside(root, reference['path'])
    if digest(path) != reference['sha256']:
        raise StudyError('Study evidence hash mismatch')
    hashes[reference['path']] = reference['sha256']
    if not json_record:
        return None
    try:
        result = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise StudyError('Malformed study evidence JSON') from error
    if not isinstance(result, dict):
        raise StudyError('Study evidence must be a JSON object')
    return result


def _seconds(value):
    if type(value) not in (int, float) or not 0 <= value <= 86400 or not math.isfinite(value):
        raise StudyError('Assumed latency must be finite nonnegative seconds, at most one day')
    return timedelta(seconds=value)


def _validate_availability(document, availability, measurements, root, hashes):
    mode = availability.get('mode') if isinstance(availability, dict) else None
    names = {'mode', 'operational_availability_established', 'historical_deployability_verified', 'evidence'}
    if mode == 'ASSUMED_LATENCY':
        names.add('scenario')
    _keys(availability, names, 'availability')
    if mode not in ('VERIFIED_OPERATIONAL', 'ASSUMED_LATENCY'):
        raise StudyError('Unsupported availability mode')
    if availability['historical_deployability_verified'] is not False:
        raise StudyError('This retrospective pathway cannot claim verified historical deployability')
    established = mode == 'VERIFIED_OPERATIONAL'
    if availability['operational_availability_established'] is not established:
        raise StudyError('Assumed latency cannot establish operational availability')
    _artifact(root, availability['evidence'], hashes, json_record=False)
    if established:
        return {'mode': mode, 'interpretation': 'REVIEWED_AVAILABILITY_RETROSPECTIVE_REPLAY',
                'historical_deployability_verified': False}
    scenario = availability['scenario']
    _keys(scenario, ('scenario_id', 'units', 'measurement_latency_seconds',
                    'feature_processing_latency_seconds', 'residual_processing_latency_seconds', 'rationale'),
          'assumed-latency scenario')
    _text(scenario['scenario_id'], 'assumed-latency scenario identity')
    _text(scenario['rationale'], 'assumed-latency rationale')
    if scenario['units'] != 'seconds':
        raise StudyError('Assumed-latency units must be seconds')
    measurement_delay = _seconds(scenario['measurement_latency_seconds'])
    feature_delay = _seconds(scenario['feature_processing_latency_seconds'])
    residual_delay = _seconds(scenario['residual_processing_latency_seconds'])
    # Check every record. The scenario describes the supplied ledger; it never
    # overwrites a receipt, shifts an origin, or makes an unavailable label usable.
    for event, measurement in measurements.items():
        if measurement['available'] != event + measurement_delay:
            raise StudyError('Measurement availability differs from the assumed-latency scenario')
    for records in document['partitions'].values():
        for row in records:
            for feature in row['features']:
                receipts = [_time(t) for t in feature['source_available_ats']]
                if not receipts or _time(feature['available_at']) != max(receipts) + feature_delay:
                    raise StudyError('Feature availability differs from the assumed-latency scenario')
            for target in row['targets']:
                ready = max(_time(target['available_at']), _time(row['issued_at'])) + residual_delay
                if _time(target['residual_available_at']) != ready:
                    raise StudyError('Residual availability differs from the assumed-latency scenario')
    return {'mode': mode, 'interpretation': 'ASSUMED_LATENCY_REPLAY', 'scenario': scenario,
            'operational_availability_established': False, 'historical_deployability_verified': False}


def validate_study_contract(document, cohort, root, kind, measurements, hashes):
    """Validate actual clocks separately from event/replay clocks.

    Old synthetic fixtures retain their old boundary check, never real-data
    authorization. A real study always needs the explicit versioned contract.
    The trusted review is checked separately in ``lineage.verify_lineage``.
    """
    reference = document.get('study_contract')
    if reference is None:
        if kind != 'SYNTHETIC_FIXTURE' or 'study_role' in document:
            raise StudyError('An explicit reviewed study contract is required for real development')
        return None
    contract = _artifact(root, reference, hashes)
    _keys(contract, ('schema_version', 'study_role', 'analysis', 'data_access', 'availability', 'replay'), 'study contract')
    if contract['schema_version'] != 'publication_v2.stage23.study.v1':
        raise StudyError('Unsupported study-contract schema')
    role = contract['study_role']
    if role not in STUDY_ROLES:
        raise StudyError('Explicit retrospective or prospective study role is required')
    if document.get('study_role', role) != role:
        raise StudyError('Conflicting study-role labels')
    if role == PROSPECTIVE_CONFIRMATION:
        raise StudyError('BLOCKED_CONFIRMATORY_TEST: prospective confirmation requires a separate independently reviewed custody/prespecification pathway')
    if document.get('contains_confirmation_data') is not False:
        raise StudyError('Retrospective data cannot acquire confirmation eligibility')

    analysis = contract['analysis']
    _keys(analysis, ('protocol_created_at', 'protocol_approved_at', 'planned_execution_not_before',
                     'reviewer', 'clock_evidence'), 'analysis clock')
    created, approved, execution_floor = map(_time, (analysis['protocol_created_at'],
        analysis['protocol_approved_at'], analysis['planned_execution_not_before']))
    now = datetime.now(timezone.utc)
    if not created <= approved <= execution_floor <= now:
        raise StudyError('Actual protocol creation/approval must precede new execution; future or reversed clocks rejected')
    _text(analysis['reviewer'], 'analysis reviewer')
    clock = _artifact(root, analysis['clock_evidence'], hashes)
    _keys(clock, ('schema_version', 'protocol_created_at', 'protocol_approved_at', 'reviewer', 'recorded_at'), 'analysis clock evidence')
    if (clock['schema_version'] != 'publication_v2.stage23.analysis-clock.v1' or
            any(clock[k] != analysis[k] for k in ('protocol_created_at', 'protocol_approved_at', 'reviewer'))):
        raise StudyError('Analysis clock evidence mismatch; backdating a declaration is not permitted')
    if not approved <= _time(clock['recorded_at']) <= execution_floor:
        raise StudyError('Analysis clock evidence was not recorded before new execution')
    if _time(cohort['declared_at']) != created:
        raise StudyError('Cohort declaration must equal actual protocol creation; backdating is not permitted')

    access = contract['data_access']
    access_names = ('acquired_at', 'first_access_at', 'exposure_status', 'prior_study_roles', 'custodian', 'recorded_at')
    _keys(access, (*access_names, 'evidence'), 'actual data access')
    access_record = _artifact(root, access['evidence'], hashes)
    _keys(access_record, ('schema_version', *access_names), 'access evidence')
    if (access_record['schema_version'] != 'publication_v2.stage23.access-record.v1' or
            any(access_record[k] != access[k] for k in access_names)):
        raise StudyError('Actual data access/exposure evidence mismatch')
    acquired, first_access, recorded = map(_time, (access['acquired_at'], access['first_access_at'], access['recorded_at']))
    if not acquired <= first_access <= recorded <= approved:
        raise StudyError('Invalid actual acquisition/access/review chronology')
    if access['exposure_status'] not in ('PREVIOUSLY_INSPECTED', 'EXPOSURE_UNKNOWN'):
        raise StudyError('Retrospective use cannot assert untouched confirmation eligibility')
    previous_roles = access['prior_study_roles']
    if (not isinstance(previous_roles, list) or any(r not in STUDY_ROLES for r in previous_roles)
            or len(previous_roles) != len(set(previous_roles))):
        raise StudyError('Unsupported prior study-role/exposure metadata')
    _text(access['custodian'], 'access-record custodian')

    replay = contract['replay']
    _keys(replay, ('model_fitting_cutoff', 'model_available_at', 'static_calibration_target_cutoff',
                   'calibration_rule', 'availability_rule'), 'replay cutoff')
    if replay['calibration_rule'] != CALIBRATION_RULE or replay['availability_rule'] != AVAILABILITY_RULE:
        raise StudyError('Replay calibration must retain strict target and availability rules')
    fit, model_available, calibration_cutoff = map(_time, (replay['model_fitting_cutoff'],
        replay['model_available_at'], replay['static_calibration_target_cutoff']))
    # The unchanged runner uses dataset.fit_time as model availability. Reject
    # a separate unsupported value rather than silently ignoring it.
    if fit != _time(document['fit_time']) or model_available != fit:
        raise StudyError('Model fitting cutoff/availability differs from the supported replay ledger')
    partitions = document['partitions']
    if set(partitions) != {'train', 'calibration', 'development'} or any(not rows for rows in partitions.values()):
        raise StudyError('Replay requires nonempty train/calibration/development cohorts')
    train_targets = [target for row in partitions['train'] for target in row['targets']]
    if any(max(_time(t['target_time']), _time(t['available_at']), _time(t['residual_available_at'])) > fit for t in train_targets):
        raise StudyError('Training labels are unavailable at the replay model fitting cutoff')
    calibration_targets = [target for row in partitions['calibration'] for target in row['targets']]
    first_calibration = min(_time(row['origin_time']) for row in partitions['calibration'])
    first_development = min(_time(row['decision_time']) for row in partitions['development'])
    if not fit <= first_calibration:
        raise StudyError('Replay model fitting cutoff follows calibration issuance')
    if not max(_time(t['target_time']) for t in calibration_targets) <= calibration_cutoff < first_development:
        raise StudyError('Static calibration target cutoff must strictly precede the first development decision')
    if any(max(_time(t['available_at']), _time(t['residual_available_at'])) > first_development for t in calibration_targets):
        raise StudyError('Static calibration information is unavailable at the first development decision')
    if max(measurements) >= execution_floor:
        raise StudyError('Retrospective replay observations must precede actual new execution')
    availability = _validate_availability(document, contract['availability'], measurements, root, hashes)
    if kind == 'REAL_DEVELOPMENT':
        value = document['provenance']['availability']['value']
        if not isinstance(value, dict) or value.get('mode') != availability['mode']:
            raise StudyError('Real provenance must explicitly identify verified versus assumed availability')
    decisions = [_time(row['decision_time']) for rows in partitions.values() for row in rows]
    feature_times = [_time(f['available_at']) for rows in partitions.values() for row in rows for f in row['features']]
    target_times = [_time(t['available_at']) for rows in partitions.values() for row in rows for t in row['targets']]
    return {'schema_version': contract['schema_version'], 'study_role': role,
            'analysis': analysis, 'data_access': access, 'replay': replay, 'availability': availability,
            'actual_admission_checked_at': now.isoformat(),
            'actual_new_fit_must_follow_approval': True,
            'historical_observation_range': [min(measurements).isoformat(), max(measurements).isoformat()],
            'replay_decision_range': [min(decisions).isoformat(), max(decisions).isoformat()],
            'feature_available_range': [min(feature_times).isoformat(), max(feature_times).isoformat()],
            'target_available_range': [min(target_times).isoformat(), max(target_times).isoformat()],
            'contains_confirmation_data': False, 'confirmatory_status': 'BLOCKED_CONFIRMATORY_TEST',
            'evidence_authenticity': 'REQUIRES_INDEPENDENT_REVIEW_NOT_ESTABLISHED_BY_HASHES'}
