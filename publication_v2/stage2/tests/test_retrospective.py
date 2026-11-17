"""Synthetic retrospective-protocol regressions; no model fitting or real data admission."""
from __future__ import annotations

import copy
import csv
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from publication_v2.integrity import digest
from publication_v2.stage2.data import DatasetError, load_bundle
from publication_v2.stage2.lineage import FIELDS, POLICY, verify_lineage
from publication_v2.stage2.tests.fixtures import dataset, refresh_lineage


CREATED = '2026-11-04T10:00:00+00:00'
APPROVED = '2026-11-04T11:00:00+00:00'
EXECUTION = '2026-11-04T13:00:00+00:00'


def _historical(value):
    if isinstance(value, dict):
        return {key: _historical(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_historical(item) for item in value]
    if isinstance(value, str):
        return value.replace('2030-', '2018-').replace('2029-', '2017-')
    return value


def retrospective_dataset(root: Path) -> Path:
    """Make fictional 2018 records with an honestly later fictional 2026 plan."""
    path = dataset(root)
    document = _historical(json.loads(path.read_text(encoding='utf-8')))
    for records in document['partitions'].values():
        for row in records:
            for feature in row['features']:
                feature['available_at'] = max(feature['source_available_ats'])
    for filename in ('fixture_measurements.csv', 'fixture_upstream.csv'):
        source = root / filename
        with source.open(newline='', encoding='utf-8') as stream:
            rows = [_historical(row) for row in csv.DictReader(stream)]
        with source.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    policy_path = root / document['cohort_policy']['path']
    policy = _historical(json.loads(policy_path.read_text(encoding='utf-8')))
    policy['declared_at'] = CREATED
    policy_path.write_text(json.dumps(policy), encoding='utf-8')
    document['cohort_policy']['sha256'] = digest(policy_path)
    refresh_lineage(root, document)
    clock = {'schema_version': 'publication_v2.stage23.analysis-clock.v1',
             'protocol_created_at': CREATED, 'protocol_approved_at': APPROVED,
             'reviewer': 'SYNTHETIC_REVIEWER', 'recorded_at': '2026-11-04T12:00:00+00:00'}
    clock_path = root / 'fixture_analysis_clock.json'
    clock_path.write_text(json.dumps(clock), encoding='utf-8')
    access = {'acquired_at': '2026-10-12T14:17:29+00:00',
              'first_access_at': '2026-10-12T14:18:00+00:00',
              'exposure_status': 'PREVIOUSLY_INSPECTED',
              'prior_study_roles': ['RETROSPECTIVE_DEVELOPMENT'],
              'custodian': 'SYNTHETIC_CUSTODIAN',
              'recorded_at': '2026-10-13T09:00:00+00:00'}
    access_path = root / 'fixture_access_record.json'
    access_path.write_text(json.dumps({'schema_version': 'publication_v2.stage23.access-record.v1',
                                      **access}), encoding='utf-8')
    availability_path = root / 'fixture_latency_evidence.txt'
    availability_path.write_text('Fictional software-test scenario only. Zero measurement and feature '
                                 'latency; one-second residual processing. No deployability evidence.',
                                 encoding='utf-8')
    contract = {'schema_version': 'publication_v2.stage23.study.v1',
                'study_role': 'RETROSPECTIVE_DEVELOPMENT',
                'analysis': {'protocol_created_at': CREATED, 'protocol_approved_at': APPROVED,
                             'planned_execution_not_before': EXECUTION, 'reviewer': 'SYNTHETIC_REVIEWER',
                             'clock_evidence': {'path': clock_path.name, 'sha256': digest(clock_path)}},
                'data_access': {**access, 'evidence': {'path': access_path.name, 'sha256': digest(access_path)}},
                'availability': {'mode': 'ASSUMED_LATENCY',
                                 'operational_availability_established': False,
                                 'historical_deployability_verified': False,
                                 'evidence': {'path': availability_path.name, 'sha256': digest(availability_path)},
                                 'scenario': {'scenario_id': 'SYNTHETIC_ZERO_LATENCY', 'units': 'seconds',
                                              'measurement_latency_seconds': 0,
                                              'feature_processing_latency_seconds': 0,
                                              'residual_processing_latency_seconds': 1,
                                              'rationale': 'Explicit hypothetical timing; never operational evidence.'}},
                'replay': {'model_fitting_cutoff': document['fit_time'],
                           'model_available_at': document['fit_time'],
                           'static_calibration_target_cutoff': max(
                               item['target_time'] for row in document['partitions']['calibration']
                               for item in row['targets']),
                           'calibration_rule': 'target_time < decision_time',
                           'availability_rule': 'observation_available_at <= decision_time and residual_available_at <= decision_time'}}
    contract_path = root / 'fixture_study_contract.json'
    contract_path.write_text(json.dumps(contract), encoding='utf-8')
    document['study_contract'] = {'path': contract_path.name, 'sha256': digest(contract_path)}
    path.write_text(json.dumps(document), encoding='utf-8')
    return path


class RetrospectiveProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = retrospective_dataset(self.root)
        self.document = json.loads(self.path.read_text(encoding='utf-8'))
        self.contract_path = self.root / self.document['study_contract']['path']
        self.contract = json.loads(self.contract_path.read_text(encoding='utf-8'))

    def save(self):
        self.contract_path.write_text(json.dumps(self.contract), encoding='utf-8')
        if 'study_contract' in self.document:
            self.document['study_contract']['sha256'] = digest(self.contract_path)
        self.path.write_text(json.dumps(self.document), encoding='utf-8')

    def load(self):
        self.save()
        return load_bundle(self.path, self.root, allow_synthetic=True)

    def save_policy(self, policy):
        path = self.root / self.document['cohort_policy']['path']
        path.write_text(json.dumps(policy), encoding='utf-8')
        self.document['cohort_policy']['sha256'] = digest(path)

    def mock_real_review(self):
        """Fictional trust-policy fixture only; no installed approval or real observations."""
        self.document['dataset_kind'] = 'REAL_DEVELOPMENT'
        for item in self.document['provenance'].values():
            item['status'] = 'ATTESTED'
        self.document['provenance']['availability']['value'] = {
            'mode': self.contract['availability']['mode']}
        manifest_path = self.root / self.document['lineage_manifest']['path']
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['independent_review_id'] = 'MOCK_REVIEW_SYNTHETIC_MEASUREMENTS_ONLY'
        manifest['study_role'] = self.contract['study_role']
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        self.document['lineage_manifest']['sha256'] = digest(manifest_path)
        self.save()
        evidence = self.root / 'fictional_review_not_real_provenance.txt'
        evidence.write_text('Fictional software fixture; no external review, rights, timing or '
                            'source eligibility is established. No real observations or fits.', encoding='utf-8')
        cohort = json.loads((self.root / self.document['cohort_policy']['path']).read_text(encoding='utf-8'))
        canonical_hash = lambda value: hashlib.sha256(json.dumps(
            value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        review = {'independently_checked': True,
                  'lineage_manifest_sha256': self.document['lineage_manifest']['sha256'],
                  'cohort_policy_sha256': self.document['cohort_policy']['sha256'],
                  'source_identity': manifest['source_identity'],
                  'provenance_sha256': canonical_hash(self.document['provenance']),
                  'dataset_document_sha256': canonical_hash(self.document),
                  'review_document': {'path': evidence.name, 'sha256': digest(evidence)},
                  'reviewer': 'FICTIONAL_SOFTWARE_TEST_REVIEWER',
                  'authorized_periods': cohort['authorized_periods'],
                  'study_role': self.contract['study_role'],
                  'study_contract_sha256': self.document['study_contract']['sha256'],
                  'analysis_clock_evidence_sha256': self.contract['analysis']['clock_evidence']['sha256'],
                  'availability_mode': self.contract['availability']['mode']}
        policy = json.loads(POLICY.read_text(encoding='utf-8'))
        policy['real_data_reviews'] = {manifest['independent_review_id']: review}
        return policy, manifest['independent_review_id']

    def patched_policy(self, policy):
        original_read = Path.read_text

        def read(path, *args, **kwargs):
            return json.dumps(policy) if path == POLICY else original_read(path, *args, **kwargs)

        return patch.object(Path, 'read_text', read)

    def test_legitimate_late_retrospective_declaration_is_admitted(self):
        bundle = self.load()
        self.assertLess(bundle.partitions['development'][0].decision,
                        datetime.fromisoformat(CREATED))
        self.assertIn('RETROSPECTIVE_DEVELOPMENT', json.dumps(bundle.admission_report))
        self.assertIn(self.contract_path.name, bundle.input_hashes)
        self.assertIn('fixture_analysis_clock.json', bundle.input_hashes)
        self.assertIn('fixture_access_record.json', bundle.input_hashes)
        self.assertIn('BLOCKED_CONFIRMATORY_TEST', json.dumps(bundle.admission_report))

    def test_legacy_synthetic_fixture_keeps_its_existing_guard(self):
        del self.document['study_contract']
        policy_path = self.root / self.document['cohort_policy']['path']
        policy = json.loads(policy_path.read_text(encoding='utf-8'))
        with self.assertRaises(DatasetError):
            self.load()
        policy['declared_at'] = '2017-12-31T00:00:00+00:00'
        self.save_policy(policy)
        self.load()

    def test_backdated_cohort_declaration_cannot_disagree_with_actual_creation(self):
        policy_path = self.root / self.document['cohort_policy']['path']
        policy = json.loads(policy_path.read_text(encoding='utf-8'))
        policy['declared_at'] = '2017-12-31T00:00:00+00:00'
        self.save_policy(policy)
        with self.assertRaises(DatasetError):
            self.load()

    def test_backdated_creation_cannot_disagree_with_clock_evidence(self):
        self.contract['analysis']['protocol_created_at'] = '2017-12-31T00:00:00+00:00'
        with self.assertRaises(DatasetError):
            self.load()

    def test_actual_analysis_clocks_must_be_ordered_and_not_future(self):
        original = copy.deepcopy(self.contract)
        for field, invalid in (('protocol_approved_at', '2026-11-04T09:00:00+00:00'),
                               ('planned_execution_not_before', '2026-11-04T10:30:00+00:00'),
                               ('protocol_created_at', '2099-01-01T00:00:00+00:00'),
                               ('protocol_created_at', '2026-11-04T10:00:00')):
            with self.subTest(field=field, invalid=invalid):
                self.contract = copy.deepcopy(original)
                self.contract['analysis'][field] = invalid
                with self.assertRaises(DatasetError):
                    self.load()

    def test_clock_evidence_tampering_fails_even_with_updated_contract_hash(self):
        clock = self.root / self.contract['analysis']['clock_evidence']['path']
        clock.write_text('{}', encoding='utf-8')
        with self.assertRaises(DatasetError):
            self.load()

    def test_actual_access_is_disclosed_and_cannot_claim_untouched(self):
        self.load()
        self.contract['data_access']['exposure_status'] = 'UNTOUCHED'
        with self.assertRaises(DatasetError):
            self.load()

    def test_access_evidence_mismatch_fails(self):
        self.contract['data_access']['first_access_at'] = '2026-10-13T14:18:00+00:00'
        with self.assertRaises(DatasetError):
            self.load()

    def test_role_label_and_self_declared_custody_do_not_enable_confirmation(self):
        self.contract['study_role'] = 'PROSPECTIVE_CONFIRMATION'
        self.contract['data_access']['exposure_status'] = 'UNTOUCHED'
        self.contract['data_access']['non_exposure_attested'] = True
        self.contract['data_access']['independent_custody_established'] = True
        with self.assertRaises(DatasetError):
            self.load()

    def test_confirmation_role_alone_is_rejected_without_other_invalid_metadata(self):
        self.contract['study_role'] = 'PROSPECTIVE_CONFIRMATION'
        with self.assertRaises(DatasetError):
            self.load()

    def test_confirmation_data_cannot_be_relabelled_as_development(self):
        self.document['contains_confirmation_data'] = True
        with self.assertRaises(DatasetError):
            self.load()

    def test_historical_exposure_survives_role_and_serialization_changes(self):
        self.save()
        lineage = verify_lineage(self.document, self.root, 'SYNTHETIC_FIXTURE')
        registry = {tuple(float(lineage.measurements[t][key]).hex() for key in FIELDS[3:]):
                    [datetime(2018, 12, 1)] for t in list(lineage.measurements)[:10]}
        upstream = self.root / self.document['source_artifact']['upstream']['path']
        with upstream.open(newline='', encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        with upstream.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(reversed(rows))
        refresh_lineage(self.root, self.document)
        with patch('publication_v2.stage2.lineage.historical_registry', return_value=registry):
            with self.assertRaises(DatasetError):
                self.load()

    def test_assumed_availability_never_establishes_historical_deployability(self):
        self.contract['availability']['historical_deployability_verified'] = True
        with self.assertRaises(DatasetError):
            self.load()

    def test_assumed_availability_cannot_claim_operational_evidence(self):
        self.contract['availability']['operational_availability_established'] = True
        with self.assertRaises(DatasetError):
            self.load()

    def test_assumed_latency_requires_explicit_complete_scenario(self):
        original = copy.deepcopy(self.contract)
        for missing in ('scenario', 'rationale', 'scenario_id', 'units'):
            with self.subTest(missing=missing):
                self.contract = copy.deepcopy(original)
                if missing == 'scenario':
                    del self.contract['availability']['scenario']
                else:
                    del self.contract['availability']['scenario'][missing]
                with self.assertRaises(DatasetError):
                    self.load()

    def test_invalid_assumed_latencies_and_unsupported_metadata_fail(self):
        original = copy.deepcopy(self.contract)
        for invalid in (-1, True, float('nan'), float('inf'), '0', 10**400):
            with self.subTest(invalid=invalid):
                self.contract = copy.deepcopy(original)
                self.contract['availability']['scenario']['measurement_latency_seconds'] = invalid
                with self.assertRaises(DatasetError):
                    self.load()
        self.contract = copy.deepcopy(original)
        self.contract['availability']['scenario']['units'] = 'minutes'
        with self.assertRaises(DatasetError):
            self.load()
        self.contract = copy.deepcopy(original)
        self.contract['availability']['scenario']['unreviewed_adjustment'] = 'permitted'
        with self.assertRaises(DatasetError):
            self.load()

    def test_assumed_receipt_and_processing_delays_must_match_ledgers(self):
        original = copy.deepcopy(self.contract)
        for field in ('measurement_latency_seconds', 'feature_processing_latency_seconds',
                      'residual_processing_latency_seconds'):
            with self.subTest(field=field):
                self.contract = copy.deepcopy(original)
                self.contract['availability']['scenario'][field] = 7
                with self.assertRaises(DatasetError):
                    self.load()

    def test_unavailable_feature_remains_rejected_in_assumed_scenario(self):
        feature = self.document['partitions']['development'][0]['features'][0]
        decision = self.document['partitions']['development'][0]['decision_time']
        feature['available_at'] = (datetime.fromisoformat(decision) + timedelta(seconds=1)).isoformat()
        with self.assertRaises(DatasetError):
            self.load()

    def test_consistent_feature_delay_reaches_and_fails_unchanged_origin_gate(self):
        self.contract['availability']['scenario']['feature_processing_latency_seconds'] = 1
        for rows in self.document['partitions'].values():
            for row in rows:
                for feature in row['features']:
                    feature['available_at'] = (
                        max(map(datetime.fromisoformat, feature['source_available_ats']))
                        + timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(DatasetError, 'Feature availability invalid'):
            self.load()

    def test_verified_operational_branch_is_only_a_synthetic_replay_fixture(self):
        availability = self.contract['availability']
        availability['mode'] = 'VERIFIED_OPERATIONAL'
        availability['operational_availability_established'] = True
        del availability['scenario']
        evidence = self.root / availability['evidence']['path']
        evidence.write_text('Fictional verified-clock software fixture, not actual operational '
                            'availability or historical deployability evidence.', encoding='utf-8')
        availability['evidence']['sha256'] = digest(evidence)
        bundle = self.load()
        admitted = bundle.admission_report['study_contract']['availability']
        self.assertEqual(admitted['mode'], 'VERIFIED_OPERATIONAL')
        self.assertIs(admitted['historical_deployability_verified'], False)
        self.assertEqual(bundle.admission_report['confirmatory_status'], 'BLOCKED_CONFIRMATORY_TEST')

    def test_mock_independent_review_requires_each_new_study_binding(self):
        policy, review_id = self.mock_real_review()
        with self.patched_policy(policy):
            bundle = load_bundle(self.path, self.root)
        self.assertEqual(bundle.admission_report['study_role'], 'RETROSPECTIVE_DEVELOPMENT')
        self.assertEqual(bundle.admission_report['confirmatory_status'], 'BLOCKED_CONFIRMATORY_TEST')
        changes = {'study_role': 'PROSPECTIVE_CONFIRMATION',
                   'study_contract_sha256': '0' * 64,
                   'analysis_clock_evidence_sha256': '0' * 64,
                   'availability_mode': 'VERIFIED_OPERATIONAL'}
        for name, wrong in changes.items():
            for remove in (False, True):
                with self.subTest(binding=name, remove=remove):
                    changed = copy.deepcopy(policy)
                    if remove:
                        del changed['real_data_reviews'][review_id][name]
                    else:
                        changed['real_data_reviews'][review_id][name] = wrong
                    with self.patched_policy(changed), self.assertRaisesRegex(
                            DatasetError, 'study role, actual analysis clock or availability scenario'):
                        load_bundle(self.path, self.root)

    def test_confirmation_remains_blocked_under_fully_matching_mock_review(self):
        self.contract['study_role'] = 'PROSPECTIVE_CONFIRMATION'
        policy, _ = self.mock_real_review()
        with self.patched_policy(policy), self.assertRaisesRegex(DatasetError, 'BLOCKED_CONFIRMATORY_TEST'):
            load_bundle(self.path, self.root)

    def test_unavailable_model_and_fitting_cutoff_mismatches_fail(self):
        original = copy.deepcopy(self.contract)
        calibration_origin = self.document['partitions']['calibration'][0]['origin_time']
        for field, invalid in (('model_available_at', (datetime.fromisoformat(calibration_origin) + timedelta(seconds=1)).isoformat()),
                               ('model_fitting_cutoff', '2018-01-01T00:00:00+00:00')):
            with self.subTest(field=field):
                self.contract = copy.deepcopy(original)
                self.contract['replay'][field] = invalid
                with self.assertRaises(DatasetError):
                    self.load()

    def test_training_labels_unavailable_at_fit_are_rejected(self):
        observation = self.document['partitions']['train'][-1]['targets'][-1]
        observation['residual_available_at'] = (
            datetime.fromisoformat(self.document['fit_time']) + timedelta(seconds=1)).isoformat()
        with self.assertRaises(DatasetError):
            self.load()

    def test_consistent_replay_fit_metadata_still_cannot_precede_training_labels(self):
        latest = max(item['target_time'] for row in self.document['partitions']['train']
                     for item in row['targets'])
        too_early = (datetime.fromisoformat(latest) - timedelta(seconds=1)).isoformat()
        self.document['fit_time'] = too_early
        self.contract['replay']['model_fitting_cutoff'] = too_early
        self.contract['replay']['model_available_at'] = too_early
        with self.assertRaises(DatasetError):
            self.load()

    def test_consistent_replay_fit_metadata_still_cannot_follow_calibration_issuance(self):
        first = self.document['partitions']['calibration'][0]['issued_at']
        too_late = (datetime.fromisoformat(first) + timedelta(seconds=1)).isoformat()
        self.document['fit_time'] = too_late
        self.contract['replay']['model_fitting_cutoff'] = too_late
        self.contract['replay']['model_available_at'] = too_late
        with self.assertRaises(DatasetError):
            self.load()

    def test_calibration_cutoff_and_equal_time_rule_cannot_be_weakened(self):
        original = copy.deepcopy(self.contract)
        for field, invalid in (('static_calibration_target_cutoff', self.document['partitions']['development'][0]['decision_time']),
                               ('calibration_rule', 'target_time <= decision_time'),
                               ('availability_rule', 'ignore_receipts')):
            with self.subTest(field=field):
                self.contract = copy.deepcopy(original)
                self.contract['replay'][field] = invalid
                with self.assertRaises(DatasetError):
                    self.load()

    def test_real_data_still_requires_independent_registry_approval(self):
        self.document['dataset_kind'] = 'REAL_DEVELOPMENT'
        for item in self.document['provenance'].values():
            item['status'] = 'ATTESTED'
        self.save()
        with self.assertRaises(DatasetError):
            load_bundle(self.path, self.root)


if __name__ == '__main__':
    unittest.main()
