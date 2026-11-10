"""Read-only, exact-machine environment evidence for development experiments.

The installed distribution closure and native bytes are recorded, not just six
top-level version strings.  This is an environment fingerprint, not evidence of
dataset provenance or of a successful clean-machine installation.  Native hashes
are platform-specific; they cannot replace a portable wheel/container lock and
an independently exercised clean-environment reproduction.
"""
from __future__ import annotations

import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

SCHEMA = 'publication_v2.stage2.environment.v1'
REQUIREMENTS = Path(__file__).with_name('requirements.txt')
_NATIVE_SUFFIXES = ('.dll', '.pyd', '.so', '.dylib', '.lib', '.a')
_REQUIRED_PROBES = ('numpy', 'scipy', 'sklearn', 'xgboost', 'lightgbm')
_SHA256 = re.compile(r'^[0-9a-f]{64}$')
_THREAD_ENV = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
               'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')


class EnvironmentError(ValueError):
    """An environment is incomplete, inconsistent, or changed."""


def _sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _normalise(name: str) -> str:
    return re.sub(r'[-_.]+', '-', name).lower()


def _distribution_inventory() -> tuple[list[dict], list[dict], list[str]]:
    packages, native, issues = [], [], []
    for distribution in metadata.distributions():
        name = distribution.metadata.get('Name')
        version = distribution.version
        if not name or not isinstance(version, str) or not version.strip():
            issues.append('Installed distribution has missing name/version metadata')
            continue
        files = distribution.files
        if files is None:
            issues.append(f'{name}: installed file inventory is unavailable')
        packages.append({'name': name, 'canonical_name': _normalise(name), 'version': version,
                         'location': str(Path(distribution.locate_file('')).resolve()),
                         'file_inventory_available': files is not None})
        for relative in files or ():
            text = str(relative).lower()
            if not (text.endswith(_NATIVE_SUFFIXES) or '.so.' in text):
                continue
            path = Path(distribution.locate_file(relative)).resolve()
            entry = {'distribution': _normalise(name), 'relative_path': str(relative).replace('\\', '/'),
                     'path': str(path)}
            try:
                entry.update(sha256=_sha256(path), size_bytes=path.stat().st_size, status='available')
            except OSError as error:
                entry.update(sha256=None, size_bytes=None, status='unavailable', error=type(error).__name__)
                issues.append(f'{name}: required native artifact unavailable: {relative}')
            native.append(entry)
    packages.sort(key=lambda entry: (entry['canonical_name'], entry['version'], entry['location']))
    native.sort(key=lambda entry: (entry['distribution'], entry['relative_path'], entry['path']))
    names = [entry['canonical_name'] for entry in packages]
    if len(names) != len(set(names)):
        issues.append('Ambiguous duplicate installed distribution names')
    return packages, native, sorted(set(issues))


def _requirements(packages: list[dict], path: Path = REQUIREMENTS) -> dict:
    raw = path.read_bytes()
    text = raw.decode('utf-8')
    installed = {entry['canonical_name']: entry['version'] for entry in packages}
    checks, issues = [], []
    seen = set()
    for number, line in enumerate(text.splitlines(), 1):
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9_.-]*)==([^\s;]+)', line)
        if not match:
            issues.append(f'Unsupported dependency requirement on line {number}: exact pins required')
            continue
        name, expected = _normalise(match[1]), match[2]
        actual = installed.get(name)
        if name in seen:
            issues.append(f'Duplicate direct dependency requirement: {name}')
        seen.add(name)
        checks.append({'name': name, 'expected_version': expected, 'installed_version': actual,
                       'status': 'match' if actual == expected else 'missing' if actual is None else 'mismatch'})
    if not checks:
        issues.append('No supported direct dependency pins were supplied')
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(raw).hexdigest(),
            'checks': checks, 'issues': issues,
            'status': 'pass' if not issues and all(row['status'] == 'match' for row in checks) else 'fail'}


