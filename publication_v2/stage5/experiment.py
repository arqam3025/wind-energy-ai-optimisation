"""Stage 5 exploratory runner: extra controllers on the SAME episodes as a completed Stage 4 run.

Used on DEVELOPMENT data (Kelmarsh 2021, fitted on 2018-2020) to design improvements. It reads
the ``series.npz`` and ``prepare.json`` of a Stage 4 run directory, reconstructs the identical
paired episode set, runs only the requested extra controllers, and merges their results with the
stored Stage 4 results for analysis. The sealed 2023-2024 data is never used here.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from publication_v2.stage4 import experiment as s4
from publication_v2.stage4.closed_loop import run_episode
from publication_v2.stage33.controller import StochasticMPCConfig, decide_stochastic
from publication_v2.stage33.experiment import STOCHASTIC_VARIANTS
from .filters import FILTER_VARIANTS, decide_filter
from .switches import GradedConfig, decide_filter_gated, decide_graded_filter, decide_graded_mpc

REGISTRY = {name: (decide_filter, cfg) for name, cfg in FILTER_VARIANTS.items()}
REGISTRY.update({
    'stochastic_skill00': (decide_stochastic, STOCHASTIC_VARIANTS['stochastic_skill00']),
    'graded_mpc': (decide_graded_mpc, GradedConfig(base=StochasticMPCConfig())),
    'lowpass_fast_gated': (decide_filter_gated, FILTER_VARIANTS['lowpass_fast']),
    'graded_lowpass': (decide_graded_filter, GradedConfig(base=FILTER_VARIANTS['lowpass_fast'])),
})
_SERIES = {}


def register(name, decider, config):
    REGISTRY[name] = (decider, config)


def _init(series_dir):
    _SERIES.update(s4._load(Path(series_dir)))


def _task(args):
    forecast, k0, controller = args
    decider, config = REGISTRY[controller]
    return run_episode(_SERIES[forecast], k0, controller, decider=decider, decider_config=config)


def episodes(series_dir: Path):
    series = s4._load(series_dir)
    sets = {name: set(s4.episode_starts(series[name])[0]) for name in s4.FORECASTS}
    return sorted(set.intersection(*sets.values()))


def run(series_dir: Path, out: Path, controllers, forecasts=s4.FORECASTS, workers=None):
    meta = json.loads((series_dir / 'prepare.json').read_text(encoding='utf-8'))
    if meta.get('stage') == 'sealed' or 2023 in meta.get('eval_years', []):
        raise PermissionError('Stage 5 exploration must not use the sealed test years')
    common = episodes(series_dir)
    tasks = [(f, k0, c) for f in forecasts for k0 in common for c in controllers]
    start = time.time()
    with ProcessPoolExecutor(workers or max(1, (os.cpu_count() or 2) - 1), initializer=_init,
                             initargs=(str(series_dir),)) as pool:
        results = list(pool.map(_task, tasks, chunksize=8))
    out.mkdir(parents=True, exist_ok=True)
    record = {'source_run': str(series_dir), 'episodes': len(common), 'controllers': list(controllers),
              'seconds': time.time() - start, 'results': results}
    (out / 'extra_results.json').write_text(json.dumps(record) + '\n', encoding='utf-8')
    return record


def merged(base_results: Path, extra: dict):
    base = json.loads(base_results.read_text(encoding='utf-8'))
    starts = {r['start'] for r in extra['results']}
    kept = [r for r in base['results'] if r['start'] in starts]
    return {**base, 'episodes': extra['episodes'], 'results': kept + extra['results']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('series_dir', type=Path, help='a completed Stage 4 development/validation run directory')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--controllers', nargs='+', default=list(FILTER_VARIANTS))
    args = parser.parse_args(argv)
    record = run(args.series_dir, args.out, args.controllers)
    print(f"{record['episodes']} episodes x {len(record['controllers'])} controllers in {record['seconds']:.0f} s")


if __name__ == '__main__':
    main()
