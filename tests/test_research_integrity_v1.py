"""Synthetic integrity fixtures; no research artifact is edited by these tests."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from windresearch.integrity import (IntegrityError, checked_relative_path,
    verify_frozen_manifest, verify_hash_mapping, verify_protected_baseline)

spec = importlib.util.spec_from_file_location("_research_final_verifier", ROOT / "scripts/verify_research_grade_v1.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(directory: Path) -> tuple[Path, str]:
    (directory / "scripts").mkdir()
    (directory / "results").mkdir()
    source = directory / "scripts/controller.py"
    result = directory / "results/development.csv"
    source.write_text("unchanged scientific source\n", encoding="utf-8")
    result.write_text("power_kw\n1.0\n", encoding="utf-8")
    manifest = {"source_files": {"controller": {"path": "scripts/controller.py", "sha256": digest(source)}},
        "development_result_files": {"case": {"1": {"path": "results/development.csv", "sha256": digest(result)}}}}
    path = directory / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path, digest(path)


class ResearchIntegrityTests(unittest.TestCase):
    def test_valid_fixture_then_corrupt_reference_rejected_under_optimized_python(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, expected = fixture(root)
            verify_frozen_manifest(root, "manifest.json", expected)
            (root / "scripts/controller.py").write_text("corrupted\n", encoding="utf-8")
            # An actual -O interpreter is necessary: a unit-level assertion
            # cannot demonstrate that production checks survive optimization.
            program = ("import sys; from pathlib import Path; "
                "sys.path.insert(0,sys.argv[1]); "
                "from windresearch.integrity import verify_frozen_manifest; "
                "verify_frozen_manifest(Path(sys.argv[2]),'manifest.json',sys.argv[3])")
            completed = subprocess.run([sys.executable, "-O", "-c", program,
                str(ROOT / "src"), str(root), expected], capture_output=True, text=True, check=False)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("SHA256 mismatch for scripts/controller.py", completed.stderr)
            self.assertEqual((root / "scripts/controller.py").read_text(), "corrupted\n")

    def test_manifest_changed_and_reference_missing_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, expected = fixture(root)
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with self.assertRaisesRegex(IntegrityError, "manifest SHA256 mismatch"):
                verify_frozen_manifest(root, "manifest.json", expected)
            path.write_bytes(original)
            (root / "results/development.csv").unlink()
            with self.assertRaisesRegex(IntegrityError, "Cannot read integrity artifact"):
                verify_frozen_manifest(root, "manifest.json", expected)

    def test_malformed_authenticated_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "manifest.json"
            path.write_text('{"source_files":{},"development_result_files":{}}')
            with self.assertRaisesRegex(IntegrityError, "Malformed frozen manifest"):
                verify_frozen_manifest(root, "manifest.json", digest(path))

    def test_path_traversal_and_normalized_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("../outside.txt", "/outside.txt", "C:\\outside.txt", "\\\\host\\share\\file"):
                with self.assertRaises(IntegrityError):
                    checked_relative_path(root, name)
            (root / "nested").mkdir()
            artifact = root / "nested/file.txt"
            artifact.write_text("preserve")
            with self.assertRaisesRegex(IntegrityError, "Duplicate normalized"):
                verify_hash_mapping(root, {"nested/file.txt": digest(artifact), "nested\\file.txt": digest(artifact)})

    def test_windows_baseline_paths_work_and_changes_are_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fixture(root)
            source = root / "scripts/controller.py"
            baseline = root / "baseline.json"
            baseline.write_text(json.dumps({"scripts\\controller.py": digest(source)}))
            result = verify_protected_baseline(root, baseline)
            self.assertEqual(result["checked_files"], 1)
            source.write_text("changed")
            with self.assertRaisesRegex(IntegrityError, "SHA256 mismatch"):
                verify_protected_baseline(root, baseline)

    def test_saved_trace_ramps_soc_and_metrics_are_independently_reconstructed(self):
        times = pd.date_range("2020-01-01", periods=2, freq="10min")
        config = {"dt_hours": 1 / 6, "eta_charge": .95, "eta_discharge": .95,
            "capacity_kwh": 2000., "min_soc_percent": 40., "max_soc_percent": 90.,
            "initial_soc_percent": 50., "max_power_kw": 1000., "ramp_limit_kw": 200.,
            "primary_enabled": True, "primary_tolerance": 100.}
        source = pd.DataFrame({"timestamp": times, "current_power_kw": [900., 1000.], "actual_h1_kw": [1000., 1300.]})
        trace = pd.DataFrame({"decision_timestamp": times, "timestamp": times + pd.Timedelta(minutes=10),
            "wind_generation_kw": [1000., 1300.], "grid_export_kw": [1000., 1300.],
            "charge_kw": 0., "discharge_kw": 0., "curtailment_kw": 0., "energy_kwh": 1000.,
            "initial_energy_kwh": 1000., "soc_percent": 50., "grid_ramp_kw": [100., 300.],
            "ramp_exceedance_kw": [0., 100.], "ramp_violation": [0, 1],
            "reference_200kw_exceedance_kw": [0., 100.], "reference_200kw_violation": [0, 1],
            "committed_charge_kw": 0., "committed_discharge_kw": 0., "committed_curtailment_kw": 0.,
            "stage1_status": "optimal", "stage2_status": "optimal", "stage1_objective": 0.,
            "stage2_objective": 0., "achieved_primary_objective": 0., "max_constraint_residual": 0.})
        zero = ["charge_energy_kwh", "discharge_energy_kwh", "throughput_kwh", "conversion_losses_kwh",
                "curtailment_kwh", "energy_conservation_residual_kwh", "soc_violations",
                "terminal_inventory_change_kwh", "equivalent_full_cycle_proxy", "solver_failures"]
        metric = pd.Series({**dict.fromkeys(zero, 0.), "ramp_violations": 1, "total_ramp_exceedance_kw": 100.,
            "mean_grid_ramp_kw": 200., "max_grid_ramp_kw": 300., "reference_200kw_violations": 1,
            "reference_200kw_exceedance_kw": 100., "actual_export_kwh": 2300 / 6,
            "hypothetical_terminal_adjusted_export_kwh": 2300 / 6, "final_soc_percent": 50.,
            "min_soc_percent": 50., "max_soc_percent": 50., "intervals": 2})
        report = verifier.verify_trace(trace, source, config, "xgboost_nominal", metric)
        self.assertEqual(report["intervals"], 2)
        for column, replacement, message in [("grid_ramp_kw", 0., "grid ramp"),
                ("ramp_violation", 0, "violation count"), ("soc_percent", 49., "SOC percentage")]:
            corrupted = trace.copy()
            corrupted.loc[1, column] = replacement
            with self.assertRaisesRegex(IntegrityError, message):
                verifier.verify_trace(corrupted, source, config, "xgboost_nominal", metric)
        wrong_metric = metric.copy()
        wrong_metric["total_ramp_exceedance_kw"] = 0.
        with self.assertRaisesRegex(IntegrityError, "block metric total_ramp_exceedance"):
            verifier.verify_trace(trace, source, config, "xgboost_nominal", wrong_metric)

    def test_final_report_refuses_existing_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "existing.json"
            output.write_text("preserve report")
            completed = subprocess.run([sys.executable, str(ROOT / "scripts/verify_research_grade_v1.py"),
                "--output", str(output)], capture_output=True, text=True, check=False)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("Refusing existing verification report", completed.stderr)
            self.assertEqual(output.read_text(), "preserve report")

    def test_future_planning_overlap_uses_kw_tolerance_independent_of_active_power(self):
        # 0.4 W in the inactive channel is below the predeclared 1 W solver
        # constraint tolerance, whether the active channel is 1 or 1,000 kW.
        # The old kW-squared product would falsely depend on that magnitude.
        for active_power in (1., 100., 1000.):
            self.assertAlmostEqual(verifier.planning_overlap_kw([active_power], [.0004]), .0004)
            self.assertAlmostEqual(verifier.planning_overlap_kw([.0004], [active_power]), .0004)
            with self.assertRaisesRegex(IntegrityError, "overlap.*exceeds"):
                verifier.planning_overlap_kw([active_power], [.002])
        self.assertEqual(verifier.planning_overlap_kw([0.], [1000.]), 0.)


if __name__ == "__main__":
    unittest.main()
