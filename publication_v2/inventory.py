"""Read-only chronological and provenance inventory for publication Stage 1.

The local timestamps are an opaque, naive dataset clock. This module never
localizes them to UTC, trains a model, evaluates a controller or proposes a
test split from the absence of saved scores. Human access is not reconstructible
from a filesystem: missing attestation is an explicit confirmatory blocker.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
import hashlib
from importlib import metadata as package_metadata
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any

STEP = timedelta(minutes=10)
PACKAGES = ('numpy', 'pandas', 'scipy', 'matplotlib', 'cvxpy', 'highspy', 'xgboost',
            'scikit-learn', 'streamlit', 'plotly')


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def parse_dataset_time(value: str) -> datetime:
    """Parse encoding only: an offset must never be invented for naive records."""
    if not isinstance(value, str):
        raise ValueError('Missing or non-string timestamp')
    text = value.strip()
    if not text:
        raise ValueError('Missing timestamp')
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.strptime(text, '%d %m %Y %H:%M')


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def profile_csv(path: Path, root: Path) -> dict[str, Any]:
    """Inspect row/timestamp structure without interpreting missing rows as data."""
    fields, rows = _read(path)
    column = next((name for name in ('timestamp', 'Date/Time', 'start_timestamp') if name in fields), None)
    profile: dict[str, Any] = {'path': path.relative_to(root).as_posix(), 'sha256': digest(path),
        'bytes': path.stat().st_size, 'rows': len(rows), 'columns': fields,
        'timestamp_column': column, 'timestamp_semantics': 'historical encoding; physical availability not attested',
        'clock_status': 'UNKNOWN_TIMEZONE', 'missing_cells': sum(v is None or not str(v).strip()
            for row in rows for v in row.values()), 'status': 'AVAILABLE', 'nonfinite_numeric_cells': []}
    timestamps: list[datetime] = []
    errors: list[dict[str, Any]] = []
    if column is not None:
        for index, row in enumerate(rows, start=2):
            try:
                timestamps.append(parse_dataset_time(row.get(column, '')))
            except (ValueError, TypeError) as error:
                errors.append({'csv_line': index, 'error': str(error)})
    if errors:
        profile['status'] = 'INVALID_TIMESTAMP_ENCODING'
    naive = sum(t.tzinfo is None or t.utcoffset() is None for t in timestamps)
    aware = len(timestamps) - naive
    profile.update(timestamp_errors=errors, timestamp_count=len(timestamps),
        naive_timestamp_count=naive, offset_encoded_timestamp_count=aware,
        duplicated_timestamps=len(timestamps) - len(set(timestamps)))
    if naive and aware:
        profile['status'] = 'MIXED_CLOCK_ENCODING'
        return profile
    if timestamps:
        ordered = sorted(set(timestamps))
        differences = [b - a for a, b in zip(ordered, ordered[1:])]
        expected_step = STEP if column != 'start_timestamp' else None
        horizons = sorted({int(match.group(1)) for name in fields
            if (match := re.fullmatch(r'(?:target|actual)_h([1-6])_kw', name))})
        profile.update(first_timestamp=ordered[0].isoformat(sep=' '), last_timestamp=ordered[-1].isoformat(sep=' '),
            strictly_increasing_in_file=all(a < b for a, b in zip(timestamps, timestamps[1:])),
            expected_step_minutes=10 if expected_step else None,
            non_ten_minute_gap_count=sum(delta != STEP for delta in differences) if expected_step else None,
            missing_ten_minute_slots=sum(max(0, int(delta / STEP) - 1) for delta in differences) if expected_step else None,
            off_grid_gap_count=sum(delta % STEP != timedelta() for delta in differences) if expected_step else None,
            explicit_horizon_steps=horizons,
            latest_inferred_target_timestamp=(ordered[-1] + horizons[-1] * STEP).isoformat(sep=' ') if horizons else None,
            inferred_target_basis='origin + named horizon; not an observation-availability attestation' if horizons else None)
        if column == 'Date/Time':
            profile['timestamp_semantics'] = 'raw SCADA measurement timestamp; integration window and release time unknown'
        elif horizons:
            profile['timestamp_semantics'] = 'forecast/feature origin; targets inferred at origin + horizon'
    nonfinite: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        for name, value in row.items():
            if name == column or value is None or not str(value).strip():
                continue
            try:
                number = float(value)
            except (ValueError, TypeError):
                continue
            if not math.isfinite(number):
                nonfinite.append({'csv_line': index, 'column': name})
    profile['nonfinite_numeric_cells'] = nonfinite
    return profile


def _origins(path: Path) -> list[datetime]:
    _, rows = _read(path)
    return [parse_dataset_time(row['timestamp']) for row in rows]


def _known_role(path: str, schedule_roles: dict[int, str]) -> str:
    match = re.fullmatch(r'data/processed/evaluation_block_(\d+)\.csv', path)
    if match:
        return 'historical_' + schedule_roles.get(int(match.group(1)), 'role_unverified')
    if '/controller_development_blocks/' in path or 'controller_development_split' in path:
        return 'historical_development'
    if path.endswith('multistep_calibration_split.csv'):
        return 'historical_calibration'
    if path == 'data/raw/T1.csv':
        return 'source_previously_loaded_and_audited'
    if path.endswith(('wind_multistep_features.csv', 'wind_features_10min.csv', 'wind_forecasting_10min.csv')):
        return 'previously_materialized_full_source_features'
    if 'test' in path:
        return 'historical_test_period_exposed_retrospective'
    if 'validation' in path:
        return 'historical_validation'
    return 'historical_artifact_role_not_exhaustively_attested'


def boundary_findings(root: Path) -> dict[str, Any]:
    """Recompute historical target boundaries; do not silently purge old data."""
    output: dict[str, Any] = {'clock': 'opaque dataset-local naive timestamps',
                             'interpretation': 'Historical defects are inventoried, never used as a valid new protocol.'}
    calibration = root / 'results/multistep_calibration_split.csv'
    development = root / 'data/processed/controller_development_blocks/development_block_1.csv'
    if calibration.exists() and development.exists():
        origins = _origins(calibration)
        decisions = _origins(development)
        first = decisions[0]
        unavailable = []
        for h in range(1, 7):
            target_times = [t + h * STEP for t in origins]
            affected = [(t, sum(target >= t for target in target_times)) for t in decisions if t <= max(target_times)]
            unavailable.append({'horizon_minutes': h * 10,
                'latest_calibration_target': max(target_times).isoformat(sep=' '),
                'unavailable_at_first_development_decision': sum(t >= first for t in target_times),
                'affected_decision_cells': len(affected),
                'unavailable_label_decision_pairs': sum(count for _, count in affected)})
        output['calibration_development'] = {'first_development_decision': first.isoformat(sep=' '),
            'strict_target_time_before_decision': all(t['unavailable_at_first_development_decision'] == 0 for t in unavailable),
            'by_horizon': unavailable, 'affected_horizon_decision_cells': sum(t['affected_decision_cells'] for t in unavailable),
            'unavailable_label_decision_pairs': sum(t['unavailable_label_decision_pairs'] for t in unavailable),
            'evidence': [calibration.relative_to(root).as_posix(), development.relative_to(root).as_posix()]}
    schedule_path = root / 'results/evaluation_schedule.csv'
    if schedule_path.exists():
        _, schedule = _read(schedule_path)
        role_frames: list[tuple[dict[str, str], list[datetime]]] = []
        for row in schedule:
            source = root / f"data/processed/evaluation_block_{row['block_id']}.csv"
            if source.exists():
                role_frames.append((row, _origins(source)))
        development_targets: dict[datetime, set[tuple[int, int]]] = {}
        for row, origins in role_frames:
            if row['evaluation_role'] == 'development':
                for origin in origins:
                    for h in range(1, 7):
                        development_targets.setdefault(origin + h * STEP, set()).add((int(row['block_id']), h))
        overlap = []
        for row, origins in role_frames:
            if row['evaluation_role'] != 'evaluation':
                continue
            for origin in origins:
                for h in range(1, 7):
                    target = origin + h * STEP
                    if target in development_targets:
                        overlap.append({'evaluation_block': int(row['block_id']), 'evaluation_horizon_minutes': h * 10,
                            'evaluation_origin': origin.isoformat(sep=' '), 'shared_target': target.isoformat(sep=' '),
                            'development_blocks': sorted({b for b, _ in development_targets[target]})})
        output['scheduled_role_overlap'] = {'development_blocks': [int(r['block_id']) for r in schedule if r['evaluation_role'] == 'development'],
            'evaluation_blocks': [int(r['block_id']) for r in schedule if r['evaluation_role'] == 'evaluation'],
            'overlapping_horizon_target_pairs': len(overlap),
            'unique_shared_target_times': len({r['shared_target'] for r in overlap}),
            'overlapping_scored_h1_times': len({r['shared_target'] for r in overlap if r['evaluation_horizon_minutes'] == 10}),
            'overlaps': overlap, 'evidence': ['results/evaluation_schedule.csv', 'data/processed/evaluation_block_6.csv']}
        # The full development CSV also includes a tail outside the eighteen
        # complete controller episodes. Inventory its declared role without
        # inventing evidence that this unused tail selected the frozen policy.
        declared_development = root / 'results/multistep_controller_development_split.csv'
        if declared_development.exists():
            declared_origins = _origins(declared_development)
            declared_targets = {t + h * STEP for t in declared_origins for h in range(1, 7)}
            declared_overlap = []
            for row, origins in role_frames:
                if row['evaluation_role'] == 'evaluation':
                    for origin in origins:
                        for h in range(1, 7):
                            target = origin + h * STEP
                            if target in declared_targets:
                                declared_overlap.append({'evaluation_block': int(row['block_id']),
                                    'evaluation_origin': origin.isoformat(sep=' '),
                                    'evaluation_horizon_minutes': h * 10, 'shared_target': target.isoformat(sep=' ')})
            output['full_declared_development_artifact_overlap'] = {
                'development_artifact': declared_development.relative_to(root).as_posix(),
                'development_origins': len(declared_origins),
                'latest_origin': max(declared_origins).isoformat(sep=' ') if declared_origins else None,
                'latest_h6_target': max(declared_targets).isoformat(sep=' ') if declared_targets else None,
                'overlapping_horizon_target_pairs': len(declared_overlap),
                'unique_shared_target_times': len({r['shared_target'] for r in declared_overlap}),
                'overlapping_scored_h1_times': len({r['shared_target'] for r in declared_overlap if r['evaluation_horizon_minutes'] == 10}),
                'overlaps': declared_overlap,
                'qualification': 'Declared development artifact includes a tail beyond the eighteen complete controller blocks. Its existence/exposure is confirmed; use of that tail for frozen-controller selection is not established.'}
            union_times = development_targets.keys() | declared_targets
            combined = []
            for row, origins in role_frames:
                if row['evaluation_role'] == 'evaluation':
                    for origin in origins:
                        for h in range(1, 7):
                            target = origin + h * STEP
                            if target in union_times:
                                combined.append((target, h))
            output['combined_declared_development_overlap'] = {
                'overlapping_horizon_target_pairs': len(combined),
                'unique_shared_target_times': len({t for t, _ in combined}),
                'overlapping_scored_h1_times': len({t for t, h in combined if h == 1}),
                'scope': 'Union of the full declared validation-development artifact and every schedule-designated development block; source-target timestamps deduplicated.'}
    return output


def _git_evidence(root: Path) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for key, arguments in {
        'current_branch': ['branch', '--show-current'], 'head': ['rev-parse', 'HEAD'],
        'pre_freeze_inspection_commit': ['show', '--format=%H%n%aI%n%s', '--no-patch', 'bcb2c99'],
        'pre_freeze_inspection_paths': ['ls-tree', '-r', '--name-only', 'bcb2c99', '--',
            'scripts/inspect_block_25_event.py', 'scripts/inspect_block_34_forecasts.py']}.items():
        completed = subprocess.run(['git', *arguments], cwd=root, capture_output=True, text=True, check=False)
        results[key] = completed.stdout.strip() if completed.returncode == 0 else None
        if completed.returncode:
            results[key + '_status'] = 'UNAVAILABLE_GIT_EVIDENCE'
    return results


def build_inventory(root: Path) -> dict[str, Any]:
    """Inspect existing artifacts only; return JSON-safe facts and honest blockers."""
    root = Path(root).resolve()
    metadata_path = Path(__file__).with_name('metadata.json')
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    required = ['data/raw/T1.csv', 'data/processed/wind_features_10min.csv',
        'data/processed/wind_multistep_features.csv', 'results/multistep_calibration_split.csv',
        'results/multistep_controller_development_split.csv', 'results/evaluation_schedule.csv',
        'results/development_controller_freeze_manifest.json']
    required += [f'models/wind_xgboost_h{h}.json' for h in range(1, 7)]
    required += [f'data/processed/controller_development_blocks/development_block_{b}.csv' for b in range(1, 19)]
    required += [f'data/processed/evaluation_block_{b}.csv' for b in range(1, 51)]
    missing = [name for name in required if not (root / name).is_file()]
    schedule_roles = {}
    if (root / 'results/evaluation_schedule.csv').exists():
        _, schedule = _read(root / 'results/evaluation_schedule.csv')
        schedule_roles = {int(row['block_id']): row['evaluation_role'] for row in schedule}
    paths = list((root / 'data').rglob('*.csv'))
    paths += sorted((root / 'results').glob('multistep*.csv'))
    if (root / 'results/evaluation_schedule.csv').exists():
        paths.append(root / 'results/evaluation_schedule.csv')
    profiles = []
    for path in sorted(set(paths)):
        profile = profile_csv(path, root)
        profile['historical_role'] = _known_role(profile['path'], schedule_roles)
        profiles.append(profile)
    models = [{'path': p.relative_to(root).as_posix(), 'sha256': digest(p), 'bytes': p.stat().st_size,
        'status': 'EXISTING_MODEL_NOT_RETRAINED', 'historical_fit_attestation': 'UNKNOWN',
        'prediction_issue_time_attestation': 'UNKNOWN'} for p in sorted((root / 'models').glob('*')) if p.is_file()]
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = package_metadata.version(name)
        except package_metadata.PackageNotFoundError:
            versions[name] = None
    source_requirements = root / 'requirements-research.txt'
    requirement_versions = {}
    if source_requirements.exists():
        for line in source_requirements.read_text(encoding='utf-8').splitlines():
            if '==' in line and not line.lstrip().startswith('#'):
                name, version = line.split('==', 1)
                requirement_versions[name.strip()] = version.strip()
    environment = {'python': platform.python_version(), 'implementation': platform.python_implementation(),
        'platform': platform.platform(), 'interpreter': sys.executable,
        'stage1_runtime_dependencies': 'Python standard library only', 'installed_research_packages': versions,
        'declared_research_packages': requirement_versions,
        'declared_package_mismatches': {n: {'declared': v, 'installed': versions.get(n)}
            for n, v in requirement_versions.items() if versions.get(n) != v},
        'clean_environment_replication': 'NOT_PERFORMED'}
    evidence = [
        {'kind': 'prior_source_audit', 'scope': 'the complete local raw CSV was loaded for descriptive inspection',
         'evidence': ['scripts/audit_wind_dataset.py:5', 'scripts/audit_wind_dataset.py:47'],
         'qualification': 'Source proves intended full-file analysis; human reading of every row is not attested.'},
        {'kind': 'saved_full_feature_audit', 'scope': 'all 50,125 retained feature rows reconstructed in a previous audit',
         'evidence': ['results/research_grade_v1/forecast_uncertainty/audit_summary.json',
                      'results/research_grade_v1/forecast_uncertainty/feature_timestamp_audit.csv'],
         'qualification': 'This is prior artifact inspection, not a new performance experiment or exhaustive human-access log.'},
        {'kind': 'pre_freeze_evaluation_access', 'scope': 'evaluation blocks 25 and 34 investigated before the freeze',
         'evidence': ['git:bcb2c99:scripts/inspect_block_25_event.py', 'git:bcb2c99:scripts/inspect_block_34_forecasts.py']},
        {'kind': 'development_access', 'scope': '18 validation-period development episodes and schedule-designated block 6',
         'evidence': ['data/processed/controller_development_blocks/', 'results/evaluation_schedule.csv',
                      'scripts/prepare_development_block_6.py']},
        {'kind': 'retrospective_evaluation_access', 'scope': '49 archived scored episodes and subsequent six-case study',
         'evidence': ['results/frozen_heldout/final_20261029/',
                      'results/research_grade_v1_20261029/benchmark/protocol.json', 'docs/EXPERIMENTAL_RESULTS.md']},
        {'kind': 'attestation_absent', 'scope': 'no independently reserved uninspected outcome source has a release/access attestation',
         'evidence': ['publication_v2/metadata.json'],
         'qualification': 'Unscored or unlisted rows are exposure-unknown, never inferred untouched.'}]
    inputs = {p['path']: p['sha256'] for p in profiles}
    for name in required:
        path = root / name
        if path.is_file():
            inputs[name] = digest(path)
    for name in ('requirements-research.txt', 'docs/environment-frozen-evaluation.txt',
                 'results/research_grade_v1/forecast_uncertainty/audit_summary.json',
                 'scripts/audit_wind_dataset.py', 'scripts/build_wind_features.py', 'scripts/prepare_multistep_ml_data.py',
                 'scripts/train_multistep_xgboost.py', 'scripts/prepare_evaluation_schedule.py',
                 'scripts/prepare_development_block_6.py'):
        path = root / name
        if path.is_file():
            inputs[name] = digest(path)
    blockers = [{'code': 'BLOCKED_CONFIRMATORY_TEST', 'message': 'No genuinely uninspected eligible dataset with verifiable access/reservation evidence is available.',
                 'evidence': [e['kind'] for e in evidence]},
        {'code': 'UNKNOWN_DATASET_VERSION', 'message': 'The local SHA256 identifies bytes, not an independently attested upstream dataset release.'},
        {'code': 'UNKNOWN_TIMEZONE', 'message': 'Naive source timestamps do not establish timezone, DST, integration-window end, or clock synchronization.'},
        {'code': 'UNKNOWN_MEASUREMENT_AVAILABILITY', 'message': 'Physical measurement/release latency and operational forecast issue time are not attested.'},
        {'code': 'UNKNOWN_DATA_LICENSE', 'message': 'Dataset access does not establish redistribution permission; exact acquisition terms are absent.'},
        {'code': 'UNATTESTED_HISTORICAL_MODEL_FIT', 'message': 'Current model hashes and source consistency do not independently attest historical fitting data/access.'},
        {'code': 'CLEAN_ENVIRONMENT_NOT_REPLICATED', 'message': 'Installed-package capture is not a tested clean-room installation.'}]
    if missing:
        blockers.append({'code': 'MISSING_REQUIRED_INPUTS', 'message': 'Required local artifact bundle is incomplete.', 'evidence': missing})
    invalid = [p['path'] for p in profiles if p['status'] != 'AVAILABLE' or p.get('duplicated_timestamps', 0) or p['nonfinite_numeric_cells'] or p['missing_cells']]
    if invalid:
        blockers.append({'code': 'INVALID_HISTORICAL_INPUT_STRUCTURE', 'message': 'Historical files contain invalid/duplicate timestamps or nonfinite numeric cells.', 'evidence': invalid})
    return {'schema_version': 'publication_v2.inventory.v1', 'chronology_clock': 'opaque dataset-local naive; physical timezone unknown',
        'chronological_artifacts': sorted(profiles, key=lambda p: (p.get('first_timestamp', ''), p['path'])),
        'model_artifacts': models, 'exposure_evidence': evidence, 'git_evidence': _git_evidence(root),
        'boundary_findings': boundary_findings(root), 'provenance': metadata,
        'blockers': blockers, 'missing_inputs': missing, 'input_sha256': inputs,
        'model_sha256': {p['path']: p['sha256'] for p in models}, 'environment': environment,
        'confirmatory_status': 'BLOCKED_CONFIRMATORY_TEST',
        'confirmatory_test': {'status': 'BLOCKED_CONFIRMATORY_TEST', 'proposed_split': None,
            'reason': 'Existing 49 episodes are retrospective; no eligible uninspected data with verifiable reservation/access evidence is supplied.',
            'uncovered_rows_policy': 'Not scored is not untouched. Uncovered periods remain exposure-unknown.',
            'additional_data_needed': metadata['additional_data_needed']}}
