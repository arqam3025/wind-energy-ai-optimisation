"""Non-experimental review-package integrity tests; standard library only.

All adverse proposals are in-memory copies. File/archive fixtures are invented
temporary bytes. No source data, registry, model or research result is written.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile


PACKAGE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('stage24_package_validator', PACKAGE / 'validate_package.py')
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def sha256(value):
    return hashlib.sha256(value).hexdigest()


class PendingReviewIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.register = json.loads((PACKAGE / 'evidence_register.json').read_text(encoding='utf-8'))
        self.proposal = json.loads((PACKAGE / 'proposed_registry_entry.json').read_text(encoding='utf-8'))
        self.form = json.loads((PACKAGE / 'reviewer_decision_form.json').read_text(encoding='utf-8'))

    def evidence(self, identity):
        return next(row for row in self.register['evidence'] if row['id'] == identity)

    def validate(self):
        return validator.validate_documents(self.register, self.proposal, self.form)

    def rejected(self):
        with self.assertRaises(validator.PackageError):
            self.validate()

    def test_pending_package_is_reviewable_without_admitting_data(self):
        result = self.validate()
        self.assertIsInstance(result, dict)
        self.assertIn('BLOCKED_CONFIRMATORY_TEST', json.dumps(result))
        self.assertIs(self.register['real_data_admitted'], False)
        self.assertIs(self.proposal['installable'], False)
        self.assertEqual(self.form['decision'], 'NOT_REVIEWED')

    def test_approval_or_installation_flags_cannot_open_pending_proposal(self):
        original = copy.deepcopy(self.proposal)
        for name in ('approved', 'installable', 'independently_checked'):
            with self.subTest(flag=name):
                self.proposal = copy.deepcopy(original)
                self.proposal[name] = True
                self.rejected()

    def test_pending_status_and_experiment_authorization_are_not_mutable(self):
        original = copy.deepcopy(self.register)
        for name, value in (('status', 'APPROVED'), ('real_data_admitted', True),
                            ('experiments_authorized', True)):
            with self.subTest(field=name):
                self.register = copy.deepcopy(original)
                self.register[name] = value
                self.rejected()

    def test_study_role_and_confirmation_status_cannot_be_relabelled(self):
        originals = tuple(copy.deepcopy(doc) for doc in (self.register, self.proposal, self.form))
        for index in range(3):
            for name, value in (('study_role', 'PROSPECTIVE_CONFIRMATION'),
                                ('confirmatory_status', 'CONFIRMATORY_READY')):
                with self.subTest(document=index, field=name):
                    documents = [copy.deepcopy(doc) for doc in originals]
                    documents[index][name] = value
                    self.register, self.proposal, self.form = documents
                    self.rejected()

    def test_candidate_entry_has_no_independent_review_or_approved_binding(self):
        original = copy.deepcopy(self.proposal)
        values = {
            'independently_checked': True,
            'reviewer': 'unreviewed actor',
            'review_document': {'path': 'invented.json', 'sha256': 'a' * 64},
            'authorized_periods': {'train': {'start': '2018-01-01', 'end': '2018-02-01'}},
            'source_identity': {'release': 'unverified-version'},
            'lineage_manifest_sha256': 'a' * 64,
            'cohort_policy_sha256': 'a' * 64,
            'provenance_sha256': 'a' * 64,
            'dataset_document_sha256': 'a' * 64,
            'study_contract_sha256': 'a' * 64,
            'analysis_clock_evidence_sha256': 'a' * 64,
            'availability_mode': 'VERIFIED_OPERATIONAL',
            'study_role': 'PROSPECTIVE_CONFIRMATION',
        }
        for name, value in values.items():
            with self.subTest(field=name):
                self.proposal = copy.deepcopy(original)
                self.proposal['candidate_review_entry'][name] = value
                self.rejected()

    def test_blank_form_options_do_not_mean_a_completed_approval(self):
        original = copy.deepcopy(self.form)
        for name, value in (('decision', 'APPROVE_RETROSPECTIVE_ONLY'),
                            ('reviewer', 'unverified reviewer'),
                            ('reviewed_at', '2018-01-01T00:00:00+00:00'),
                            ('approval_at', '2018-01-01T00:00:00+00:00'),
                            ('independence_statement', 'self-asserted'),
                            ('review_document', {'path': 'unreviewed.json'}),
                            ('form_authorizes_execution', True),
                            ('form_authorizes_registry_installation', True)):
            with self.subTest(field=name):
                self.form = copy.deepcopy(original)
                self.form[name] = value
                self.rejected()

    def test_checklist_cannot_be_silently_marked_reviewed(self):
        self.form['checklist'][0]['status'] = 'PASS'
        self.form['checklist'][0]['evidence_ids'] = ['E01_SOURCE_ATTRIBUTION']
        self.rejected()

    def test_required_evidence_cannot_be_removed_or_given_duplicate_identity(self):
        original = copy.deepcopy(self.register)
        self.register['evidence'] = [row for row in self.register['evidence'] if row['id'] != 'E14_LICENCE']
        self.rejected()
        self.register = original
        self.register['evidence'].append(copy.deepcopy(self.register['evidence'][0]))
        self.rejected()

    def test_evidence_requires_explicit_topic_and_classification(self):
        original = copy.deepcopy(self.register)
        for field in ('topic', 'category'):
            with self.subTest(field=field):
                self.register = copy.deepcopy(original)
                del self.evidence('E15_TIMEZONE')[field]
                self.rejected()

    def test_local_record_cannot_be_upgraded_to_independent_authentication(self):
        self.evidence('E01_SOURCE_ATTRIBUTION')['category'] = 'INDEPENDENTLY_AUTHENTICATED'
        self.rejected()

    def test_independent_authentication_cannot_be_forged_from_local_evidence(self):
        self.register['independent_scientific_authentication'] = {
            'status': 'ESTABLISHED', 'evidence_ids': ['E02_LOCAL_RAW']}
        self.rejected()

    def test_missing_evidence_cannot_gain_an_invented_value(self):
        self.evidence('E15_TIMEZONE')['value'] = 'UTC'
        self.rejected()

    def test_unapproved_new_cutoffs_and_protocol_dates_remain_blank(self):
        original = copy.deepcopy(self.register)
        for field, value in (
                ('analysis_protocol_created_at', '2017-01-01T00:00:00+00:00'),
                ('analysis_protocol_approved_at', '2017-01-01T00:00:00+00:00'),
                ('model_fitting_cutoff', '2018-09-09T02:40:00+00:00'),
                ('static_calibration_target_cutoff', '2018-10-15T11:00:00+00:00'),
                ('authorized_periods', {'train': {'start': '2018-01-01', 'end': '2018-02-01'}})):
            with self.subTest(field=field):
                self.register = copy.deepcopy(original)
                self.register['new_admission_design'][field] = value
                self.rejected()

    def test_original_source_and_archive_hashes_cannot_be_replaced(self):
        original = copy.deepcopy(self.proposal)
        for field in ('local_raw_sha256', 'local_archive_sha256'):
            with self.subTest(field=field):
                self.proposal = copy.deepcopy(original)
                self.proposal['source_reference'][field] = 'a' * 64
                self.rejected()

    def test_signed_download_credentials_cannot_enter_public_package(self):
        self.evidence('E04_ACQUISITION_TRACE')['value']['archive']['host_url_without_query'] += (
            '?X-Goog-Credential=fictional&X-Goog-Signature=not-a-real-secret')
        self.rejected()


class ReferencedArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = b'invented evidence bytes for software validation only\n'
        self.path = self.root / 'evidence.txt'
        self.path.write_bytes(self.data)

    def test_valid_relative_reference_is_verified_without_rewriting_it(self):
        refs = [{'path': self.path.name, 'sha256': sha256(self.data)}]
        self.assertEqual(validator.verify_file_references(self.root, refs), 1)
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_missing_or_tampered_reference_fails(self):
        for reference in ({'path': 'absent.txt', 'sha256': sha256(self.data)},
                          {'path': self.path.name, 'sha256': 'a' * 64}):
            with self.subTest(reference=reference):
                with self.assertRaises(validator.PackageError):
                    validator.verify_file_references(self.root, [reference])

    def test_reference_cannot_escape_declared_root(self):
        for path in ('../outside.txt', str(self.path.resolve()), 'C:/outside.txt'):
            with self.subTest(path=path):
                with self.assertRaises(validator.PackageError):
                    validator.verify_file_references(self.root, [{'path': path, 'sha256': sha256(self.data)}])

    def archive(self, entries):
        archive = self.root / 'fictional.zip'
        with ZipFile(archive, 'w') as bundle:
            for name, content in entries:
                bundle.writestr(name, content)
        return archive

    def test_archive_member_verification_uses_supplied_bytes_and_hashes(self):
        archive = self.archive([('T1.csv', self.data)])
        result = validator.verify_archive(archive, sha256(archive.read_bytes()), sha256(self.data))
        self.assertIsInstance(result, dict)
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_archive_hash_member_hash_and_extra_member_fail_closed(self):
        archive = self.archive([('T1.csv', self.data)])
        for archive_hash, raw_hash in (('a' * 64, sha256(self.data)),
                                       (sha256(archive.read_bytes()), 'a' * 64)):
            with self.subTest(archive_hash=archive_hash, raw_hash=raw_hash):
                with self.assertRaises(validator.PackageError):
                    validator.verify_archive(archive, archive_hash, raw_hash)
        archive = self.archive([('T1.csv', self.data), ('unexpected.txt', b'not the source')])
        with self.assertRaises(validator.PackageError):
            validator.verify_archive(archive, sha256(archive.read_bytes()), sha256(self.data))


if __name__ == '__main__':
    unittest.main()
