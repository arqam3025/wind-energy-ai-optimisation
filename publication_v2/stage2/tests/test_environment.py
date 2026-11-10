"""Environment regressions use synthetic metadata, never research experiments."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from publication_v2.stage2.environment import (SCHEMA, EnvironmentError, _distribution_inventory,
    _native_probe, _requirements, capture_environment, dependency_lock_text, validate_environment)


def snapshot() -> dict:
    names = ('lightgbm', 'numpy', 'scikit-learn', 'scipy', 'xgboost')
    packages = [{'name': name, 'canonical_name': name, 'version': '1.0', 'location': '/synthetic',
                 'file_inventory_available': True} for name in names]
    modules = {('sklearn' if name == 'scikit-learn' else name):
               {'status': 'available', 'reported_version': '1.0', 'version_status': 'reported'} for name in names}
    return {'schema_version': SCHEMA, 'python': {'full_version': 'synthetic',
                'executable_sha256': [{'status': 'available', 'sha256': 'a'*64}]},
            'operating_system': {'system': 'synthetic'}, 'installed_distributions': packages,
            'direct_requirements': {'status': 'pass', 'checks': [{'name': name, 'expected_version': '1.0',
                'installed_version': '1.0', 'status': 'match'} for name in names], 'issues': []},
            'native_distribution_artifacts': [{'status': 'available', 'sha256': 'b'*64}],
            'native_runtime': {'status': 'available', 'modules': modules,
                               'threadpools': {'status': 'available', 'libraries': [{'binary_hash_status': 'available', 'sha256': 'c'*64}]}},
            'inventory_issues': [], 'reproduction': {'clean_environment_validated': False}}


class EnvironmentTests(unittest.TestCase):
    def test_complete_manifest_roundtrips_and_full_lock_has_all_dependencies(self):
        expected = snapshot(); current = json.loads(json.dumps(expected))
        validate_environment(expected, current)
        lines = dependency_lock_text(expected).splitlines()[1:]
        self.assertEqual(lines, [f"{row['canonical_name']}==1.0" for row in expected['installed_distributions']])

    def test_dependency_version_change_rejected_even_when_both_snapshots_valid(self):
        expected = snapshot(); current = deepcopy(expected)
        current['installed_distributions'][1]['version'] = '2.0'
        current['direct_requirements']['checks'][1].update(expected_version='2.0', installed_version='2.0')
        current['native_runtime']['modules']['numpy']['reported_version'] = '2.0'
        with self.assertRaisesRegex(EnvironmentError, 'fingerprint changed'):
            validate_environment(expected, current)

    def test_adding_unpinned_transitive_dependency_also_changes_fingerprint(self):
        expected = snapshot(); current = deepcopy(expected)
        current['installed_distributions'].append({'name': 'other', 'canonical_name': 'other', 'version': '2.0',
                                                  'location': '/synthetic', 'file_inventory_available': True})
        with self.assertRaisesRegex(EnvironmentError, 'fingerprint changed'):
            validate_environment(expected, current)

    def test_changed_native_bytes_rejected(self):
        expected = snapshot(); current = deepcopy(expected)
        current['native_distribution_artifacts'][0]['sha256'] = 'd'*64
        with self.assertRaisesRegex(EnvironmentError, 'fingerprint changed'):
            validate_environment(expected, current)

    def test_corrupt_native_hash_or_unavailable_binary_rejected(self):
        for key, value in (('sha256', 'broken'), ('sha256', None), ('status', 'unavailable')):
            current = snapshot(); current['native_distribution_artifacts'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(EnvironmentError):
                validate_environment(current, current)

    def test_missing_dependency_metadata_and_duplicate_names_rejected(self):
        for mutate in (lambda doc: doc['installed_distributions'].pop(),
                       lambda doc: doc['installed_distributions'].append(deepcopy(doc['installed_distributions'][0])),
                       lambda doc: doc['installed_distributions'][0].update(version=None),
                       lambda doc: doc['installed_distributions'][0].update(file_inventory_available=False)):
            current = snapshot(); mutate(current)
            with self.assertRaises(EnvironmentError): validate_environment(current, current)

    def test_direct_pin_missing_mismatch_and_unsupported_requirements_fail_closed(self):
        packages = snapshot()['installed_distributions']
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'requirements.txt'
            for text in ('absent==1.0', 'numpy==2.0', 'numpy>=1.0', 'numpy==1.0; python_version>"3"',
                         'numpy==1.0\nnumpy==1.0', '# only a comment'):
                path.write_text(text, encoding='utf-8')
                self.assertEqual(_requirements(packages, path)['status'], 'fail')
            path.write_text('numpy==1.0\n', encoding='utf-8')
            self.assertEqual(_requirements(packages, path)['status'], 'pass')

    def test_required_native_import_or_version_missing_is_rejected(self):
        for key, value in (('status', 'unavailable'), ('reported_version', None), ('version_status', 'unavailable')):
            current = snapshot(); current['native_runtime']['modules']['xgboost'][key] = value
            with self.subTest(key=key), self.assertRaises(EnvironmentError): validate_environment(current, current)

    def test_runtime_version_must_match_distribution_version(self):
        current = snapshot(); current['native_runtime']['modules']['xgboost']['reported_version'] = '2.0'
        with self.assertRaisesRegex(EnvironmentError, 'disagrees'): validate_environment(current, current)

    def test_unknown_optional_solver_version_remains_explicit(self):
        current = snapshot()
        current['native_runtime']['modules']['highspy'] = {'status': 'unavailable', 'reported_version': None,
                                                          'version_status': 'unavailable', 'error_type': 'ImportError'}
        validate_environment(current, current)
        self.assertIsNone(current['native_runtime']['modules']['highspy']['reported_version'])

    def test_missing_malformed_or_false_clean_environment_claim_rejected(self):
        for mutate in (lambda doc: doc.pop('operating_system'),
                       lambda doc: doc.update(schema_version='unknown'),
                       lambda doc: doc.update(native_distribution_artifacts=[]),
                       lambda doc: doc['reproduction'].update(clean_environment_validated=True),
                       lambda doc: doc['native_runtime']['threadpools'].update(status='unavailable')):
            current = snapshot(); mutate(current)
            with self.assertRaises(EnvironmentError): validate_environment(current, current)

    def test_native_inventory_reads_actual_bytes_and_detects_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); binary = root/'native.dll'; binary.write_bytes(b'synthetic native bytes')
            dist = SimpleNamespace(metadata={'Name': 'Example_Native'}, version='1.0', files=[Path('native.dll')],
                                   locate_file=lambda relative: root/relative)
            with patch('publication_v2.stage2.environment.metadata.distributions', return_value=[dist]):
                packages, before, issues = _distribution_inventory()
                self.assertEqual(issues, []); self.assertEqual(packages[0]['canonical_name'], 'example-native')
                binary.write_bytes(b'changed native bytes')
                _, after, _ = _distribution_inventory()
                self.assertNotEqual(before[0]['sha256'], after[0]['sha256'])
                binary.unlink()
                _, missing, issues = _distribution_inventory()
                self.assertEqual(missing[0]['status'], 'unavailable'); self.assertTrue(issues)

    def test_missing_file_inventory_and_invalid_distribution_metadata_recorded(self):
        for dist in (SimpleNamespace(metadata={'Name': 'Example'}, version='1.0', files=None, locate_file=lambda _: Path('.')),
                     SimpleNamespace(metadata={}, version='1.0', files=[], locate_file=lambda _: Path('.'))):
            with patch('publication_v2.stage2.environment.metadata.distributions', return_value=[dist]):
                _, _, issues = _distribution_inventory()
                self.assertTrue(issues)

    def test_probe_failure_is_explicit_and_does_not_guess_versions(self):
        with patch('publication_v2.stage2.environment.subprocess.run', side_effect=subprocess.TimeoutExpired('probe', 45)):
            result = _native_probe()
        self.assertEqual(result['status'], 'unavailable'); self.assertEqual(result['modules'], {})
        self.assertEqual(result['error_type'], 'TimeoutExpired')

    def test_capture_is_json_safe_and_documents_unvalidated_clean_environment(self):
        expected = snapshot()
        with patch('publication_v2.stage2.environment._distribution_inventory', return_value=(expected['installed_distributions'], expected['native_distribution_artifacts'], [])), \
             patch('publication_v2.stage2.environment._native_probe', return_value=expected['native_runtime']), \
             patch('publication_v2.stage2.environment._requirements', return_value=expected['direct_requirements']):
            captured = capture_environment()
        validate_environment(captured, json.loads(json.dumps(captured)))
        self.assertEqual(captured['python']['implementation'], 'CPython')
        self.assertIn('compiler', captured['python']); self.assertIn('logical_cpu_count', captured['operating_system'])
        self.assertFalse(captured['reproduction']['clean_environment_validated'])
        self.assertFalse(captured['reproduction']['portable_wheel_hash_lock_available'])


if __name__ == '__main__': unittest.main()
