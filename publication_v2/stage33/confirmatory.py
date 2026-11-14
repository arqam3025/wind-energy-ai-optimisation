"""Stage 3.3 confirmatory (held-out) evaluation: frozen design and one-shot runner.

The design constants below are restated in docs/STAGE33_CONFIRMATORY_PROTOCOL.md.
The runner refuses to start unless: the protocol file's SHA-256 equals
PROTOCOL_SHA256, the git tree is clean, and the output directory does not exist.
Results are checkpointed per condition so an interrupted run resumes by
recomputing only missing conditions (computation is deterministic).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from .experiment import CONTROLLER_NAMES, DEVELOPMENT_SEEDS, environment, make_spec, run_matrix

PROTOCOL_PATH = Path(__file__).resolve().parents[2] / 'docs' / 'STAGE33_CONFIRMATORY_PROTOCOL.md'
PROTOCOL_SHA256 = None  # set when the protocol is frozen; None = not yet frozen (runner refuses)

HELD_OUT_SEEDS = tuple(range(700000, 700050))          # disjoint from development seeds 1000-1099
VOLATILITIES = (0.7, 1.0, 1.5)
STEPS = 48
SKILFUL = ('oracle25', 'oracle50', 'oracle100')
UNSKILLED = ('persistence', 'mean_reversion', 'skill_combo', 'damped_trend')
GRADIENT_ONLY = ('oracle150', 'oracle200')             # secondary (break-even curve)
FORECAST_CONDITIONS = SKILFUL + GRADIENT_ONLY + UNSKILLED
CONTROLLERS = CONTROLLER_NAMES                          # all 14, fixed in experiment.py
PRIMARY = 'stochastic_skill'


def protocol_sha256(path=PROTOCOL_PATH):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(*args):
    return subprocess.run(['git', *args], capture_output=True, text=True, check=True).stdout.strip()


def preflight(output: Path):
    if PROTOCOL_SHA256 is None:
        raise SystemExit('Refusing: protocol not frozen (PROTOCOL_SHA256 is None)')
    if protocol_sha256() != PROTOCOL_SHA256:
        raise SystemExit('Refusing: protocol file differs from the frozen SHA-256')
    if _git('status', '--porcelain', '--untracked-files=no'):
        raise SystemExit('Refusing: tracked files are modified; run from the frozen commit')
    if output.exists() and (output / 'COMPLETED.json').exists():
        raise SystemExit('Refusing: a completed confirmatory run already exists here')


def run(output: Path, workers=None, *, rehearsal_seeds=None):
    """Confirmatory run; ``rehearsal_seeds`` (development seeds only) exercises the pipeline unfrozen."""
    if rehearsal_seeds is None:
        preflight(output)
        seeds, role = HELD_OUT_SEEDS, 'SYNTHETIC_CONFIRMATORY_HELD_OUT_SEEDS'
    else:
        if not rehearsal_seeds or any(s not in DEVELOPMENT_SEEDS for s in rehearsal_seeds):
            raise SystemExit('Refusing: rehearsal may only use development seeds 1000-1099')
        if output.exists():
            raise SystemExit('Refusing to reuse a rehearsal directory')
        seeds, role = tuple(rehearsal_seeds), 'PIPELINE_REHEARSAL_DEVELOPMENT_SEEDS'
    output.mkdir(parents=True, exist_ok=True)
    manifest = {'study_role': role, 'protocol_sha256': PROTOCOL_SHA256 if rehearsal_seeds is None else protocol_sha256(),
                'git_head': _git('rev-parse', 'HEAD'), 'environment': environment(),
                'seeds': list(seeds), 'volatilities': list(VOLATILITIES), 'steps': STEPS,
                'forecasts': list(FORECAST_CONDITIONS), 'controllers': list(CONTROLLERS)}
    started = output / 'STARTED.json'
    if started.exists():
        previous = json.loads(started.read_text(encoding='utf-8'))
        if {k: previous[k] for k in ('protocol_sha256', 'git_head')} != {k: manifest[k] for k in ('protocol_sha256', 'git_head')}:
            raise SystemExit('Refusing to resume: partial run came from a different protocol/commit')
    else:
        started.write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    for forecast in FORECAST_CONDITIONS:
        path = output / f'{forecast}.json'
        if path.exists():
            continue
        specs = [(forecast, make_spec(forecast, seed, steps=STEPS, volatility=v))
                 for v in VOLATILITIES for seed in seeds]
        results = run_matrix(specs, CONTROLLERS, workers)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(results, allow_nan=False), encoding='utf-8')
        tmp.replace(path)
        print(f'{forecast}: {len(results)} runs', flush=True)
    digests = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob('*.json'))
               if p.name not in ('COMPLETED.json',)}
    (output / 'COMPLETED.json').write_text(json.dumps({**manifest, 'file_sha256': digests}, indent=1), encoding='utf-8')


def load(output: Path):
    completed = json.loads((output / 'COMPLETED.json').read_text(encoding='utf-8'))
    for name, digest in completed['file_sha256'].items():
        if hashlib.sha256((output / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Result file {name} does not match its recorded SHA-256')
    results = []
    for forecast in completed['forecasts']:
        results.extend(json.loads((output / f'{forecast}.json').read_text(encoding='utf-8')))
    return completed, results


def main(argv=None):
    parser = argparse.ArgumentParser(description='Stage 3.3 CONFIRMATORY run (held-out seeds, run once)')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=None)
    parser.add_argument('--rehearsal-seeds', type=int, nargs='+', default=None,
                        help='development seeds only: rehearse the pipeline without the frozen protocol')
    args = parser.parse_args(argv)
    run(args.out, args.workers, rehearsal_seeds=args.rehearsal_seeds)


if __name__ == '__main__':
    main()
