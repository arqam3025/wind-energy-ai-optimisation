"""Small synthetic inventory fixtures; never research performance evidence."""
import json
from pathlib import Path
import tempfile
import unittest

from publication_v2.inventory import boundary_findings, build_inventory, parse_dataset_time, profile_csv


class InventoryTests(unittest.TestCase):
    def test_naive_timestamp_not_relabelled_utc(self):
        self.assertIsNone(parse_dataset_time('01 01 2018 00:00').tzinfo)
        self.assertIsNone(parse_dataset_time('2018-01-01 00:00:00').tzinfo)

    def test_duplicate_missing_and_gap_structure_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'example.csv'
            path.write_text('timestamp,actual_h6_kw\n2018-01-01 00:00:00,1\n2018-01-01 00:00:00,2\n2018-01-01 00:30:00,\n,4\n')
            profile = profile_csv(path, root)
            self.assertEqual(profile['duplicated_timestamps'], 1)
            self.assertEqual(profile['missing_ten_minute_slots'], 2)
            self.assertEqual(len(profile['timestamp_errors']), 1)
            self.assertEqual(profile['missing_cells'], 2)
            self.assertEqual(profile['latest_inferred_target_timestamp'], '2018-01-01 01:30:00')
            self.assertEqual(profile['clock_status'], 'UNKNOWN_TIMEZONE')

    def test_nonfinite_cells_reported_and_mixed_clocks_not_sorted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'numeric.csv'
            path.write_text('timestamp,power_kw\n2018-01-01 00:00:00,NaN\n')
            self.assertEqual(profile_csv(path, root)['nonfinite_numeric_cells'], [{'csv_line': 2, 'column': 'power_kw'}])
            path.write_text('timestamp,power_kw\n2018-01-01 00:00:00,1\n2018-01-01T00:10:00+00:00,2\n')
            self.assertEqual(profile_csv(path, root)['status'], 'MIXED_CLOCK_ENCODING')

    def test_equal_target_static_calibration_fails_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'results').mkdir()
            dev = root / 'data/processed/controller_development_blocks'
            dev.mkdir(parents=True)
            (root / 'results/multistep_calibration_split.csv').write_text('timestamp\n2018-01-01 00:00:00\n')
            (dev / 'development_block_1.csv').write_text('timestamp\n2018-01-01 00:10:00\n2018-01-01 00:20:00\n')
            result = boundary_findings(root)['calibration_development']
            self.assertFalse(result['strict_target_time_before_decision'])
            self.assertEqual(result['by_horizon'][0]['unavailable_at_first_development_decision'], 1)

    def test_cross_horizon_role_overlap_includes_schedule_development(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'results').mkdir()
            data = root / 'data/processed'
            data.mkdir(parents=True)
            (root / 'results/evaluation_schedule.csv').write_text('block_id,evaluation_role\n6,development\n7,evaluation\n')
            (data / 'evaluation_block_6.csv').write_text('timestamp\n2018-01-01 00:00:00\n')
            (data / 'evaluation_block_7.csv').write_text('timestamp\n2018-01-01 00:10:00\n')
            result = boundary_findings(root)['scheduled_role_overlap']
            self.assertEqual(result['development_blocks'], [6])
            self.assertEqual(result['unique_shared_target_times'], 5)
            self.assertEqual(result['overlapping_scored_h1_times'], 1)
            self.assertEqual(result['overlapping_horizon_target_pairs'], 5)

    def test_empty_missing_bundle_never_becomes_an_untouched_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = build_inventory(root)
            self.assertEqual(result['confirmatory_status'], 'BLOCKED_CONFIRMATORY_TEST')
            self.assertIsNone(result['confirmatory_test']['proposed_split'])
            self.assertTrue(result['missing_inputs'])
            self.assertIn('MISSING_REQUIRED_INPUTS', [b['code'] for b in result['blockers']])
            self.assertIsNone(result['provenance']['dataset']['timezone']['value'])
            self.assertIsNone(result['provenance']['dataset']['upstream_dataset_version']['value'])
            json.dumps(result, allow_nan=False)

    def test_full_declared_development_tail_also_counts_for_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'results').mkdir()
            data = root / 'data/processed'
            data.mkdir(parents=True)
            (root / 'results/evaluation_schedule.csv').write_text('block_id,evaluation_role\n1,evaluation\n')
            (root / 'results/multistep_controller_development_split.csv').write_text('timestamp\n2018-01-01 00:00:00\n')
            (data / 'evaluation_block_1.csv').write_text('timestamp\n2018-01-01 00:10:00\n')
            result = boundary_findings(root)
            self.assertEqual(result['full_declared_development_artifact_overlap']['overlapping_horizon_target_pairs'], 5)
            self.assertEqual(result['combined_declared_development_overlap']['unique_shared_target_times'], 5)
            self.assertEqual(result['combined_declared_development_overlap']['overlapping_scored_h1_times'], 1)


if __name__ == '__main__':
    unittest.main()
