"""Byte-level research integrity checks that remain active under ``python -O``.

No frozen program is imported, no model is fitted and no checked file is written.
An authenticated manifest proves byte identity, not the truth of scientific
declarations recorded inside that manifest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
from typing import Any

EXPECTED_FREEZE_SHA256 = "b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a"
DEFAULT_MANIFEST = "results/development_controller_freeze_manifest.json"


class IntegrityError(RuntimeError):
    """A missing, malformed, escaping or changed research artifact."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise IntegrityError(f"Cannot read integrity artifact: {path}") from error
    return digest.hexdigest()


def checked_relative_path(root: Path, relative: str) -> Path:
    """Accept portable repository-relative paths, rejecting traversal/symlinks."""
    if not isinstance(relative, str) or not relative or PureWindowsPath(relative).drive:
        raise IntegrityError(f"Expected a repository-relative artifact path: {relative!r}")
    normalized = Path(relative.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise IntegrityError(f"Artifact path escapes repository: {relative!r}")
    repository = Path(root).resolve()
    target = (repository / normalized).resolve()
    if not target.is_relative_to(repository) or target == repository:
        raise IntegrityError(f"Artifact path escapes repository: {relative!r}")
    return target


def _expected_digest(value: Any, context: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise IntegrityError(f"Invalid SHA256 for {context}")
    return value


def verify_hash_mapping(root: Path, entries: dict[str, str]) -> dict[str, Any]:
    """Verify every path/hash pair explicitly, including Windows-authored paths."""
    if not isinstance(entries, dict) or not entries:
        raise IntegrityError("Integrity mapping must contain at least one artifact")
    resolved: set[Path] = set()
    for relative, expected in entries.items():
        target = checked_relative_path(root, relative)
        if target in resolved:
            raise IntegrityError(f"Duplicate normalized artifact path: {relative}")
        resolved.add(target)
        expected = _expected_digest(expected, relative)
        actual = sha256(target)
        if actual != expected:
            raise IntegrityError(f"SHA256 mismatch for {relative}: expected {expected}, found {actual}")
    return {"status": "pass", "checked_files": len(entries)}


def verify_frozen_manifest(
    root: Path | None = None,
    manifest_path: str = DEFAULT_MANIFEST,
    expected_sha256: str = EXPECTED_FREEZE_SHA256,
) -> dict[str, Any]:
    """Authenticate the manifest and every frozen source/development reference.

    Optional root/path/digest arguments permit isolated corruption fixtures.
    Production callers should retain the default expected digest. The returned
    object is the original manifest schema, compatible with existing readers.
    """
    repository = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    path = checked_relative_path(repository, manifest_path)
    expected_sha256 = _expected_digest(expected_sha256, "manifest")
    actual = sha256(path)
    if actual != expected_sha256:
        raise IntegrityError(f"Frozen manifest SHA256 mismatch: expected {expected_sha256}, found {actual}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        sources = manifest["source_files"]
        groups = manifest["development_result_files"]
        if not isinstance(sources, dict) or not sources or not isinstance(groups, dict) or not groups:
            raise ValueError("Missing frozen source/development mappings")
        references = list(sources.values())
        for group in groups.values():
            if not isinstance(group, dict) or not group:
                raise ValueError("Empty/malformed frozen development group")
            references.extend(group.values())
        entries: dict[str, str] = {}
        for entry in references:
            if not isinstance(entry, dict) or set(("path", "sha256")) - entry.keys():
                raise ValueError("Malformed frozen reference")
            if entry["path"] in entries:
                raise ValueError(f"Duplicate frozen reference: {entry['path']}")
            entries[entry["path"]] = entry["sha256"]
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as error:
        raise IntegrityError(f"Malformed frozen manifest: {path}") from error
    verify_hash_mapping(repository, entries)
    return manifest


def verify_protected_baseline(root: Path, baseline_path: Path) -> dict[str, Any]:
    """Check the task's separate pre-change inventory without changing it."""
    try:
        entries = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise IntegrityError(f"Cannot load protected baseline: {baseline_path}") from error
    result = verify_hash_mapping(root, entries)
    result["baseline_sha256"] = sha256(baseline_path)
    return result
