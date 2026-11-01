"""Synthetic Stage 1 lifecycle fixtures; no research observations or algorithms."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from publication_v2 import runner


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        package = self.root / "publication_v2"
        package.mkdir()
        (package / "runner.py").write_text("# synthetic source identity fixture\n", encoding="utf-8")
        for name in runner.REQUIRED_CONFIG:
            value = json.loads(json.dumps(runner.PROTOCOL_CONTRACT)) if name == "experiment_manifest.json" else {}
            (package / name).write_text(json.dumps(value), encoding="utf-8")
        (self.root / "input.csv").write_text("timestamp,value\nsynthetic,1\n", encoding="utf-8")
        (self.root / "model.json").write_text('{"synthetic_identity_fixture":true}', encoding="utf-8")

    def inventory(self, root):
        return {"confirmatory_status": "BLOCKED_CONFIRMATORY_TEST",
            "blockers": [{"code": "NO_UNTOUCHED_DATA", "message": "Synthetic lifecycle fixture only"}],
            "missing_inputs": [], "input_sha256": {"input.csv": runner._digest(root / "input.csv")},
            "model_sha256": {"model.json": runner._digest(root / "model.json")}}

    def create_run(self, run_id="fixture", **kwargs):
        return runner.run_audit(self.root, Path("publication_v2/runs"), run_id,
            audit_fn=kwargs.pop("audit_fn", self.inventory),
            preservation_fn=kwargs.pop("preservation_fn", lambda _: {"status": "pass", "synthetic": True}), **kwargs)

    def test_blocked_audit_completion_never_claims_experiment(self):
        directory = self.create_run()
        manifest = runner.verify_audit_run(directory, root=self.root)
        self.assertEqual(manifest["scientific_status"], "BLOCKED_CONFIRMATORY_TEST")
        self.assertFalse(manifest["experiment_executed"])
        self.assertFalse(manifest["algorithms_implemented"])
        self.assertEqual(manifest["experiment_status"], "NOT_IMPLEMENTED_NO_EVALUATION")
        with self.assertRaises(runner.ScientificBlocker):
            runner.check_confirmatory_preflight(directory, root=self.root)

    def test_existing_run_or_partial_run_not_resumed_or_overwritten(self):
        directory = self.create_run()
        previous = {p.name: p.read_bytes() for p in directory.iterdir()}
        with self.assertRaises(FileExistsError):
            self.create_run()
        self.assertEqual(previous, {p.name: p.read_bytes() for p in directory.iterdir()})
        partial = self.root / "publication_v2/runs/partial"
        partial.mkdir()
        (partial / "STARTED.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.create_run("partial")
        with self.assertRaises(runner.MissingInputError):
            runner.verify_audit_run(partial, root=self.root)

    def test_missing_required_input_has_failure_without_completion(self):
        def missing(root):
            value = self.inventory(root)
            value["missing_inputs"] = ["missing.csv"]
            return value
        with self.assertRaisesRegex(runner.MissingInputError, "missing.csv"):
            self.create_run(audit_fn=missing)
        directory = self.root / "publication_v2/runs/fixture"
        self.assertTrue((directory / "STARTED.json").is_file())
        self.assertTrue((directory / "FAILED.json").is_file())
        self.assertFalse((directory / "COMPLETED.json").exists())

    def test_missing_configuration_never_creates_run(self):
        (self.root / "publication_v2/metadata.json").unlink()
        with self.assertRaises(runner.MissingInputError):
            self.create_run()
        self.assertFalse((self.root / "publication_v2/runs/fixture").exists())

    def test_default_audit_cannot_authenticate_a_different_executed_checkout(self):
        with self.assertRaisesRegex(runner.AuditError, "imported publication_v2 package"):
            runner.run_audit(self.root, Path("publication_v2/runs"), "foreign-source")
        self.assertFalse((self.root / "publication_v2/runs/foreign-source").exists())

    def test_semantically_changed_stage_and_calibration_configuration_refused(self):
        path = self.root / "publication_v2/experiment_manifest.json"
        original = path.read_bytes()
        for key, changed in [("stage", 2), ("stage", True), ("algorithms_implemented", True),
                             ("algorithms_implemented", 0), ("experiment_execution_authorized", True),
                             ("interval_minutes", 60), ("horizons_minutes", [10, 20, 30]),
                             ("calibration_rule", "target_time <= decision_time"),
                             ("feature_rule", "future observations permitted")]:
            with self.subTest(field=key, value=changed):
                value = json.loads(original)
                value[key] = changed
                path.write_text(json.dumps(value), encoding="utf-8")
                try:
                    with self.assertRaisesRegex(runner.AuditError, "protocol contract"):
                        self.create_run("invalid-config")
                finally:
                    path.write_bytes(original)
        self.assertFalse((self.root / "publication_v2/runs/invalid-config").exists())

    def test_default_audit_merges_temporal_hashes_and_rejects_collisions(self):
        script = self.root / "historical_script.py"
        script.write_text("# synthetic historical-input identity\n", encoding="utf-8")
        temporal = {"input_sha256": {"historical_script.py": runner._digest(script)},
                    "new_forecast_or_control_algorithm_executed": False}
        with patch("publication_v2.inventory.build_inventory", side_effect=self.inventory), \
                patch("publication_v2.temporal_audit.audit_temporal_artifacts", return_value=temporal):
            result = runner._default_audit(self.root)
        self.assertEqual(result["input_sha256"]["historical_script.py"], runner._digest(script))
        self.assertIn("input.csv", result["input_sha256"])
        temporal["input_sha256"]["input.csv"] = "0" * 64
        with patch("publication_v2.inventory.build_inventory", side_effect=self.inventory), \
                patch("publication_v2.temporal_audit.audit_temporal_artifacts", return_value=temporal):
            with self.assertRaisesRegex(runner.AuditError, "hash collision"):
                runner._default_audit(self.root)

    def test_marker_schema_and_authenticated_start_stage_consistency_checked(self):
        directory = self.create_run("marker-schema")
        marker_path = directory / "COMPLETED.json"
        marker = json.loads(marker_path.read_text())
        marker["schema_version"] = "wrong.version"
        marker_path.write_text(json.dumps(marker), encoding="utf-8")
        with self.assertRaises(runner.AuditError):
            runner.verify_audit_run(directory, root=self.root)
        directory = self.create_run("start-stage")
        started_path = directory / "STARTED.json"
        started = json.loads(started_path.read_text())
        started["stage"] = 2
        started_path.write_text(json.dumps(started), encoding="utf-8")
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["artifact_sha256"]["STARTED.json"] = runner._digest(started_path)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        marker_path = directory / "COMPLETED.json"
        marker = json.loads(marker_path.read_text())
        marker["manifest_sha256"] = runner._digest(manifest_path)
        marker_path.write_text(json.dumps(marker), encoding="utf-8")
        with self.assertRaisesRegex(runner.AuditError, "same Stage 1 audit run"):
            runner.verify_audit_run(directory, root=self.root)

    def test_interruption_before_atomic_completion_retains_failed_marker(self):
        actual = os.link
        def interrupt(source, destination, *args, **kwargs):
            if Path(destination).name == "COMPLETED.json":
                raise KeyboardInterrupt("synthetic interruption before publication")
            return actual(source, destination, *args, **kwargs)
        with patch.object(runner.os, "link", side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.create_run()
        directory = self.root / "publication_v2/runs/fixture"
        self.assertTrue((directory / "FAILED.json").is_file())
        self.assertFalse((directory / "COMPLETED.json").exists())
        self.assertFalse(list(directory.glob("*.tmp")))

    def test_atomic_publisher_cannot_replace_existing_marker(self):
        directory = self.root / "publication_v2"
        runner._atomic_json(directory, "marker.json", {"original": True})
        previous = (directory / "marker.json").read_bytes()
        with self.assertRaises(FileExistsError):
            runner._atomic_json(directory, "marker.json", {"original": False})
        self.assertEqual(previous, (directory / "marker.json").read_bytes())

    def test_artifact_model_input_and_source_corruption_all_refused(self):
        for index, relative in enumerate(["input.csv", "model.json", "publication_v2/runner.py",
                                           "publication_v2/experiment_manifest.json"]):
            with self.subTest(relative=relative):
                directory = self.create_run(f"corrupt{index}")
                path = self.root / relative
                previous = path.read_bytes()
                path.write_bytes(previous + b" ")
                try:
                    with self.assertRaises(runner.AuditError):
                        runner.verify_audit_run(directory, root=self.root)
                finally:
                    path.write_bytes(previous)
        directory = self.create_run("artifact")
        (directory / "inventory.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(runner.AuditError):
            runner.verify_audit_run(directory, root=self.root)

    def test_expected_manifest_identity_and_environment_checked(self):
        directory = self.create_run()
        with self.assertRaises(runner.AuditError):
            runner.verify_audit_run(directory, root=self.root, expected_manifest_sha256="0" * 64)
        with patch.object(runner, "_environment", return_value={"changed": True}):
            with self.assertRaisesRegex(runner.AuditError, "environment"):
                runner.verify_audit_run(directory, root=self.root)

    def test_preservation_failure_never_completes(self):
        with self.assertRaises(runner.AuditError):
            self.create_run(preservation_fn=lambda _: {"status": "fail"})
        directory = self.root / "publication_v2/runs/fixture"
        self.assertTrue((directory / "FAILED.json").is_file())
        self.assertFalse((directory / "COMPLETED.json").exists())

    def test_configuration_change_during_audit_is_failed(self):
        def change_configuration(root):
            value = self.inventory(root)
            path = root / "publication_v2/metadata.json"
            path.write_bytes(path.read_bytes() + b" ")
            return value
        with self.assertRaisesRegex(runner.AuditError, "configuration changed"):
            self.create_run(audit_fn=change_configuration)
        directory = self.root / "publication_v2/runs/fixture"
        self.assertTrue((directory / "FAILED.json").is_file())
        self.assertFalse((directory / "COMPLETED.json").exists())

    def test_even_hypothetical_future_eligibility_cannot_execute_stage2(self):
        with patch.object(runner, "verify_audit_run", return_value={
                "scientific_status": "HYPOTHETICAL_ELIGIBLE", "blockers": []}):
            with self.assertRaises(runner.Stage2NotImplemented):
                runner.check_confirmatory_preflight(self.root)

    def test_symlink_metadata_rejection_independent_of_creation_privilege(self):
        link = self.root / "publication_v2/runs"
        original = Path.is_symlink
        def reported_symlink(path):
            return path == link or original(path)
        with patch.object(Path, "is_symlink", reported_symlink):
            with self.assertRaisesRegex(runner.AuditError, "Symlink"):
                self.create_run()
        self.assertFalse(link.exists())

    def test_offline_verifier_rejects_symlink_markers_including_dangling_failure(self):
        for index, name in enumerate(["FAILED.json", "COMPLETED.json", "manifest.json", "inventory.json"]):
            with self.subTest(marker=name):
                directory = self.create_run(f"marker{index}")
                target = directory / name
                original = Path.is_symlink
                def reported_symlink(path):
                    return path == target or original(path)
                with patch.object(Path, "is_symlink", reported_symlink):
                    with self.assertRaisesRegex(runner.AuditError, "Symlink"):
                        runner.verify_audit_run(directory, root=self.root)

    def test_windows_junction_output_root_and_ancestor_metadata_rejected(self):
        original = getattr(Path, "is_junction", lambda _: False)
        for junction in [self.root / "publication_v2", self.root / "publication_v2/runs"]:
            with self.subTest(junction=str(junction)):
                def reported_junction(path):
                    return path == junction or original(path)
                with patch.object(Path, "is_junction", reported_junction, create=True):
                    with self.assertRaisesRegex(runner.AuditError, "junction"):
                        self.create_run("junction-output")
        self.assertFalse((self.root / "publication_v2/runs/junction-output").exists())

    def test_windows_junction_markers_artifacts_and_run_ancestors_rejected(self):
        original = getattr(Path, "is_junction", lambda _: False)
        for index, name in enumerate(["COMPLETED.json", "inventory.json", "FAILED.json", ".."]):
            with self.subTest(junction=name):
                directory = self.create_run(f"junction{index}")
                junction = directory.parent if name == ".." else directory / name
                def reported_junction(path):
                    return path == junction or original(path)
                with patch.object(Path, "is_junction", reported_junction, create=True):
                    with self.assertRaisesRegex(runner.AuditError, "junction"):
                        runner.verify_audit_run(directory, root=self.root)

    def test_path_traversal_unsafe_windows_names_and_output_escape_refused(self):
        for run_id in ["../escape", "a/b", "a\\b", "..", "bad.", "NUL", "CON.json"]:
            with self.subTest(run_id=run_id), self.assertRaises(runner.AuditError):
                self.create_run(run_id)
        with self.assertRaises(runner.AuditError):
            runner.run_audit(self.root, self.root / "results", "unsafe", audit_fn=self.inventory)
        self.assertFalse((self.root / "results").exists())

    def test_symlink_output_refused_when_platform_allows_fixture(self):
        outside = self.root / "outside"
        outside.mkdir()
        link = self.root / "publication_v2/runs"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"This Windows account cannot create symlink fixtures: {error}")
        with self.assertRaises(runner.AuditError):
            self.create_run()
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
