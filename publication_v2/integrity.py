"""Read-only preservation checks, including all ignored local research outputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

FREEZE_SHA256 = "b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a"
ROOTS = ("data", "models", "results", "scripts", "src", "tests", "docs", "app", ".streamlit",
         "configs", "audits", "documentation_backups", "figures")
NEW_DOCS = {"PUBLICATION_V2_STAGE1_REPORT.md", "PUBLICATION_V2_PROTOCOL.md", "PUBLICATION_V2_STAGE2_PLAN.md"}


class PreservationError(ValueError):
    """A research artifact is missing, changed, or outside the repository."""


def digest(path: Path) -> str:
    try:
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    except OSError as error:
        raise PreservationError(f'Missing/unreadable required input: {path}') from error


def inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or ':' in relative:
        raise PreservationError(f'Invalid repository-relative input: {relative!r}')
    path = Path(relative.replace('\\', '/'))
    if path.is_absolute() or '..' in path.parts:
        raise PreservationError(f'Escaping input: {relative}')
    target = root.resolve() / path
    if not target.resolve().is_relative_to(root.resolve()) or target.is_symlink():
        raise PreservationError(f'Escaping/symlink input: {relative}')
    current = target
    while current != root.resolve() and current != current.parent:
        if current.is_symlink() or getattr(current, 'is_junction', lambda: False)():
            raise PreservationError(f'Symlink/junction input is not accepted: {relative}')
        current = current.parent
    return target


def capture_baseline(root: Path) -> dict:
    """Snapshot pre-existing research; the isolated extension is excluded."""
    paths = set()
    for folder in ROOTS:
        base = root / folder
        if base.exists():
            for path in base.rglob('*'):
                if (path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'
                        and not (folder == 'docs' and path.name in NEW_DOCS)):
                    paths.add(path)
    for path in root.iterdir():
        if path.is_file() and path.suffix.lower() in ('.md', '.txt', '.json', '.toml', '.yml', '.yaml'):
            paths.add(path)
    paths.update(p for p in (root / '.gitignore', root / '.gitattributes') if p.exists())
    files = {p.relative_to(root).as_posix(): digest(inside(root, p.relative_to(root).as_posix()))
             for p in sorted(paths)}
    if not files:
        raise PreservationError('No pre-existing research files to protect')
    return {'schema_version': 1, 'scope': 'All existing local research artifacts; excludes caches and Stage1 extension',
            'files': files, 'protected_files': len(files)}


def verify_preservation(root: Path, baseline: dict) -> dict:
    files = baseline.get('files')
    if not isinstance(files, dict) or not files:
        raise PreservationError('Missing/nonempty preservation mapping required')
    for relative, expected in files.items():
        if not isinstance(expected, str) or len(expected) != 64 or digest(inside(root, relative)) != expected:
            raise PreservationError(f'Protected artifact changed: {relative}')
    return {'status': 'pass', 'protected_files': len(files)}


def verify_frozen(root: Path) -> dict:
    manifest_path = root / 'results/development_controller_freeze_manifest.json'
    if digest(manifest_path) != FREEZE_SHA256:
        raise PreservationError('Frozen manifest hash mismatch')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    entries = list(manifest['source_files'].values())
    entries += [item for group in manifest['development_result_files'].values() for item in group.values()]
    if len(entries) != 59 or len({item['path'] for item in entries}) != 59:
        raise PreservationError('Expected 59 distinct frozen references')
    for entry in entries:
        if digest(inside(root, entry['path'])) != entry['sha256']:
            raise PreservationError(f'Frozen reference changed: {entry["path"]}')
    return {'status': 'pass', 'manifest_sha256': FREEZE_SHA256, 'references': len(entries)}


def verify_repository(root: Path) -> dict:
    path = root / 'publication_v2/preservation_baseline.json'
    try:
        baseline = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise PreservationError(f'Missing/invalid preservation baseline: {path}') from error
    return {'status': 'pass', 'preservation': verify_preservation(root, baseline), 'freeze': verify_frozen(root)}
