"""Structural reconstruction of archived tables, without assigning a timezone.

No model is imported or run. Unknown issue/receipt/fitting times stay unknown;
successful value/clock joins cannot certify operational or confirmatory use.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
import math
from pathlib import Path

from .integrity import digest


class TemporalInputError(ValueError):
    """A required historical timestamp/value join cannot be verified."""


def _number(value: str, context: str) -> float:
    try:
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('nonfinite')
        return result
    except (ValueError, TypeError) as error:
        raise TemporalInputError(f'Missing/nonfinite numeric value: {context}') from error


def _rows(path: Path, *, raw: bool = False) -> list[tuple[datetime, dict]]:
    if not path.is_file():
        raise TemporalInputError(f'Missing required temporal input: {path}')
    result, seen = [], set()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        key = 'Date/Time' if raw else 'timestamp'
        if not reader.fieldnames or key not in reader.fieldnames:
            raise TemporalInputError(f'Missing timestamp column: {path}')
        for row in reader:
            try:
                time = datetime.strptime(row[key], '%d %m %Y %H:%M') if raw else datetime.fromisoformat(row[key])
            except (ValueError, TypeError) as error:
                raise TemporalInputError(f'Invalid timestamp in {path}') from error
            if time.tzinfo is not None:
                raise TemporalInputError('Historical opaque-clock audit cannot mix in assigned timezones')
            if time in seen or (result and time <= result[-1][0]):
                raise TemporalInputError(f'Duplicate/unsorted timestamp in {path}: {time}')
            if time.second or time.microsecond or time.minute % 10:
                raise TemporalInputError(f'Off-grid historical timestamp: {path}: {time}')
            seen.add(time)
            result.append((time, row))
    if not result:
        raise TemporalInputError(f'Empty required temporal input: {path}')
    return result


def reconstruct_features(root: Path) -> dict:
    raw_path = root / 'data/raw/T1.csv'
    raw = dict(_rows(raw_path, raw=True))
    first = next(iter(raw.values()))
    direction = next((key for key in first if key.startswith('Wind Direction')), None)
    if direction is None:
        raise TemporalInputError('Raw wind direction column is missing')
    source_columns = {'power_kw': 'LV ActivePower (kW)', 'wind_speed': 'Wind Speed (m/s)', 'wind_direction': direction}
    source = {t: {k: _number(row.get(v), f'{raw_path}:{t}:{v}') for k, v in source_columns.items()}
              for t, row in raw.items()}
    checks, targets, tables = 0, 0, []
    hashes = {'data/raw/T1.csv': digest(raw_path)}
    for relative in ('data/processed/wind_features_10min.csv', 'data/processed/wind_multistep_features.csv'):
        path = root / relative
        rows = _rows(path)
        for time, row in rows:
            required_times = [time - timedelta(minutes=k) for k in (0, 10, 20, 30, 60)]
            if any(t not in source for t in required_times):
                raise TemporalInputError(f'Missing feature source support: {relative}:{time}')
            expected = dict(source[time])
            for lag in (10, 20, 30, 60):
                past = source[time-timedelta(minutes=lag)]
                expected[f'power_lag_{lag}min'] = past['power_kw']
                expected[f'wind_lag_{lag}min'] = past['wind_speed']
            expected['power_change_10min'] = expected['power_kw'] - expected['power_lag_10min']
            expected['wind_change_10min'] = expected['wind_speed'] - expected['wind_lag_10min']
            expected['power_mean_40min'] = sum(source[time-timedelta(minutes=k)]['power_kw'] for k in (0,10,20,30))/4
            for key, value in expected.items():
                if abs(_number(row.get(key), f'{relative}:{time}:{key}') - value) > 1e-6:
                    raise TemporalInputError(f'Feature value/support mismatch: {relative}:{time}:{key}')
                checks += 1
            target = time + timedelta(minutes=10)
            if row.get('target_timestamp') != target.isoformat(sep=' '):
                raise TemporalInputError(f'Target timestamp mismatch: {relative}:{time}')
            expected_targets = [('target_power_kw', target)]
            if 'target_h1_kw' in row:
                expected_targets += [(f'target_h{h}_kw', time+timedelta(minutes=10*h)) for h in range(1,7)]
            for key, target in expected_targets:
                if target not in source:
                    raise TemporalInputError(f'Missing source target: {relative}:{target}')
                if abs(_number(row.get(key), f'{relative}:{time}:{key}') - source[target]['power_kw']) > 1e-6:
                    raise TemporalInputError(f'Target value mismatch: {relative}:{time}:{key}')
                targets += 1
        hashes[relative] = digest(path)
        tables.append({'path': relative, 'rows': len(rows), 'features_per_row': 14})
    return {'status': 'STRUCTURAL_CLOCK_AND_VALUE_JOINS_PASS', 'tables': tables,
            'feature_value_checks': checks, 'target_value_checks': targets,
            'input_sha256': hashes, 'source': source}


def audit_temporal_artifacts(root: Path) -> dict:
    features = reconstruct_features(root)
    source = features.pop('source')
    hashes = features.pop('input_sha256')
    for relative in ('scripts/prepare_all_evaluation_blocks.py', 'scripts/prepare_development_block_6.py',
                     'scripts/generate_multistep_validation_forecasts.py', 'scripts/generate_multistep_test_forecasts.py'):
        hashes[relative] = digest(root / relative)
    relatives = ['results/multistep_calibration_split.csv', 'results/multistep_controller_development_split.csv',
                 'results/multistep_mpc_validation_audited.csv', 'results/multistep_mpc_test_forecasts.csv']
    relatives += [f'data/processed/controller_development_blocks/development_block_{b}.csv' for b in range(1,19)]
    relatives += [f'data/processed/evaluation_block_{b}.csv' for b in range(1,51)]
    prediction_rows, target_checks, block_frames = 0, 0, {}
    for relative in relatives:
        rows = _rows(root / relative)
        hashes[relative] = digest(root / relative)
        for origin, row in rows:
            clipped_current = relative.startswith('data/processed/evaluation_block_')
            current = source[origin]['power_kw'] if origin in source else float('nan')
            expected_current = max(0, current) if clipped_current else current
            if origin not in source or abs(_number(row.get('current_power_kw'), relative) - expected_current) > .001:
                raise TemporalInputError(f'Forecast origin/current measurement mismatch: {relative}:{origin}')
            for h in range(1,7):
                target = origin+timedelta(minutes=10*h)
                if target not in source:
                    raise TemporalInputError(f'Missing forecast target: {relative}:{target}')
                actual = _number(row.get(f'actual_h{h}_kw'), relative)
                if abs(actual-max(0,source[target]['power_kw'])) > .001:
                    raise TemporalInputError(f'Forecast target alignment mismatch: {relative}:{origin}:h{h}')
                _number(row.get(f'xgboost_h{h}_kw'), relative)
                persistence = _number(row.get(f'persistence_h{h}_kw'), relative)
                if abs(persistence-max(0, _number(row['current_power_kw'], relative))) > .001:
                    raise TemporalInputError(f'Persistence origin mismatch: {relative}:{origin}')
                target_checks += 1
            prediction_rows += 1
        if relative.startswith('data/processed/evaluation_block_'):
            block_frames[int(Path(relative).stem.rsplit('_',1)[1])] = rows
    schedule_path = root / 'results/evaluation_schedule.csv'
    hashes['results/evaluation_schedule.csv'] = digest(schedule_path)
    with schedule_path.open(encoding='utf-8-sig', newline='') as stream:
        schedule = list(csv.DictReader(stream))
    ids = [int(row['block_id']) for row in schedule]
    if len(ids) != 50 or len(set(ids)) != 50 or set(ids) != set(block_frames):
        raise TemporalInputError('Scheduled episode identities are missing/duplicated')
    totals = {case: {'ramp_violations':0,'summed_exceedance_kw':0.,'transitions':0} for case in ('uncontrolled','fixed','adaptive_one_sided')}
    residual_checks, archived_rows = 0, 0
    for entry in schedule:
        block = int(entry['block_id'])
        frame = block_frames[block]
        times = [t for t,_ in frame]
        if len(frame) != 144 or any(b-a != timedelta(minutes=10) for a,b in zip(times,times[1:])):
            raise TemporalInputError(f'Episode is incomplete or has a cadence gap: {block}')
        if str(times[0]) != entry['start_timestamp'] or str(times[-1]) != entry['end_timestamp']:
            raise TemporalInputError(f'Schedule boundary differs from episode {block}')
        if int(entry['forecast_origins']) != len(frame) or entry['evaluation_role'] not in ('evaluation','development'):
            raise TemporalInputError(f'Unknown role or count for episode {block}')
        if entry['evaluation_role'] == 'development':
            if block != 6:
                raise TemporalInputError('Unexpected development role; protocol requires explicit review')
            continue
        for case in totals:
            previous = max(0, source[times[0]]['power_kw'])
            if case == 'uncontrolled':
                records = [(t+timedelta(minutes=10), {'grid_export_kw': row['actual_h1_kw']}) for t,row in frame]
            else:
                relative = f'results/frozen_heldout/final_20261029/{case}/adaptive_charging_mpc_block_{block}_weight_0p500.csv'
                path = root / relative
                records = _rows(path)
                hashes[relative] = digest(path)
                if len(records) != len(frame):
                    raise TemporalInputError(f'Incomplete archived episode: {relative}')
            for (executed, row), (origin, observed) in zip(records,frame):
                if executed != origin+timedelta(minutes=10):
                    raise TemporalInputError(f'Archived decision/target timestamp mismatch: {block}:{case}')
                if case != 'uncontrolled':
                    if abs(_number(row.get('wind_generation_kw'), str(block))-_number(observed['actual_h1_kw'], str(block))) > .001:
                        raise TemporalInputError('Archived outcome differs from source target')
                    archived_rows += 1
                if case == 'adaptive_one_sided':
                    newest = datetime.fromisoformat(row.get('newest_residual_target',''))
                    if newest.tzinfo is not None or not newest < origin:
                        raise TemporalInputError(f'Equal/future archived residual target at {origin}')
                    residual_checks += 1
                export = _number(row.get('grid_export_kw'), f'{block}:{case}')
                ramp = abs(export-previous)
                totals[case]['ramp_violations'] += int(ramp > 200.001)
                totals[case]['summed_exceedance_kw'] += max(0, ramp-200)
                totals[case]['transitions'] += 1
                previous = export
    if any(record['transitions'] != 7056 for record in totals.values()):
        raise TemporalInputError('Original retrospective cohort differs from 49x144')
    return {'status': 'STRUCTURAL_AUDIT_ONLY_NOT_OPERATIONAL_CERTIFICATION', 'features': features,
            'clock': 'opaque historical dataset clock; no timezone or latency assigned',
            'power_encoding': 'Raw/features/forecast-table current power is signed. Prepared evaluation-block current power, all persistence forecasts and all actual forecast targets are clipped at zero; original preparation scripts are the evidence.',
            'forecast_tables': len(relatives), 'forecast_origin_rows_checked': prediction_rows,
            'forecast_target_pairs_checked': target_checks, 'archived_target_rows_checked': archived_rows,
            'strict_archived_newest_residual_target_checks': residual_checks,
            'calibration_availability_limit': 'Target-before-decision can be checked structurally; observation/residual arrival and forecast issue times are not recorded',
            'historical_boundary_violations': 'See inventory.boundary_findings; findings are retained, never repaired or used as eligible input',
            'original_retrospective_metrics_recomputed': totals, 'input_sha256': hashes,
            'new_forecast_or_control_algorithm_executed': False}
