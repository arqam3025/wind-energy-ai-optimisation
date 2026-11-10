"""Fail-closed Stage 1 audit scaffold; no forecasting or control is executed.

An atomic ``COMPLETED.json`` means that an inventory/preservation audit finished,
not that an experiment or independent evaluation succeeded. Missing or changed
inputs fail the audit. Unknown scientific provenance remains an explicit blocker.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path, PureWindowsPath
import platform
import re
import sys
import tempfile
from typing import Any, Callable
import uuid

SCHEMA = "publication_v2.stage1.audit.v1"
CONFIG_SCHEMA = "publication_v2.protocol.v1"
REQUIRED_CONFIG = ("experiment_manifest.json", "metadata.json", "preservation_baseline.json")
PROTOCOL_CONTRACT = {
    "schema_version": CONFIG_SCHEMA, "stage": 1,
    "algorithms_implemented": False, "experiment_execution_authorized": False,
    "interval_minutes": 10, "horizons_minutes": [10, 20, 30, 40, 50, 60],
    "calibration_rule": "target_time < decision_time AND observation_available_at <= residual_available_at <= decision_time",
    "feature_rule": "source_time <= available_at <= origin_time <= issued_at <= decision_time",
    "forecast_rule": "origin_time <= issued_at <= decision_time < target_time = origin_time + horizon",
    "training_rule": "model_latest_training_target < forecast_origin AND model_available_at <= issued_at",
    "embargo_rule": "Every earlier-role target at each horizon must be strictly before the next role's first decision; equal-time targets rejected",
    "cross_split_rule": "No shared target timestamp across roles, including different horizons",
    "missing_data_policy": "Reject missing required records/values, duplicates or undeclared cadence gaps; never impute silently",
    "timezone_policy": "Require attested event-time/availability semantics and offset-aware timestamps for eligibility; naive historical clocks are audited structurally without invented timezone",
}


class AuditError(RuntimeError):
    """The Stage 1 audit or its authenticated evidence is incomplete."""


class MissingInputError(AuditError):
    """A required input is absent; no completion marker may be issued."""


class ScientificBlocker(AuditError):
    """The audit finished, but independent evaluation is scientifically blocked."""


class Stage2NotImplemented(AuditError):
    """Stage 1 never runs an algorithm, even if future prerequisites are met."""


def _digest(path: Path) -> str:
    if not path.is_file():
        raise MissingInputError(f"Required regular input file is missing: {path}")
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise MissingInputError(f"Required JSON input is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise AuditError(f"Invalid JSON input: {path}") from error
    if not isinstance(value, dict):
        raise AuditError(f"Expected a JSON object: {path}")
    return value


def _redirects_namespace(path: Path) -> bool:
    """Windows directory junctions redirect paths without being symlinks."""
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


def _reject_redirect_ancestors(path: Path) -> None:
    """Check the target and every lexical ancestor before reading or creating."""
    for current in (path, *path.parents):
        if _redirects_namespace(current):
            raise AuditError(f"Symlink/junction artifact namespace is not accepted: {current}")


def _within(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or PureWindowsPath(relative).drive:
        raise AuditError(f"Expected a repository-relative path: {relative!r}")
    path = Path(relative.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise AuditError(f"Escaping artifact path: {relative!r}")
    target = root / path
    if not target.resolve().is_relative_to(root.resolve()):
        raise AuditError(f"Artifact resolves outside the repository: {relative!r}")
    _reject_redirect_ancestors(target)
    return target


def _verify_mapping(root: Path, mapping: Any, label: str) -> None:
    if not isinstance(mapping, dict) or not mapping:
        raise AuditError(f"Missing or malformed {label} hash mapping")
    for relative, expected in mapping.items():
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise AuditError(f"Invalid {label} digest for {relative!r}")
        if _digest(_within(root, relative)) != expected:
            raise AuditError(f"Changed {label}: {relative}")


def _environment() -> dict[str, Any]:
    """Record installed distributions without importing models or invoking pip."""
    packages = sorted((dist.metadata["Name"], dist.version) for dist in metadata.distributions()
                      if dist.metadata.get("Name"))
    return {"python_version": platform.python_version(),
            "implementation": platform.python_implementation(), "platform": platform.platform(),
            "installed_distributions": [list(item) for item in packages],
            "clean_environment_reproduction": "not_performed_by_stage1_runner"}


def _source_hashes(root: Path) -> dict[str, str]:
    package = root / "publication_v2"
    for name in REQUIRED_CONFIG:
        _digest(_within(root, f"publication_v2/{name}"))
    config = _json(package / "experiment_manifest.json")
    for key, expected in PROTOCOL_CONTRACT.items():
        actual = config.get(key)
        if type(actual) is not type(expected) or actual != expected:
            raise AuditError(f"Stage 1 experiment manifest violates the fixed protocol contract: {key}")
        if isinstance(expected, list) and any(type(item) is not int for item in actual):
            raise AuditError(f"Stage 1 experiment manifest requires integer {key}")
    cohort = config.get("cohort")
    if cohort is not None and (not isinstance(cohort, dict)
            or cohort.get("historical_49_blocks") != "retrospective_exposed"
            or cohort.get("scheduled_block_6") != "development_excluded_from_evaluation"
            or cohort.get("confirmatory_status") != "BLOCKED_CONFIRMATORY_TEST"
            or cohort.get("proposed_untouched_split") is not None):
        raise AuditError("Stage 1 cannot reclassify the historical cohort or declare an untouched split")
    paths = sorted(set(package.glob("*.py")) | {package / name for name in REQUIRED_CONFIG})
    if not any(path.suffix == ".py" for path in paths):
        raise MissingInputError("No Stage 1 source files available to authenticate")
    return {path.relative_to(root).as_posix(): _digest(_within(root, path.relative_to(root).as_posix()))
            for path in paths}


def _atomic_json(directory: Path, name: str, value: dict[str, Any]) -> None:
    """Fsync a private temporary file, then publish by an exclusive atomic link.

    A hard link never replaces an existing destination. Filesystems without
    same-directory hard-link support fail closed; there is no overwrite fallback.
    Only the temporary file created by this invocation is removed.
    """
    if Path(name).name != name or not name.endswith(".json"):
        raise AuditError("Internal marker filename must be a plain JSON filename")
    _reject_redirect_ancestors(directory)
    destination = _within(directory, name)
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=directory, prefix=f".{name}.",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _run_directory(root: Path, output_root: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", run_id) or run_id.endswith("."):
        raise AuditError("run-id must be 1–64 safe characters and cannot end with a period")
    stem = run_id.split(".", 1)[0].upper()
    if stem in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                 *(f"LPT{i}" for i in range(1, 10))}:
        raise AuditError("Windows reserved names cannot be run IDs")
    intended = root / "publication_v2" / "runs"
    output = output_root if output_root.is_absolute() else root / output_root
    relative = output.relative_to(root) if output.is_relative_to(root) else None
    if relative is None or not output.resolve().is_relative_to(intended.resolve()):
        raise AuditError("Outputs must stay inside publication_v2/runs")
    _within(root, relative.as_posix())
    output.mkdir(parents=True, exist_ok=True)
    target = output / run_id
    _reject_redirect_ancestors(target)
    target.mkdir(exist_ok=False)
    return target


def _default_audit(root: Path) -> dict[str, Any]:
    from .inventory import build_inventory
    from .temporal_audit import audit_temporal_artifacts
    inventory = build_inventory(root)
    if inventory.get("missing_inputs"):
        raise MissingInputError(f"Missing required inventory inputs: {inventory['missing_inputs']}")
    temporal = audit_temporal_artifacts(root)
    if not isinstance(temporal, dict) or temporal.get("new_forecast_or_control_algorithm_executed") is not False:
        raise AuditError("Temporal audit must explicitly certify that no new forecast/control algorithm was executed")
    base_hashes, temporal_hashes = inventory.get("input_sha256"), temporal.get("input_sha256")
    if not isinstance(base_hashes, dict) or not isinstance(temporal_hashes, dict) or not temporal_hashes:
        raise MissingInputError("Inventory and temporal audit must identify all input hashes")
    merged = dict(base_hashes)
    for relative, digest in temporal_hashes.items():
        if relative in merged and merged[relative] != digest:
            raise AuditError(f"Inventory/temporal input hash collision: {relative}")
        merged[relative] = digest
    inventory["input_sha256"] = merged
    inventory["temporal_verification"] = temporal
    return inventory


def _default_preservation(root: Path) -> dict[str, Any]:
    from .integrity import verify_repository
    return verify_repository(root)


def run_audit(root: Path, output_root: Path, run_id: str, *,
              audit_fn: Callable[[Path], dict[str, Any]] | None = None,
              preservation_fn: Callable[[Path], dict[str, Any]] | None = None) -> Path:
    """Finish only the Stage 1 audit; scientific blockers are never success claims."""
    root = Path(root).resolve()
    imported_root = Path(__file__).resolve().parents[1]
    if audit_fn is None and root != imported_root:
        raise AuditError("The default audit must run from the root of the imported publication_v2 package; invoke the other checkout's own module instead")
    sources = _source_hashes(root)  # Missing configuration never creates a run directory.
    environment = _environment()
    directory = _run_directory(root, Path(output_root), run_id)
    preserve = preservation_fn or _default_preservation
    started = {"schema_version": SCHEMA, "stage": 1, "run_id": run_id,
        "execution_id": str(uuid.uuid4()), "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "inventory_and_protocol_audit_only", "experiment_executed": False}
    completion_published = False
    try:
        _atomic_json(directory, "STARTED.json", started)
        before = preserve(root)
        if before.get("status") != "pass":
            raise AuditError("Pre-audit preservation verification did not pass")
        _atomic_json(directory, "preservation_before.json", before)
        inventory = (audit_fn or _default_audit)(root)
        if not isinstance(inventory, dict) or inventory.get("missing_inputs"):
            raise MissingInputError(f"Missing required audit inputs: {inventory.get('missing_inputs') if isinstance(inventory, dict) else 'malformed inventory'}")
        if inventory.get("confirmatory_status") != "BLOCKED_CONFIRMATORY_TEST":
            raise AuditError("Stage 1 requires an explicitly reviewed confirmatory classification; this scaffold cannot certify a new untouched cohort")
        if not isinstance(inventory.get("blockers"), list) or not inventory["blockers"]:
            raise AuditError("Blocked confirmatory classification requires explicit blocker evidence")
        _verify_mapping(root, inventory.get("input_sha256"), "input")
        _verify_mapping(root, inventory.get("model_sha256"), "model")
        _atomic_json(directory, "inventory.json", inventory)
        after = preserve(root)
        if after.get("status") != "pass":
            raise AuditError("Post-audit preservation verification did not pass")
        _atomic_json(directory, "preservation_after.json", after)
        if sources != _source_hashes(root):
            raise AuditError("Stage 1 code or configuration changed while the audit was running")
        if environment != _environment():
            raise AuditError("Runtime environment changed while the audit was running")
        artifacts = {name: _digest(directory / name) for name in
            ("STARTED.json", "preservation_before.json", "inventory.json", "preservation_after.json")}
        manifest = {"schema_version": SCHEMA, "run_id": run_id, "stage": 1,
            "audit_status": "AUDIT_COMPLETED", "scientific_status": "BLOCKED_CONFIRMATORY_TEST",
            "experiment_status": "NOT_IMPLEMENTED_NO_EVALUATION", "experiment_executed": False,
            "algorithms_implemented": False, "blockers": inventory["blockers"],
            "repository_root_at_audit": str(root), "environment": environment,
            "audit_provider": "default_repository_audit" if audit_fn is None else "injected_test_or_internal_audit",
            "source_sha256": sources, "input_sha256": inventory["input_sha256"],
            "model_sha256": inventory["model_sha256"], "artifact_sha256": artifacts,
            "completed_utc": datetime.now(timezone.utc).isoformat()}
        _atomic_json(directory, "manifest.json", manifest)
        _atomic_json(directory, "COMPLETED.json", {"schema_version": SCHEMA,
            "run_id": run_id,
            "audit_status": "AUDIT_COMPLETED", "scientific_status": manifest["scientific_status"],
            "experiment_executed": False, "manifest_sha256": _digest(directory / "manifest.json")})
        completion_published = True
        return directory
    except BaseException as error:
        if not completion_published:
            try:
                _atomic_json(directory, "FAILED.json", {"schema_version": SCHEMA,
                    "audit_status": "AUDIT_FAILED", "experiment_executed": False,
                    "error_type": type(error).__name__, "message": str(error)})
            except (OSError, AuditError, ValueError):
                pass  # STARTED/the exclusive run path remain; no completion is fabricated.
        raise


def verify_audit_run(directory: Path, *, root: Path | None = None,
                     expected_manifest_sha256: str | None = None) -> dict[str, Any]:
    """Authenticate an audit before consumption; partial/stale evidence is refused."""
    directory = Path(directory).absolute()
    _reject_redirect_ancestors(directory)
    if not directory.is_dir():
        raise AuditError("Run is missing, symlinked, partial, or explicitly failed")
    # A dangling FAILED marker must not disappear merely because exists() is false.
    # Authenticate path type before reading any completion/manifest/artifact bytes.
    for name in ("FAILED.json", "COMPLETED.json", "manifest.json", "STARTED.json",
                 "preservation_before.json", "inventory.json", "preservation_after.json"):
        _within(directory, name)
    if (directory / "FAILED.json").exists():
        raise AuditError("Run is explicitly failed")
    marker = _json(directory / "COMPLETED.json")
    manifest_hash = _digest(directory / "manifest.json")
    if marker.get("manifest_sha256") != manifest_hash or (
            expected_manifest_sha256 is not None and expected_manifest_sha256 != manifest_hash):
        raise AuditError("Manifest digest does not match the completion marker or expected identity")
    manifest = _json(directory / "manifest.json")
    if (manifest.get("schema_version") != SCHEMA or marker.get("schema_version") != SCHEMA
            or manifest.get("audit_status") != "AUDIT_COMPLETED"
            or type(manifest.get("stage")) is not int or manifest["stage"] != 1
            or manifest.get("experiment_executed") is not False
            or manifest.get("algorithms_implemented") is not False
            or manifest.get("experiment_status") != "NOT_IMPLEMENTED_NO_EVALUATION"
            or marker.get("experiment_executed") is not False
            or marker.get("audit_status") != "AUDIT_COMPLETED"
            or marker.get("scientific_status") != manifest.get("scientific_status")):
        raise AuditError("Audit marker/manifest scope is inconsistent or claims experiment execution")
    expected_artifacts = {"STARTED.json", "preservation_before.json", "inventory.json", "preservation_after.json"}
    if set(manifest.get("artifact_sha256", {})) != expected_artifacts:
        raise AuditError("Audit artifact scope is incomplete")
    _verify_mapping(directory, manifest["artifact_sha256"], "audit artifact")
    started = _json(directory / "STARTED.json")
    if (started.get("schema_version") != SCHEMA
            or type(started.get("stage")) is not int or started["stage"] != 1
            or started.get("experiment_executed") is not False
            or started.get("run_id") != manifest.get("run_id")
            or marker.get("run_id") != manifest.get("run_id")
            or manifest.get("run_id") != directory.name):
        raise AuditError("STARTED/completion markers do not identify the same Stage 1 audit run")
    inventory = _json(directory / "inventory.json")
    if (manifest.get("scientific_status") != inventory.get("confirmatory_status")
            or manifest.get("blockers") != inventory.get("blockers")
            or manifest.get("input_sha256") != inventory.get("input_sha256")
            or manifest.get("model_sha256") != inventory.get("model_sha256")):
        raise AuditError("Manifest scientific scope or input identities differ from the inventory")
    repository = Path(root).resolve() if root is not None else Path(manifest["repository_root_at_audit"]).resolve()
    expected_output_root = repository / "publication_v2" / "runs"
    if not directory.resolve().is_relative_to(expected_output_root.resolve()):
        raise AuditError("Run is outside the versioned publication_v2/runs scope")
    _within(repository, directory.relative_to(repository).as_posix())
    _verify_mapping(repository, manifest.get("source_sha256"), "source/configuration")
    if manifest["source_sha256"] != _source_hashes(repository):
        raise AuditError("Stage 1 authenticated source/configuration scope changed")
    _verify_mapping(repository, manifest.get("input_sha256"), "input")
    _verify_mapping(repository, manifest.get("model_sha256"), "model")
    if manifest.get("environment") != _environment():
        raise AuditError("Current environment differs from the recorded audit environment")
    return manifest


def check_confirmatory_preflight(directory: Path, *, root: Path | None = None) -> None:
    manifest = verify_audit_run(directory, root=root)
    if manifest.get("scientific_status") == "BLOCKED_CONFIRMATORY_TEST" or manifest.get("blockers"):
        codes = [str(item.get("code", item)) if isinstance(item, dict) else str(item)
                 for item in manifest.get("blockers", [])]
        raise ScientificBlocker("BLOCKED_CONFIRMATORY_TEST: " + "; ".join(codes))
    raise Stage2NotImplemented("Stage 2 algorithms/evaluation are not implemented or permitted by Stage 1")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit", help="Inventory/preservation only; no experiment execution")
    audit.add_argument("--run-id", required=True)
    audit.add_argument("--output-root", type=Path, default=Path("publication_v2/runs"))
    preflight = subparsers.add_parser("preflight", help="Verify saved audit and report scientific blockers")
    preflight.add_argument("--run", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "audit":
            directory = run_audit(args.root, args.output_root, args.run_id)
            print(json.dumps({"audit_status": "AUDIT_COMPLETED", "scientific_status": "BLOCKED_CONFIRMATORY_TEST",
                              "experiment_executed": False, "run_directory": str(directory)}))
        else:
            check_confirmatory_preflight(args.run, root=args.root)
    except ScientificBlocker as error:
        print(json.dumps({"status": "BLOCKED_CONFIRMATORY_TEST", "error": str(error)}), file=sys.stderr)
        return 2
    except Exception as error:
        print(json.dumps({"status": "AUDIT_FAILED", "error_type": type(error).__name__, "error": str(error)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
