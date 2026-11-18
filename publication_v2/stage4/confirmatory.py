"""Stage 4 frozen-protocol runner for the SEALED test (2023-2024). The 2022 validation check runs
before the freeze through ``experiment.py --stage validation``.

The runner refuses unless:
- the protocol file's SHA-256 equals ``PROTOCOL_SHA256``;
- the git tree is clean;
- for the sealed test, the output directory does not already hold a completed run.

It records the commit, environment and SHA-256 of every output. The sealed test is run once; a
resume is allowed only from the same commit and protocol, and it must be reported as a deviation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / 'docs' / 'STAGE4_CONFIRMATORY_PROTOCOL.md'
PROTOCOL_SHA256 = 'd8337ad97bfd55fdffd368002fc8ffe61a94afb5ccdcc5e9ea1b1b771d84bda7'  # frozen 2026-11-17


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args) -> str:
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def preflight(stage: str, out: Path) -> dict:
    if PROTOCOL_SHA256 is None:
        raise SystemExit('Protocol not frozen: PROTOCOL_SHA256 is unset')
    if _sha(PROTOCOL) != PROTOCOL_SHA256:
        raise SystemExit('Protocol file does not match the frozen SHA-256')
    if _git('status', '--porcelain', '--untracked-files=no'):
        raise SystemExit('Tracked files are modified; run from a clean checkout of the frozen commit')
    if (out / 'COMPLETED.json').exists():
        raise SystemExit(f'{out} already holds a completed run; it is never overwritten')
    started = out / 'STARTED.json'
    head = _git('rev-parse', 'HEAD')
    if started.exists():
        previous = json.loads(started.read_text(encoding='utf-8'))
        if previous['git_head'] != head or previous['protocol_sha256'] != PROTOCOL_SHA256 or previous['stage'] != stage:
            raise SystemExit('A resume must use the same commit, protocol and stage')
    import lightgbm, numpy, pandas, scipy  # noqa: E401
    return {'stage': stage, 'protocol_sha256': PROTOCOL_SHA256, 'git_head': head,
            'started_utc': datetime.now(timezone.utc).isoformat(),
            'environment': {'python': platform.python_version(), 'numpy': numpy.__version__,
                            'pandas': pandas.__version__, 'scipy': scipy.__version__,
                            'lightgbm': lightgbm.__version__, 'platform': platform.platform()}}


def run(stage: str, out: Path, workers: int):
    from . import analysis, experiment
    record = preflight(stage, out)
    out.mkdir(parents=True, exist_ok=True)
    if not (out / 'STARTED.json').exists():
        (out / 'STARTED.json').write_bytes((json.dumps(record, indent=1) + '\n').encode())
    if not (out / 'series.npz').exists():
        experiment.prepare(out, stage, sealed_opt_in=(stage == 'sealed'))
    results = experiment.run(out, stride=1, workers=workers)
    tests, rows = analysis.primary_tests(results['results']), analysis.descriptive(results['results'])
    (out / 'tests.json').write_bytes((json.dumps({'tests': tests, 'descriptive': rows}, indent=1) + '\n').encode())
    skill = analysis.forecast_skill(out)
    (out / 'forecast_skill.json').write_bytes((json.dumps(skill, indent=1) + chr(10)).encode())
    (out / 'REPORT.md').write_bytes((analysis.render(tests, rows, results) + analysis.render_skill(skill)).encode())
    files = sorted(p.name for p in out.iterdir() if p.is_file() and p.name != 'COMPLETED.json')
    completed = {**record, 'completed_utc': datetime.now(timezone.utc).isoformat(),
                 'file_sha256': {name: _sha(out / name) for name in files}}
    (out / 'COMPLETED.json').write_bytes((json.dumps(completed, indent=1) + '\n').encode())
    print((out / 'REPORT.md').read_text(encoding='utf-8'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--stage', choices=('sealed',), default='sealed')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = parser.parse_args(argv)
    run(args.stage, args.out, args.workers)


if __name__ == '__main__':
    sys.exit(main())