_PROBE_SCRIPT = r'''
import importlib, json
modules = {}
for name in ('numpy', 'scipy', 'sklearn', 'xgboost', 'lightgbm', 'cvxpy', 'highspy', 'clarabel', 'osqp', 'scs'):
    try:
        module = importlib.import_module(name)
        version = getattr(module, '__version__', None)
        if name == 'highspy':
            parts = [getattr(module, 'HIGHS_VERSION_' + part, None) for part in ('MAJOR','MINOR','PATCH')]
            version = '.'.join(map(str, parts)) if all(isinstance(part, int) for part in parts) else None
        modules[name] = {'status':'available', 'reported_version':str(version) if version is not None else None,
                         'version_status':'reported' if version is not None else 'unavailable',
                         'module_file':getattr(module, '__file__', None)}
    except Exception as error:
        modules[name] = {'status':'unavailable', 'reported_version':None, 'version_status':'unavailable',
                         'error_type':type(error).__name__, 'error':str(error)}
try:
    from threadpoolctl import threadpool_info
    pools = threadpool_info()
    pools.sort(key=lambda row: (str(row.get('filepath')), str(row.get('internal_api'))))
    threadpools = {'status':'available', 'libraries':pools}
except Exception as error:
    threadpools = {'status':'unavailable', 'libraries':[], 'error_type':type(error).__name__, 'error':str(error)}
print(json.dumps({'modules':modules, 'threadpools':threadpools}, sort_keys=True))
'''


def _native_probe() -> dict:
    # A fixed import order in a fresh interpreter avoids differences caused by
    # whichever numerical modules the experiment happened to load previously.
    child_env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    controls = {name: '1' for name in _THREAD_ENV}
    child_env.update(controls)
    try:
        result = subprocess.run([sys.executable, '-B', '-c', _PROBE_SCRIPT], env=child_env,
                                capture_output=True, text=True, check=False, timeout=45)
        if result.returncode:
            return {'status': 'unavailable', 'modules': {}, 'threadpools': {'status': 'unavailable', 'libraries': []},
                    'error': f'Isolated import probe exited {result.returncode}', 'stderr': result.stderr.strip(),
                    'probe_thread_controls': controls}
        report = json.loads(result.stdout)
        report.update(status='available', stderr=result.stderr.strip(), probe_thread_controls=controls)
        for entry in report['threadpools']['libraries']:
            path = entry.get('filepath')
            try:
                entry['sha256'] = _sha256(Path(path)) if path else None
                entry['binary_hash_status'] = 'available' if path else 'unavailable'
            except OSError as error:
                entry.update(sha256=None, binary_hash_status='unavailable', hash_error=type(error).__name__)
        return report
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        return {'status': 'unavailable', 'modules': {}, 'threadpools': {'status': 'unavailable', 'libraries': []},
                'error_type': type(error).__name__, 'error': str(error), 'probe_thread_controls': controls}


def capture_environment() -> dict:
    """Capture actual installed evidence without fitting, solving, or installing.

    Missing information remains explicit.  Call ``validate_environment`` before
    starting an experiment; a recorded missing item is not reproducibility proof.
    No probe timestamp or process/thread count that changes during fitting is
    included, so a run may compare independently captured snapshots exactly.
    """
    packages, native, issues = _distribution_inventory()
    executable_hashes = []
    for value in sorted({sys.executable, getattr(sys, '_base_executable', sys.executable)}):
        path = Path(value).resolve()
        try:
            executable_hashes.append({'path': str(path), 'sha256': _sha256(path), 'status': 'available'})
        except OSError as error:
            executable_hashes.append({'path': str(path), 'sha256': None, 'status': 'unavailable',
                                      'error': type(error).__name__})
            issues.append(f'Interpreter executable unavailable: {path}')
    return {'schema_version': SCHEMA,
            'python': {'version': platform.python_version(), 'full_version': sys.version,
                       'implementation': platform.python_implementation(), 'implementation_version': list(sys.implementation.version),
                       'cache_tag': sys.implementation.cache_tag, 'build': list(platform.python_build()),
                       'compiler': platform.python_compiler(), 'executable': sys.executable,
                       'base_executable': getattr(sys, '_base_executable', None), 'executable_sha256': executable_hashes,
                       'sys_platform': sys.platform, 'byteorder': sys.byteorder},
            'operating_system': {'system': platform.system(), 'release': platform.release(), 'version': platform.version(),
                                 'platform': platform.platform(), 'machine': platform.machine(), 'processor': platform.processor(),
                                 'architecture': list(platform.architecture()), 'logical_cpu_count': os.cpu_count()},
            'installed_distributions': packages, 'direct_requirements': _requirements(packages),
            'native_distribution_artifacts': native, 'native_runtime': _native_probe(),
            'thread_environment': {name: os.environ.get(name) for name in _THREAD_ENV},
            'inventory_issues': sorted(set(issues)),
            'reproduction': {'clean_environment_validated': False, 'environment_lock_scope': 'all installed distribution versions',
                             'native_hash_scope': 'installed distribution binaries and threadpoolctl reported libraries',
                             'operating_system_transitive_library_closure_verified': False,
                             'portable_wheel_hash_lock_available': False,
                             'limitations': ['No clean-environment installation/reproduction was executed.',
                                             'Native hashes identify this platform; a portable container/wheel lock is not provided.',
                                             'Version pins do not authenticate upstream packages or dataset provenance.']}}


