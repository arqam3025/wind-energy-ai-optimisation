"""Stage 4 development experiment: real Kelmarsh closed loop on development data only.

Round 1 design (development, not confirmatory): forecasters are fitted on 2018-2020 and evaluated
in closed loop on 2021. 2021 is part of the development period; it is not the validation year
(2022) and not the sealed test (2023-2024). Episodes are 8-hour blocks starting at
00:00/08:00/16:00 UTC. The series starts on 2021-01-01, so every conformal and skill window is
built from out-of-sample 2021 residuals only.

Forecasts:
* ``persistence``: causal baseline;
* ``lightgbm``: Stage 2 forecaster with its default hyperparameters (not tuned on Kelmarsh);
* ``lightgbm_spatial``: the same learner and hyperparameters with causal neighbour-turbine
  features, selected in round 2 on an inner split (fit 2018-2019, select on 2020);
* ``perfect``: PRIVILEGED reference that uses realised future values. It is an upper bound, not
  a deployable forecaster.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

import lightgbm

from publication_v2.stage2.forecasting import DEFAULT_HYPERPARAMETERS, fit_forecaster
from .closed_loop import CONTROLLERS, STEPS, Series, eligible, run_episode
from .features import FEATURES, LABELS, SPATIAL_FEATURES, build, build_spatial, complete
from .kelmarsh import load_development_farm

FIT_YEARS, EVAL_YEAR = (2018, 2019, 2020), 2021
FORECASTS = ('persistence', 'lightgbm', 'lightgbm_spatial', 'perfect')
LGBM = dict(DEFAULT_HYPERPARAMETERS['lightgbm'], objective='regression', n_jobs=4, random_state=20261101,
            deterministic=True, force_col_wise=True, verbosity=-1)
_SERIES: dict[str, Series] = {}


def prepare(out: Path) -> dict:
    frames = load_development_farm()
    frame = frames[1]
    table = build(frame)
    spatial = build_spatial(frames)
    train = complete(table[table.index.year.isin(FIT_YEARS)])
    model = fit_forecaster('lightgbm', train[FEATURES].to_numpy(), train[LABELS].to_numpy())
    evaluation = table[table.index.year == EVAL_YEAR]
    features_ok = evaluation[FEATURES].notna().all(axis=1).to_numpy()
    predictions = {name: np.full((len(evaluation), len(LABELS)), np.nan) for name in FORECASTS}
    x = evaluation.loc[features_ok, FEATURES].to_numpy()
    predictions['lightgbm'][features_ok] = model.predict(x)
    predictions['persistence'][features_ok] = np.repeat(x[:, :1], len(LABELS), axis=1)
    s_train = spatial[spatial.index.year.isin(FIT_YEARS)].dropna(subset=SPATIAL_FEATURES + LABELS)
    s_eval = spatial[spatial.index.year == EVAL_YEAR]
    s_ok = s_eval[SPATIAL_FEATURES].notna().all(axis=1).to_numpy()
    spatial_models = [lightgbm.LGBMRegressor(**LGBM).fit(s_train[SPATIAL_FEATURES].to_numpy(), s_train[label].to_numpy())
                      for label in LABELS]
    predictions['lightgbm_spatial'][s_ok] = np.maximum(0., np.column_stack(
        [m.predict(s_eval.loc[s_ok, SPATIAL_FEATURES].to_numpy()) for m in spatial_models]))
    predictions['perfect'] = evaluation[LABELS].to_numpy()  # PRIVILEGED: realised future values
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / 'series.npz', times=evaluation.index.as_unit('ns').asi8, realised=evaluation['power_kw'].to_numpy(),
                        **{f'pred_{k}': v for k, v in predictions.items()})
    meta = {'fit_years': FIT_YEARS, 'eval_year': EVAL_YEAR, 'training_rows': model.training_rows,
            'training_features_sha256': model.training_features_sha256, 'versions': model.versions,
            'hyperparameters': model.hyperparameters, 'spatial_training_rows': int(len(s_train)), 'spatial_hyperparameters': LGBM,
            'sources': sorted({f.attrs.get('source', '') for f in frames.values()})}
    (out / 'prepare.json').write_text(json.dumps(meta, indent=1, default=str) + '\n', encoding='utf-8')
    return meta


def _load(out: Path):
    data = np.load(out / 'series.npz')
    times = pd.DatetimeIndex(pd.to_datetime(data['times'], unit='ns', utc=True))
    if not (times[0].year == times[-1].year == EVAL_YEAR):
        raise ValueError('series times are not in the evaluation year')
    return {name: Series(times, data['realised'], data[f'pred_{name}'], name) for name in FORECASTS}


def _init(out):
    _SERIES.update(_load(Path(out)))


def _task(args):
    name, k0, controller = args
    return run_episode(_SERIES[name], k0, controller)


def episode_starts(series: Series, stride: int = 1):
    candidates = [k for k, t in enumerate(series.times) if t.minute == 0 and t.hour in (0, 8, 16)]
    starts = [k for k in candidates if eligible(series, k)]
    return starts[::stride], len(candidates), len(starts)


def run(out: Path, *, stride: int, workers: int, forecasts=FORECASTS, controllers=CONTROLLERS):
    series = _load(out)
    # One shared episode set: eligible for every forecast (pairing across forecasts and controllers).
    sets = {name: set(episode_starts(series[name])[0]) for name in forecasts}
    common = sorted(set.intersection(*sets.values()))[::stride]
    tasks = [(name, k0, c) for name in forecasts for k0 in common for c in controllers]
    start = time.time()
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(str(out),)) as pool:
        results = list(pool.map(_task, tasks, chunksize=4))
    record = {'episodes': len(common), 'eligible_per_forecast': {k: len(v) for k, v in sets.items()},
              'stride': stride, 'steps': STEPS, 'seconds': time.time() - start, 'results': results}
    (out / f'results_stride{stride}.json').write_text(json.dumps(record) + '\n', encoding='utf-8')
    return record


def summarise(record):
    rows = {}
    for r in record['results']:
        key = (r['forecast'], r['controller'])
        rows.setdefault(key, []).append(r)
    lines = [f"episodes={record['episodes']}  eligible={record['eligible_per_forecast']}  seconds={record['seconds']:.0f}",
             f"{'forecast':12s} {'controller':18s} {'exceed kW/ep':>12s} {'viol/ep':>8s} {'thru kWh/ep':>11s} {'gated':>6s}"]
    for (f, c), rs in rows.items():
        exc = np.mean([r['metrics']['total_ramp_exceedance_kw'] for r in rs])
        vio = np.mean([r['metrics']['ramp_violations'] for r in rs])
        thr = np.mean([r['metrics']['total_throughput_kwh'] for r in rs])
        g = sum(r['decision_status_counts'].get('skill_gated', 0) for r in rs) / (STEPS * len(rs))
        lines.append(f'{f:12s} {c:18s} {exc:12.1f} {vio:8.2f} {thr:11.1f} {g:6.2f}')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--stride', type=int, default=6)
    parser.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args(argv)
    if args.prepare or not (args.out / 'series.npz').exists():
        print(prepare(args.out))
    print(summarise(run(args.out, stride=args.stride, workers=args.workers)))


if __name__ == '__main__':
    main()
