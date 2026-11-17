"""Re-execute a closed CSV transform; keep byte identity separate from trust.

The real-data review registry is deliberately empty. Maintainer approval of
independent evidence is necessary before populating it; this module does not
authenticate the truth of a review merely by hashing its document.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

from publication_v2.integrity import digest,inside
from publication_v2.protocol import timestamp,finite,validate_grid
from .study import validate_study_contract,StudyError,RETROSPECTIVE_DEVELOPMENT

FIELDS=('event_time','available_at','source_observation_id','power_kw','wind_speed','wind_direction')
TRANSFORM_ID='column-map-offset-aware-numeric-v1'
IMPLEMENTATION=Path(__file__).resolve()
POLICY=IMPLEMENTATION.with_name('provenance_policy.json')


class AdmissionError(ValueError):
    def __init__(self,message,report=None):
        super().__init__(message)
        self.report=report or {'status':'REJECTED','reason':message}


def _time(value):
    try:return timestamp(datetime.fromisoformat(value))
    except (ValueError,TypeError) as error:raise AdmissionError(f'Invalid or unsupported timestamp: {value!r}') from error


def _json_artifact(root,reference,hashes):
    if not isinstance(reference,dict):raise AdmissionError('Missing hashed manifest/policy reference')
    path=inside(root,reference.get('path',''))
    if digest(path)!=reference.get('sha256'):raise AdmissionError(f'Artifact hash mismatch: {reference.get("path")}')
    hashes[reference['path']]=reference['sha256']
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError,OSError) as error:raise AdmissionError('Malformed lineage/policy JSON') from error


def _read_measurements(path,column_map):
    """Normalize values independent of row order, quoting and numeric spelling."""
    result={}; ids=set();raw_count=0
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if (not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames) or
            not set(column_map.values()).issubset(reader.fieldnames)):
            raise AdmissionError('Transformation mapping references missing upstream columns')
        for row in reader:
            raw_count+=1
            if None in row or any(v is None for v in row.values()):
                raise AdmissionError('Malformed CSV row has missing or extra cells')
            event,available=(_time(row[column_map[k]]) for k in ('event_time','available_at'))
            observation_id=row[column_map['source_observation_id']]
            if not isinstance(observation_id,str) or not observation_id.strip() or observation_id.strip()!=observation_id:
                raise AdmissionError('Missing/unsupported source observation identity')
            if event in result or observation_id in ids:
                raise AdmissionError('Duplicate observation identity or event timestamp',
                    {'status':'REJECTED','raw_rows_seen':raw_count,'duplicate_observation':observation_id,'event_time':event.isoformat()})
            if available<event:raise AdmissionError('Measurement availability precedes event')
            try:values={k:float(row[column_map[k]]) for k in FIELDS[3:]};finite(*values.values())
            except (ValueError,TypeError) as error:raise AdmissionError('Missing/nonfinite source measurement; no implicit repair') from error
            result[event]={'available':available,'source_observation_id':observation_id,**values};ids.add(observation_id)
    if not result:raise AdmissionError('Source measurements are empty')
    return dict(sorted(result.items()))


def semantic_sha256(measurements):
    normalized=[(t.isoformat(),v['available'].isoformat(),v['source_observation_id'],
                 *(v[k].hex() for k in FIELDS[3:])) for t,v in sorted(measurements.items())]
    return hashlib.sha256(json.dumps(normalized,separators=(',',':')).encode()).hexdigest()


def _signal(value):return tuple(float(value[k]).hex() for k in ('power_kw','wind_speed','wind_direction'))


def historical_registry(policy):
    """Known observations survive re-exported byte hashes and source aliases.

    A signal match alone may also be an identity collision. Such a collision is
    conservatively unresolved/exposed; it is never evidence of an untouched row.
    """
    known=policy['known_historical_source'];root=IMPLEMENTATION.parents[2]
    path=inside(root,known['path'])
    if digest(path)!=known['sha256']:raise AdmissionError('Known historical exposure registry changed')
    with inside(root,'results/evaluation_schedule.csv').open(encoding='utf-8-sig',newline='') as f:
        schedule=list(csv.DictReader(f))
    first_evaluation=min(datetime.fromisoformat(r['start_timestamp']) for r in schedule if r['evaluation_role']=='evaluation')
    if datetime.fromisoformat(known['native_evaluation_start'])!=first_evaluation:
        raise AdmissionError('Exposure policy boundary differs from the preserved evaluation schedule')
    return _historical_rows(str(path),known['sha256'])


@lru_cache(maxsize=2)
def _historical_rows(path,expected_digest):
    path=Path(path)
    # The caller rehashes the source on every admission before using this cache.
    result={}
    with path.open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            direction=next(k for k in row if k.startswith('Wind Direction'))
            values={'power_kw':float(row['LV ActivePower (kW)']),'wind_speed':float(row['Wind Speed (m/s)']),
                    'wind_direction':float(row[direction])}
            native=datetime.strptime(row['Date/Time'],'%d %m %Y %H:%M')
            result.setdefault(_signal(values),[]).append(native)
    return MappingProxyType({key:tuple(values) for key,values in result.items()})


@dataclass(frozen=True)
class VerifiedLineage:
    measurements:dict
    source_identity:dict
    authorization:dict
    cohort_policy:dict
    input_hashes:dict
    semantic_sha256:str
    historical_matches:dict
    historical_evaluation_start:datetime
    report:dict


def verify_lineage(document,root,kind):
    hashes={}
    manifest=_json_artifact(root,document.get('lineage_manifest'),hashes)
    if manifest.get('schema_version')!='publication_v2.stage21.lineage.v1':raise AdmissionError('Unsupported/missing transformation manifest')
    identity=manifest.get('source_identity',{})
    required=('provider','dataset','release','observation_namespace')
    if any(not isinstance(identity.get(k),str) or not identity[k].strip() for k in required):
        raise AdmissionError('Stable provider/dataset/release/observation namespace identity is required')
    if manifest.get('scope')!='DEVELOPMENT_ONLY' or manifest.get('confirmatory_status')!='BLOCKED_CONFIRMATORY_TEST':
        raise AdmissionError('Lineage cannot authorize confirmation or an untouched-data claim')
    transform=manifest.get('transformation',{})
    if (set(transform)!={'id','implementation_sha256','column_map'} or
        transform.get('id')!=TRANSFORM_ID or transform.get('implementation_sha256')!=digest(IMPLEMENTATION)):
        raise AdmissionError('Unsupported or changed transformation identity/implementation')
    mapping=transform.get('column_map')
    if (not isinstance(mapping,dict) or set(mapping)!=set(FIELDS) or
        any(not isinstance(v,str) or not v for v in mapping.values()) or len(set(mapping.values()))!=len(FIELDS)):
        raise AdmissionError('A complete one-to-one transformation column mapping is required')
    source=document.get('source_artifact',{})
    if source.get('schema_version')!='publication_v2.stage2.measurements.csv.v1':
        raise AdmissionError('Unsupported canonical measurement schema')
    if source.get('path')==source.get('upstream',{}).get('path'):
        raise AdmissionError('Upstream and canonical output must be separately identified artifacts')
    for key,ref in (('canonical',source),('upstream',source.get('upstream',{}))):
        if manifest.get(key)!=ref:raise AdmissionError('Lineage source/output identity differs from dataset declaration')
        path=inside(root,ref.get('path',''))
        if digest(path)!=ref.get('sha256'):raise AdmissionError(f'{key} byte hash mismatch')
        hashes[ref['path']]=ref['sha256']
    canonical=_read_measurements(inside(root,source['path']),{k:k for k in FIELDS})
    upstream=_read_measurements(inside(root,source['upstream']['path']),mapping)
    canonical_sha=semantic_sha256(canonical)
    if semantic_sha256(upstream)!=canonical_sha or manifest.get('canonical_semantic_sha256')!=canonical_sha:
        raise AdmissionError('Re-executed upstream transformation does not match canonical observations')
    cohort=_json_artifact(root,document.get('cohort_policy'),hashes)
    policy=json.loads(POLICY.read_text(encoding='utf-8'))
    if policy.get('schema_version')!='publication_v2.stage21.trust-policy.v1' or policy.get('confirmatory_status')!='BLOCKED_CONFIRMATORY_TEST':
        raise AdmissionError('Invalid trust policy; confirmation remains blocked')
    if kind=='REAL_DEVELOPMENT':
        # The dataset cannot authorize its own trust, source aliases or periods.
        review=policy.get('real_data_reviews',{}).get(manifest.get('independent_review_id'))
        if not review or review.get('independently_checked') is not True:
            raise AdmissionError('No independently checked source/rights/clock/lineage/period review is trusted; self-attestation is insufficient')
        if (review.get('lineage_manifest_sha256')!=document['lineage_manifest']['sha256'] or
            review.get('cohort_policy_sha256')!=document['cohort_policy']['sha256'] or
            review.get('source_identity')!=identity or
            review.get('provenance_sha256')!=hashlib.sha256(json.dumps(document.get('provenance'),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest() or
            review.get('dataset_document_sha256')!=hashlib.sha256(json.dumps(document,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()):
            raise AdmissionError('Independent review does not authorize this lineage/policy/source/provenance')
        evidence=review.get('review_document',{});evidence_path=inside(root,evidence.get('path',''))
        if digest(evidence_path)!=evidence.get('sha256') or not review.get('reviewer'):
            raise AdmissionError('Missing independently checked review identity/evidence')
        hashes[evidence['path']]=evidence['sha256']
        authorization=review.get('authorized_periods',{})
    else:
        if manifest.get('independent_review_id')!='SYNTHETIC_TEST_ONLY':raise AdmissionError('Synthetic fixtures must not claim an independent review')
        authorization=cohort.get('authorized_periods',{})
    if set(authorization)!={'train','calibration','development'}:raise AdmissionError('Explicit role-specific authorized periods are required')
    for role,window in authorization.items():
        if set(window)!={'start','end'} or _time(window['start'])>_time(window['end']):
            raise AdmissionError(f'Invalid authorized source period: {role}')
    try:
        study=validate_study_contract(document,cohort,root,kind,canonical,hashes)
    except StudyError as error:
        raise AdmissionError(str(error)) from error
    if study is not None:
        if manifest.get('study_role',study['study_role'])!=study['study_role']:
            raise AdmissionError('Lineage and reviewed study-role labels differ')
        if kind=='REAL_DEVELOPMENT' and (
            review.get('study_role')!=study['study_role'] or
            review.get('study_contract_sha256')!=document['study_contract']['sha256'] or
            review.get('analysis_clock_evidence_sha256')!=study['analysis']['clock_evidence']['sha256'] or
            review.get('availability_mode')!=study['availability']['mode']):
            raise AdmissionError('Independent review does not authorize this study role, actual analysis clock or availability scenario')
    registry=historical_registry(policy)
    matches={t:registry[_signal(row)] for t,row in canonical.items() if _signal(row) in registry}
    report={'status':'TRANSFORMATION_VERIFIED_NOT_A_PROVENANCE_THEOREM','raw_upstream_rows':len(upstream),
            'canonical_rows':len(canonical),'source_identity':identity,'transform_id':TRANSFORM_ID,
            'canonical_semantic_sha256':canonical_sha,'historical_or_identity_collision_count':len(matches),
            'exposure_classification':'HISTORICAL_OR_UNRESOLVED_COLLISION' if matches else 'NO_KNOWN_MATCH_NOT_EVIDENCE_OF_UNTOUCHED',
            'confirmatory_status':'BLOCKED_CONFIRMATORY_TEST','trust_status':'INDEPENDENT_REVIEW_PINNED' if kind=='REAL_DEVELOPMENT' else 'SYNTHETIC_SOFTWARE_FIXTURE_ONLY'}
    if study is not None:
        report['study_contract']=study
        report['study_role']=study['study_role']
    else:
        report['study_role']='LEGACY_SYNTHETIC_SOFTWARE_FIXTURE_ONLY'
    cutoff=datetime.fromisoformat(policy['known_historical_source']['native_evaluation_start'])
    return VerifiedLineage(canonical,identity,authorization,cohort,hashes,canonical_sha,matches,cutoff,report)


def audit_cohort(document,lineage,anchor):
    policy=lineage.cohort_policy
    required={'schema_version','policy_id','declared_at','missing_cells','duplicates','imputation','gaps',
              'declared_missing_measurements','role_origin_windows','excluded_origins','authorized_periods','measurement_window'}
    if not required.issubset(policy) or policy.get('schema_version')!='publication_v2.stage21.cohort-policy.v1':
        raise AdmissionError('Missing prespecified missing-data/cohort-exclusion policy')
    if policy['missing_cells']!='reject' or policy['duplicates']!='reject' or policy['imputation']!='forbidden' or policy['gaps'] not in ('reject','declared_missing_slots_only'):
        raise AdmissionError('Unsupported missing-data, duplicate or imputation policy')
    if set(policy['role_origin_windows'])!={'train','calibration','development'}:raise AdmissionError('All role candidate windows must be declared')
    measurements=lineage.measurements;times=list(measurements)
    validate_grid(times,allow_gaps=True,anchor=anchor)
    window=policy['measurement_window'];first,last=_time(window['start']),_time(window['end'])
    if first>last:raise AdmissionError('Invalid prespecified measurement coverage window')
    validate_grid((first,last) if first!=last else (first,),allow_gaps=True,anchor=anchor)
    expected={first+timedelta(minutes=10*i) for i in range(int((last-first).total_seconds()/600)+1)}
    if not set(times).issubset(expected):raise AdmissionError('Measurements lie outside prespecified source coverage')
    missing=expected-set(times);declared={_time(t) for t in policy['declared_missing_measurements']}
    report={**lineage.report,'policy_id':policy['policy_id'],'expected_measurement_slots':len(expected),'observed_measurements':len(times),
            'missing_measurement_count':len(missing),'missing_measurements':[t.isoformat() for t in sorted(missing)],
            'authorized_periods':lineage.authorization,'measurement_window':window,
            'timestamp_gaps':[{'after':a.isoformat(),'before':b.isoformat(),'missing_slots':int((b-a).total_seconds()/600)-1}
                for a,b in zip(times,times[1:]) if b-a>timedelta(minutes=10)],'roles':{},'rejected_origins':[]}
    def fail(message):raise AdmissionError(message,{**report,'status':'REJECTED','reason':message})
    if declared!=missing or (missing and policy['gaps']=='reject'):fail('Unaccounted or prohibited source timestamp gaps')
    exclusions={}
    for item in policy['excluded_origins']:
        key=(item['role'],_time(item['origin_time']))
        if key in exclusions or item.get('reason') not in ('missing_feature_support','missing_target_support'):
            fail('Duplicate or unsupported cohort exclusion reason')
        exclusions[key]=item
    consumed=set()
    for role,window in policy['role_origin_windows'].items():
        start,end=_time(window['start']),_time(window['end'])
        if start>end:fail('Invalid role candidate window')
        # Actual declaration/approval clocks are validated in the new explicit
        # retrospective contract. Retain the old rule only for old synthetic
        # software fixtures; it must never authorize a real research dataset.
        if lineage.report.get('study_role')!=RETROSPECTIVE_DEVELOPMENT and _time(policy['declared_at'])>=start:
            fail('Legacy synthetic cohort policy must precede every candidate origin')
        validate_grid((start,end) if start!=end else (start,),allow_gaps=True,anchor=anchor)
        candidates=[start+timedelta(minutes=10*i) for i in range(int((end-start).total_seconds()/600)+1)]
        provided=[_time(row['origin_time']) for row in document['partitions'][role]]
        if len(provided)!=len(set(provided)) or not set(provided).issubset(candidates):fail('Duplicate or unauthorized cohort origin')
        counts={'candidate_origins':len(candidates),'provided_origins':len(provided),'accepted_origins':0,
                'excluded_origins':0,'missing_feature_support':0,'missing_target_support':0}
        report['roles'][role]=counts
        auth=lineage.authorization[role];left,right=_time(auth['start']),_time(auth['end'])
        for origin in candidates:
            feature_support={origin-timedelta(minutes=k) for k in (0,10,20,30,60)}
            targets={origin+timedelta(minutes=h) for h in (10,20,30,40,50,60)}
            referenced=feature_support|targets
            if min(referenced)<left or max(referenced)>right:fail('Observation or feature/target support outside authorized source period')
            missing_features=feature_support-set(times);missing_targets=targets-set(times)
            if origin in provided:
                if (role,origin) in exclusions:fail('An excluded origin is also included')
                if missing_features or missing_targets:fail('Included origin has missing feature/target support')
                # Match by measurement identity/content, not raw file bytes or claimed aliases.
                for t in referenced:
                    if any(native>=lineage.historical_evaluation_start for native in lineage.historical_matches.get(t,())):
                        fail('Historically evaluated observation or unresolved historical identity collision is not authorized for new development')
                counts['accepted_origins']+=1
            else:
                exclusion=exclusions.get((role,origin))
                reason='missing_feature_support' if missing_features else 'missing_target_support' if missing_targets else None
                if not exclusion or reason is None or exclusion['reason']!=reason:fail('Silent or unsupported cohort omission')
                record={'role':role,'origin_time':origin.isoformat(),'reason':reason,
                        'missing_feature_times':[t.isoformat() for t in sorted(missing_features)],
                        'missing_target_times':[t.isoformat() for t in sorted(missing_targets)]}
                report['rejected_origins'].append(record);consumed.add((role,origin));counts['excluded_origins']+=1;counts[reason]+=1
        report['roles'][role]=counts
    if set(exclusions)!=consumed:fail('Exclusion policy contains entries outside candidate windows')
    report['candidate_origins']=sum(c['candidate_origins'] for c in report['roles'].values())
    report['accepted_origins']=sum(c['accepted_origins'] for c in report['roles'].values())
    report['excluded_origin_count']=len(report['rejected_origins']);report['status']='ADMITTED_DEVELOPMENT_ONLY' if document['dataset_kind']=='REAL_DEVELOPMENT' else 'SYNTHETIC_FIXTURE_ADMITTED'
    return report
