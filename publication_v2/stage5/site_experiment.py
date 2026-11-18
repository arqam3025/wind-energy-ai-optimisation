"""Stage 5 second-site closed loop (Penmanshiel), reusing the Stage 4 design without re-tuning.

Stages: development (fit 2018–2020, evaluate 2021), validation (fit 2018–2021, evaluate 2022) and
sealed (fit 2018–2021, evaluate 2023–2024; frozen protocol only). The forecasters, conformal
intervals, skill score, episodes, battery and scoring are exactly as in Stage 4. Controllers
include the Stage 5 additions (graded switch, low-pass filter).
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import lightgbm
import numpy as np

from publication_v2.stage2.forecasting import fit_forecaster
from publication_v2.stage4 import experiment as s4
from publication_v2.stage4.closed_loop import STEPS, run_episode
from publication_v2.stage4.features import FEATURES, LABELS, build, complete
from .experiment import REGISTRY
from .sites import SITES, build_spatial, load_frames, spatial_features

STAGES = {
    'development': ((2018, 2019, 2020), (2021,), ('development',)),
    'validation': ((2018, 2019, 2020, 2021), (2022,), ('development', 'validation')),
    'sealed': ((2018, 2019, 2020, 2021), (2023, 2024), ('development', 'sealed_test')),
}
BUILTIN = ('uncontrolled', 'heuristic', 'adaptive', 'stochastic', 'stochastic_skill')
CONTROLLERS = BUILTIN + ('graded_mpc', 'lowpass_fast', 'graded_lowpass')
_SERIES = {}


def prepare(out: Path, site_name: str, stage: str, *, sealed_opt_in: bool = False) -> dict:
    site = SITES[site_name]
    fit_years, eval_years, allow = STAGES[stage]
    if stage == 'sealed' and not sealed_opt_in:
        raise PermissionError('The sealed test may only be opened by the frozen Stage 5 protocol runner')
    if any(site.archives[y][0] not in allow for y in (*fit_years, *eval_years)):
        raise PermissionError('stage definition opens a year outside its allowed roles')
    fit_frames, eval_frames = load_frames(site, fit_years, allow=allow), load_frames(site, eval_years, allow=allow)
    train = complete(build(fit_frames[site.target]))
    model = fit_forecaster('lightgbm', train[FEATURES].to_numpy(), train[LABELS].to_numpy())
    evaluation = build(eval_frames[site.target])
    ok = evaluation[FEATURES].notna().all(axis=1).to_numpy()
    predictions = {name: np.full((len(evaluation), len(LABELS)), np.nan) for name in s4.FORECASTS}
    x = evaluation.loc[ok, FEATURES].to_numpy()
    predictions['lightgbm'][ok] = model.predict(x)
    predictions['persistence'][ok] = np.repeat(x[:, :1], len(LABELS), axis=1)
    columns = spatial_features(site)
    s_train = build_spatial(fit_frames, site).dropna(subset=columns + LABELS)
    s_eval = build_spatial(eval_frames, site)
    if not s_eval.index.equals(evaluation.index):
        raise ValueError('spatial and target evaluation grids differ')
    s_ok = s_eval[columns].notna().all(axis=1).to_numpy()
    models = [lightgbm.LGBMRegressor(**s4.LGBM).fit(s_train[columns].to_numpy(), s_train[label].to_numpy())
              for label in LABELS]
    predictions['lightgbm_spatial'][s_ok] = np.maximum(0., np.column_stack(
        [m.predict(s_eval.loc[s_ok, columns].to_numpy()) for m in models]))
    predictions['perfect'] = evaluation[LABELS].to_numpy()  # PRIVILEGED reference
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / 'series.npz', times=evaluation.index.as_unit('ns').asi8,
                        realised=evaluation['power_kw'].to_numpy(), **{f'pred_{k}': v for k, v in predictions.items()})
    meta = {'site': site_name, 'stage': stage, 'target_turbine': site.target, 'neighbours': site.neighbours,
            'fit_years': fit_years, 'eval_years': eval_years, 'training_rows': model.training_rows,
            'training_features_sha256': model.training_features_sha256, 'spatial_training_rows': int(len(s_train)),
            'versions': model.versions, 'absent_rows': {str(t): int(f.attrs.get('absent_rows', 0)) for t, f in eval_frames.items()},
            'sources': sorted({site.archives[y][1] for y in (*fit_years, *eval_years)})}
    (out / 'prepare.json').write_text(json.dumps(meta, indent=1, default=str) + '\n', encoding='utf-8')
    return meta


def _init(out):
    _SERIES.update(s4._load(Path(out)))


def _task(args):
    forecast, k0, controller = args
    if controller in REGISTRY:
        decider, config = REGISTRY[controller]
        return run_episode(_SERIES[forecast], k0, controller, decider=decider, decider_config=config)
    return run_episode(_SERIES[forecast], k0, controller)


def run(out: Path, *, controllers=CONTROLLERS, stride: int = 1, workers: int | None = None):
    series = s4._load(out)
    sets = {name: set(s4.episode_starts(series[name])[0]) for name in s4.FORECASTS}
    common = sorted(set.intersection(*sets.values()))[::stride]
    tasks = [(f, k0, c) for f in s4.FORECASTS for k0 in common for c in controllers]
    start = time.time()
    with ProcessPoolExecutor(workers or max(1, (os.cpu_count() or 2) - 1), initializer=_init,
                             initargs=(str(out),)) as pool:
        results = list(pool.map(_task, tasks, chunksize=4))
    record = {'episodes': len(common), 'eligible_per_forecast': {k: len(v) for k, v in sets.items()},
              'stride': stride, 'steps': STEPS, 'seconds': time.time() - start, 'results': results}
    (out / f'results_stride{stride}.json').write_text(json.dumps(record) + '\n', encoding='utf-8')
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--site', default='penmanshiel', choices=list(SITES))
    parser.add_argument('--stage', choices=('development', 'validation'), default='development')
    parser.add_argument('--stride', type=int, default=1)
    args = parser.parse_args(argv)
    if not (args.out / 'series.npz').exists():
        print(prepare(args.out, args.site, args.stage))
    print(s4.summarise(run(args.out, stride=args.stride)))


if __name__ == '__main__':
    main()
