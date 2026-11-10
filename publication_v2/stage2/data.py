"""Explicit development ledger admission. No timezone/availability is inferred."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import csv
import json
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np

from publication_v2.integrity import inside, digest
from publication_v2.protocol import (Feature, FEATURE_SUPPORT, HORIZONS, timestamp, horizon,
    validate_features, validate_grid, validate_splits, finite)
from .lineage import verify_lineage,audit_cohort,AdmissionError

REQUIRED_PROVENANCE = ('source_release', 'timezone', 'measurement_semantics', 'units', 'licensing',
                       'availability', 'development_authorization', 'feature_recipe')


class DatasetError(ValueError):
    """No experiment is permitted from a missing or ineligible data ledger."""


def time(value) -> datetime:
    try:
        return timestamp(datetime.fromisoformat(value))
    except (ValueError, TypeError) as error:
        raise DatasetError(f'Missing/invalid offset-aware timestamp: {value!r}') from error


@dataclass(frozen=True)
class Observation:
    target_time: datetime
    value_kw: float
    available_at: datetime
    residual_available_at: datetime
    previous_target_time: datetime
    previous_value_kw: float
    previous_available_at: datetime


@dataclass(frozen=True)
class Sample:
    origin: datetime
    issued: datetime
    decision: datetime
    features: tuple[Feature, ...]
    observations: tuple[Observation, ...]


@dataclass(frozen=True)
class DevelopmentBundle:
    partitions: dict[str, tuple[Sample, ...]]
    fit_time: datetime
    grid_anchor: datetime
    input_hashes: dict[str, str]
    provenance: dict
    dataset_kind: str
    dataset_sha256: str
    admission_report: dict

    def features_for(self, role: str) -> np.ndarray:
        return np.asarray([[{f.name:f.value for f in sample.features}[name] for name in FEATURE_SUPPORT]
                           for sample in self.partitions[role]], dtype=float)

    def targets_for_fit(self) -> np.ndarray:
        return np.asarray([[o.value_kw for o in sample.observations] for sample in self.partitions['train']],dtype=float)


def load_bundle(path: Path, root: Path, *, allow_synthetic: bool = False) -> DevelopmentBundle:
    path = path.absolute()
    if not path.is_relative_to(root.resolve()):
        raise DatasetError('Input ledger must be within the declared repository/workspace root')
    path = inside(root,path.relative_to(root).as_posix())
    if not path.is_file():
        raise DatasetError(f'Missing required dataset ledger: {path}')
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
        return validate_document(document, root, path, allow_synthetic=allow_synthetic)
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, DatasetError): raise
        rejection=DatasetError(f'Invalid dataset ledger {path}: {error}')
        rejection.report=getattr(error,'report',{'status':'REJECTED','reason':str(error)})
        raise rejection from error


def validate_document(doc: dict, root: Path, path: Path, *, allow_synthetic: bool = False) -> DevelopmentBundle:
    if doc.get('schema_version') != 'publication_v2.stage2.dataset.v1' or doc.get('scope') != 'DEVELOPMENT_ONLY':
        raise DatasetError('Only a versioned DEVELOPMENT_ONLY dataset ledger is accepted')
    kind = doc.get('dataset_kind')
    if type(allow_synthetic) is not bool or (allow_synthetic and kind=='REAL_DEVELOPMENT'):
        raise DatasetError('Software-test mode cannot admit real development observations')
    if kind not in ('REAL_DEVELOPMENT','SYNTHETIC_FIXTURE') or (kind=='SYNTHETIC_FIXTURE' and not allow_synthetic):
        raise DatasetError('Synthetic fixtures are allowed only through the explicit software-test API')
    if doc.get('contains_confirmation_data') is not False:
        raise DatasetError('Confirmation/test observations cannot be relabelled as development')
    provenance = doc.get('provenance',{})
    input_hashes = {path.relative_to(root).as_posix():digest(path)}
    for name in REQUIRED_PROVENANCE:
        item = provenance.get(name)
        expected_status = 'SYNTHETIC_FIXTURE' if kind=='SYNTHETIC_FIXTURE' else 'ATTESTED'
        if not isinstance(item,dict) or item.get('status') != expected_status or not item.get('value'):
            raise DatasetError(f'Missing or unattested provenance: {name}')
        evidence = item.get('evidence',{})
        evidence_path = inside(root,evidence.get('path',''))
        if digest(evidence_path) != evidence.get('sha256'):
            raise DatasetError(f'Provenance evidence identity mismatch: {name}')
        input_hashes[evidence['path']] = evidence['sha256']
    try: ZoneInfo(str(provenance['timezone']['value']))
    except (ZoneInfoNotFoundError,ValueError) as error: raise DatasetError('Unknown/unresolved source timezone') from error
    if provenance['units']['value'] != {'power':'kW','wind_speed':'m/s','wind_direction':'degrees'}:
        raise DatasetError('Explicit power/wind/direction units are required')
    if doc.get('target_transform') != 'max(0,raw_power_kw)':
        raise DatasetError('Physical target mapping must be explicitly declared, never silently inferred')
    lineage=verify_lineage(doc,root,kind)
    measurements=lineage.measurements
    input_hashes.update(lineage.input_hashes)
    anchor, fit_time = time(doc['grid_anchor']),time(doc['fit_time'])
    if set(doc.get('partitions',{})) != {'train','calibration','development'}:
        raise DatasetError('Exactly train/calibration/development partitions are required; no test role')
    admission_report=audit_cohort(doc,lineage,anchor)
    partitions = {}
    for role,records in doc['partitions'].items():
        samples = []
        for row in records:
            origin, issued, decision = map(time,(row['origin_time'],row['issued_at'],row['decision_time']))
            if not origin <= issued <= decision < origin+timedelta(minutes=10):
                raise DatasetError('Origin/issuance/decision must precede the first forecast target')
            features = tuple(Feature(f['name'],f['value'],tuple(map(time,f['source_times'])),
                time(f['available_at']),tuple(map(time,f['source_available_ats']))) for f in row['features'])
            validate_features(features,origin,issued)
            for feature in features:
                if any(t not in measurements for t in feature.source_times):
                    raise DatasetError('Missing measurement in required feature support')
                if any(receipt!=measurements[t]['available'] for t,receipt in zip(feature.source_times,feature.source_available_ats)):
                    raise DatasetError('Feature source-receipt lineage differs from measurements')
                name = feature.name
                if name in ('power_kw','wind_speed','wind_direction'):
                    expected = measurements[origin][name]
                elif '_lag_' in name:
                    key = 'power_kw' if name.startswith('power') else 'wind_speed'
                    expected = measurements[feature.source_times[0]][key]
                elif name.endswith('_change_10min'):
                    key = 'power_kw' if name.startswith('power') else 'wind_speed'
                    expected = measurements[origin][key]-measurements[origin-timedelta(minutes=10)][key]
                else:
                    expected = sum(measurements[origin-timedelta(minutes=k)]['power_kw'] for k in (0,10,20,30))/4
                if abs(feature.value-expected)>1e-6:
                    raise DatasetError(f'Feature value differs from source measurement lineage: {name}')
            observations = []
            target_rows = row['targets']
            if [item['horizon_minutes'] for item in target_rows] != list(HORIZONS):
                raise DatasetError('Every sample requires identical ordered six horizons')
            for h,item in zip(HORIZONS,target_rows):
                target, available, residual_ready = map(time,(item['target_time'],item['available_at'],item['residual_available_at']))
                previous, previous_available = map(time,(item['previous_target_time'],item['previous_available_at']))
                value, previous_value = item['value_kw'],item['previous_value_kw']
                finite(value,previous_value)
                if min(value,previous_value)<0 or target != origin+timedelta(minutes=h) or previous != target-timedelta(minutes=10):
                    raise DatasetError('Missing/misaligned/nonphysical target or adjacent ramp observation')
                if not target <= available <= residual_ready or previous_available < previous:
                    raise DatasetError('Observation/residual availability precedes its required inputs')
                if (target not in measurements or previous not in measurements or
                    abs(value-max(0,measurements[target]['power_kw']))>1e-6 or
                    abs(previous_value-max(0,measurements[previous]['power_kw']))>1e-6 or
                    available!=measurements[target]['available'] or previous_available!=measurements[previous]['available']):
                    raise DatasetError('Target/ramp observation value or receipt differs from source measurements')
                if role=='train' and not max(available,residual_ready) <= fit_time:
                    raise DatasetError('Training target is unavailable at the declared fitting cutoff')
                observations.append(Observation(target,float(value),available,residual_ready,previous,float(previous_value),previous_available))
            samples.append(Sample(origin,issued,decision,features,tuple(observations)))
        validate_grid([s.origin for s in samples],allow_gaps=True,anchor=anchor)
        partitions[role] = tuple(samples)
    validate_splits({role:[s.origin for s in rows] for role,rows in partitions.items()},
                    order=('train','calibration','development'),grid_anchor=anchor)
    latest_training_target = max(o.target_time for s in partitions['train'] for o in s.observations)
    first_calibration_origin = min(s.origin for s in partitions['calibration'])
    if not latest_training_target <= fit_time <= first_calibration_origin:
        raise DatasetError('Fitting cutoff is not after training labels and before calibration issuance')
    return DevelopmentBundle(partitions,fit_time,anchor,input_hashes,provenance,kind,digest(path),admission_report)