def dependency_lock_text(environment: dict) -> str:
    """Return a complete installed-version lock, without overwriting any file."""
    _validate_snapshot(environment)
    rows = environment['installed_distributions']
    return '# Exact installed versions; platform/native fingerprint is in environment.json.\n' + ''.join(
        f"{row['canonical_name']}=={row['version']}\n" for row in rows)


def _validate_snapshot(snapshot: dict) -> None:
    try:
        if snapshot['schema_version'] != SCHEMA:
            raise EnvironmentError('Unsupported environment manifest schema')
        if snapshot['inventory_issues'] or snapshot['direct_requirements']['status'] != 'pass':
            raise EnvironmentError('Incomplete dependency/native inventory or missing/mismatched direct dependency pin')
        packages = snapshot['installed_distributions']
        names = [row['canonical_name'] for row in packages]
        if not packages or len(names) != len(set(names)):
            raise EnvironmentError('Missing or duplicate installed dependency metadata')
        for row in packages:
            if not row['name'] or not row['version'] or not row['file_inventory_available']:
                raise EnvironmentError('Incomplete installed dependency metadata')
        installed = {row['canonical_name']: row['version'] for row in packages}
        for row in snapshot['direct_requirements']['checks']:
            if row['status'] != 'match' or row['expected_version'] != installed.get(row['name']) or row['installed_version'] != row['expected_version']:
                raise EnvironmentError('Direct dependency version evidence is inconsistent')
        if not snapshot['direct_requirements']['checks'] or snapshot['direct_requirements']['issues']:
            raise EnvironmentError('Direct dependency pin evidence is missing')
        binary_rows = snapshot['native_distribution_artifacts'] + snapshot['python']['executable_sha256']
        if (not snapshot['python']['full_version'] or not snapshot['operating_system']['system'] or
            not snapshot['native_distribution_artifacts'] or not snapshot['python']['executable_sha256']):
            raise EnvironmentError('Interpreter/operating-system evidence is incomplete')
        for row in binary_rows:
            if row['status'] != 'available' or not isinstance(row['sha256'], str) or not _SHA256.fullmatch(row['sha256']):
                raise EnvironmentError('Missing or corrupt native/interpreter binary hash metadata')
        runtime = snapshot['native_runtime']
        if runtime['status'] != 'available':
            detail=runtime.get('error_type') or runtime.get('error') or 'unreported probe failure'
            raise EnvironmentError(f'Native runtime import evidence is unavailable: {detail}; no completion is permitted')
        for name in _REQUIRED_PROBES:
            row = runtime['modules'].get(name, {})
            if row.get('status') != 'available' or row.get('version_status') != 'reported' or not row.get('reported_version'):
                raise EnvironmentError(f'Required native library availability/version is unverified: {name}')
        for name, row in runtime['modules'].items():
            distribution = 'scikit-learn' if name == 'sklearn' else name
            if (row.get('status') == 'available' and row.get('reported_version') is not None and
                installed.get(distribution) != row['reported_version']):
                raise EnvironmentError(f'Imported library version disagrees with installed metadata: {name}')
        pools = runtime['threadpools']
        if pools['status'] != 'available':
            raise EnvironmentError('threadpoolctl native runtime evidence is unavailable')
        for row in pools['libraries']:
            if row.get('binary_hash_status') != 'available' or not _SHA256.fullmatch(row.get('sha256', '')):
                raise EnvironmentError('Native threadpool library hash is missing or corrupt')
        if snapshot['reproduction']['clean_environment_validated'] is not False:
            raise EnvironmentError('This capture cannot certify a clean-environment reproduction')
    except (KeyError, TypeError, AttributeError) as error:
        raise EnvironmentError('Missing or malformed environment metadata') from error


def validate_environment(expected: dict, current: dict) -> None:
    """Fail closed for incomplete evidence or any exact-environment change."""
    _validate_snapshot(expected)
    _validate_snapshot(current)
    if expected != current:
        changed = sorted(key for key in set(expected) | set(current) if expected.get(key) != current.get(key))
        raise EnvironmentError('Environment fingerprint changed: ' + ', '.join(changed))
