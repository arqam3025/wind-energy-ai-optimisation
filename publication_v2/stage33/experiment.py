"""Parallel paired experiment runner for Stage 3.2/3.3 controllers (synthetic only).

Every controller sees the identical action-independent forecast stream for a
scenario. Results are summaries (metrics + forecast diagnostics); full traces
are recomputable from the recorded spec and controller configuration.
Seed discipline: DEVELOPMENT seeds may be used for design decisions; HELD-OUT
seeds must only be run once, with a frozen protocol, after design is complete.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess

from publication_v2.stage31.evaluation import canonical_sha256
from publication_v2.stage32.episode import run_episode
from publication_v2.stage32.synthetic import ScenarioSpec
from .controller import StochasticMPCConfig, decide_stochastic

DEVELOPMENT_SEEDS = tuple(range(1000, 1100))
STAGE31_CONTROLLERS = ('uncontrolled', 'deterministic', 'fixed_margin', 'adaptive', 'heuristic')
STOCHASTIC_VARIANTS = {
    'stochastic': StochasticMPCConfig(),
    'stochastic_no_gate': StochasticMPCConfig(gate_kw=0.),
    'stochastic_terminal': StochasticMPCConfig(soc_mode='terminal'),
    'point_band_gate': StochasticMPCConfig(scenarios='point'),
}
CONTROLLER_NAMES = STAGE31_CONTROLLERS + tuple(STOCHASTIC_VARIANTS)
FORECASTS = {  # label -> (forecast_mode, forecast_noise_kw)
    'perfect': ('announced_perfect', 0.), 'oracle25': ('announced_noisy', 25.),
    'oracle50': ('announced_noisy', 50.), 'oracle75': ('announced_noisy', 75.),
    'oracle100': ('announced_noisy', 100.), 'damped_trend': ('damped_trend', 0.),
    'persistence': ('persistence', 0.),
}


def make_spec(forecast, seed, *, steps=24, volatility=1., calibration='rolling'):
    mode, noise = FORECASTS[forecast]
    return ScenarioSpec(f'{forecast}_s{seed}_v{volatility}', profile='stochastic', forecast_mode=mode,
                        forecast_noise_kw=noise, seed=seed, steps=steps, volatility=volatility,
                        calibration_method=calibration)


def run_one(task):
    spec_fields, forecast, controller = task
    spec = ScenarioSpec(**{**spec_fields, 'faults': tuple(tuple(f) for f in spec_fields['faults'])})
    kwargs = {}
    if controller in STOCHASTIC_VARIANTS:
        kwargs = dict(decider=decide_stochastic, decider_config=STOCHASTIC_VARIANTS[controller])
    run = run_episode(spec, controller, **kwargs)
    statuses = {}
    for row in run['rows']:
        statuses[row['status']] = statuses.get(row['status'], 0) + 1
    metrics = {k: v for k, v in run['metrics'].items() if not k.startswith('computation_time_')}
    return {'scenario': spec.name, 'forecast': forecast, 'seed': spec.seed, 'volatility': spec.volatility,
            'calibration': spec.calibration_method, 'controller': controller,
            'scenario_sha256': run['scenario_sha256'], 'wind_sha256': run['wind_sha256'],
            'forecast_stream_sha256': canonical_sha256([r['forecast_sha256'] for r in run['rows']]),
            'controller_config': run['controller_config'], 'metrics': metrics,
            'decision_status_counts': statuses,
            'computation_time_s_mean': run['metrics']['computation_time_s_mean'],
            'forecast_diagnostics': run['forecast_diagnostics']}


def run_matrix(specs, controllers=CONTROLLER_NAMES, workers=None):
    """specs: iterable of (forecast_label, ScenarioSpec). Returns paired result rows."""
    tasks = [(asdict(spec), label, name) for label, spec in specs for name in controllers]
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run_one, tasks, chunksize=1))
    by_scenario = {}
    for row in results:  # pairing check: identical wind and forecast stream per scenario
        ref = by_scenario.setdefault(row['scenario'], (row['wind_sha256'], row['forecast_stream_sha256']))
        if ref != (row['wind_sha256'], row['forecast_stream_sha256']):
            raise ValueError('Unpaired comparison: controllers saw different inputs')
    return results


def environment():
    def git(*args):
        try:
            return subprocess.run(['git', *args], capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    import numpy, scipy
    return {'python': platform.python_version(), 'numpy': numpy.__version__, 'scipy': scipy.__version__,
            'git_head': git('rev-parse', 'HEAD'), 'git_dirty': bool(git('status', '--porcelain'))}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Stage 3.3 DEVELOPMENT experiment matrix (synthetic only)')
    parser.add_argument('--seeds', type=int, nargs='+', required=True)
    parser.add_argument('--forecasts', nargs='+', default=list(FORECASTS))
    parser.add_argument('--controllers', nargs='+', default=list(CONTROLLER_NAMES))
    parser.add_argument('--volatility', type=float, nargs='+', default=[1.])
    parser.add_argument('--steps', type=int, default=24)
    parser.add_argument('--workers', type=int, default=None)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    if any(seed not in DEVELOPMENT_SEEDS for seed in args.seeds):
        raise SystemExit('Refusing: this entry point only runs DEVELOPMENT seeds 1000-1099')
    if args.out.exists():
        raise SystemExit('Refusing to overwrite an existing results file')
    specs = [(f, make_spec(f, s, steps=args.steps, volatility=v))
             for f in args.forecasts for s in args.seeds for v in args.volatility]
    results = run_matrix(specs, args.controllers, args.workers)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({'study_role': 'SYNTHETIC_DEVELOPMENT', 'arguments': {
        k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
        'environment': environment(), 'results': results}, indent=1, allow_nan=False), encoding='utf-8')
    print(f'wrote {len(results)} runs to {args.out}')


if __name__ == '__main__':
    main()
