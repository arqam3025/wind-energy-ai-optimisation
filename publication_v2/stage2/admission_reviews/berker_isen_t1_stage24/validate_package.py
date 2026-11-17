"""Read-only preparation checks. Success means PENDING_REVIEW, never admission.

Uses the standard library only; no predictor, solver, training or experiment
module is imported. No files are written by this script, including on failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

PACKAGE_ID = 'berker-isen-t1-retrospective-stage24'
RAW_SHA256 = 'f92c33c1cc199756b759fec251eeddc506f35d6a9e47ede034fc3e339a7c46d5'
ARCHIVE_SHA256 = 'a867d34200add600eedb3832540435cf57335ba6374c77b50f90b0ab16553ea1'
SOURCE_URL = 'https://www.kaggle.com/datasets/berkerisen/wind-turbine-scada-dataset'
ROLE = 'RETROSPECTIVE_DEVELOPMENT'
BLOCKED = 'BLOCKED_CONFIRMATORY_TEST'
CATEGORIES = {'INDEPENDENTLY_AUTHENTICATED', 'LOCAL_CORROBORATION', 'AUTHOR_CREATED_RECORD', 'ASSUMPTION', 'MISSING_EVIDENCE'}
BLANK_DESIGN = {'analysis_protocol_created_at', 'analysis_protocol_approved_at', 'authorized_periods',
                'model_fitting_cutoff', 'model_available_at', 'static_calibration_target_cutoff',
                'availability_mode', 'assumed_latency_scenario', 'canonical_dataset',
                'lineage_manifest', 'cohort_policy', 'study_contract'}
REVIEW_KEYS = {'reviewer', 'review_document', 'authorized_periods', 'source_identity',
               'lineage_manifest_sha256', 'cohort_policy_sha256', 'provenance_sha256',
               'dataset_document_sha256', 'study_role', 'study_contract_sha256',
               'analysis_clock_evidence_sha256', 'availability_mode', 'independently_checked'}
EVIDENCE_IDS = {'E01_SOURCE_ATTRIBUTION', 'E02_LOCAL_RAW', 'E03_LOCAL_ARCHIVE', 'E04_ACQUISITION_TRACE',
                'E05_RAW_STRUCTURE', 'E06_HEADER_UNITS', 'E07_HISTORICAL_TRANSFORM', 'E08_TARGET_DEFINITION',
                'E09_EXPOSURE', 'E10_HISTORICAL_CALIBRATION', 'E11_REPLAY_CONVENTION', 'E12_LATENCY_SCENARIO',
                'E13_RELEASE', 'E14_LICENCE', 'E15_TIMEZONE', 'E16_INTERVAL', 'E17_AVAILABILITY',
                'E18_SOURCE_QC', 'E19_CANONICAL_LINEAGE', 'E20_NEW_COHORT', 'E21_NEW_CUTOFFS',
                'E22_INDEPENDENT_REVIEW', 'E23_MODEL_HISTORY', 'E24_FIRST_ACCESS', 'E25_CLEAN_ENVIRONMENT'}
CHECKLIST_IDS = {'C01_INDEPENDENCE', 'C02_SOURCE', 'C03_ACQUISITION', 'C04_RIGHTS', 'C05_TIMEZONE',
                 'C06_INTERVAL', 'C07_UNITS_TARGET', 'C08_QUALITY', 'C09_TRANSFORM', 'C10_FEATURE_SUPPORT',
                 'C11_AVAILABILITY', 'C12_LATENCY_LIMIT', 'C13_EXPOSURE', 'C14_PROTOCOL_CLOCK',
                 'C15_COHORT', 'C16_BOUNDARIES', 'C17_MODEL_CUTOFF', 'C18_CALIBRATION',
                 'C19_COMPARISON', 'C20_ENVIRONMENT', 'C21_CLAIMS', 'C22_DECISION_BINDINGS'}
PENDING_IDS = {'P01_SOURCE_RELEASE', 'P02_ACQUISITION_AND_ACCESS', 'P03_RIGHTS', 'P04_CLOCK_AND_INTERVAL',
               'P05_UNITS_AND_TARGET', 'P06_AVAILABILITY_SCENARIO', 'P07_REVIEWED_TRANSFORMATION',
               'P08_COHORT_AND_EXCLUSIONS', 'P09_EXPOSURE_AND_AUTHORIZED_PERIODS', 'P10_ACTUAL_PROTOCOL_CLOCKS',
               'P11_FITTING_CHRONOLOGY', 'P12_CALIBRATION_CHRONOLOGY',
               'P13_FAIR_COMPARISON_AND_ENVIRONMENT', 'P14_INDEPENDENT_DECISION_AND_BINDINGS'}


class PackageError(ValueError):
    """Preparation is incomplete, inconsistent or falsely suggests approval."""


def _require(condition, message):
    if not condition:
        raise PackageError(message)


def _null_tree(value):
    return all(_null_tree(v) for v in value.values()) if isinstance(value, dict) else value is None


def _hash(path):
    try:
        with Path(path).open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    except OSError as error:
        raise PackageError(f'Missing/unreadable evidence: {path}') from error


def _inside(root, relative):
    _require(isinstance(relative, str) and relative and ':' not in relative, 'Invalid evidence path')
    root = Path(root).resolve()
    fragment = Path(relative.replace('\\', '/'))
    _require(not fragment.is_absolute() and '..' not in fragment.parts, 'Evidence path escapes root')
    target = root / fragment
    _require(target.resolve().is_relative_to(root), 'Evidence path escapes root')
    current = target
    while current != root:
        _require(not current.is_symlink() and not getattr(current, 'is_junction', lambda: False)(),
                 'Redirected evidence path is unsupported')
        current = current.parent
    return target


def _json(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise PackageError(f'Missing or malformed package JSON: {path}') from error
    _require(isinstance(value, dict), 'Package JSON must be an object')
    return value


def _validate_documents(register, proposal, form):
    """Validate this initial pending package, not a completed reviewer decision.

    A later signed decision belongs in a new version and a separate admission
    process. This validator deliberately refuses to promote the initial form.
    """
    expected_schemas = ('publication_v2.stage24.evidence-register.v1',
                        'publication_v2.stage24.pending-review.v1', 'publication_v2.stage24.reviewer-form.v1')
    for doc, schema in zip((register, proposal, form), expected_schemas):
        _require(isinstance(doc, dict) and doc.get('schema_version') == schema, 'Unsupported package schema')
        _require(doc.get('status') == 'PENDING_REVIEW' and doc.get('study_role') == ROLE
                 and doc.get('confirmatory_status') == BLOCKED, 'Pending retrospective scope/confirmation firewall changed')
    _require(register.get('package_id') == proposal.get('proposal_id') == form.get('proposal_id') == PACKAGE_ID,
             'Package/proposal identity mismatch')
    _require(register.get('real_data_admitted') is False and register.get('experiments_authorized') is False,
             'Evidence register cannot authorize admission or experiments')
    for field in ('installable', 'approved', 'independently_checked'):
        _require(proposal.get(field) is False, f'Pending proposal cannot set {field}')
    candidate = proposal.get('candidate_review_entry')
    _require(isinstance(candidate, dict) and set(candidate) == REVIEW_KEYS, 'Missing/unsupported candidate review bindings')
    _require(candidate['study_role'] == ROLE and candidate['independently_checked'] is False,
             'Candidate review is not approved')
    _require(all(v is None for k, v in candidate.items() if k not in ('study_role', 'independently_checked')),
             'Pending candidate review identity, dates, periods and approval hashes must remain null')
    source = proposal.get('source_reference', {})
    _require(source.get('source_url') == SOURCE_URL and source.get('local_raw_path') == 'data/raw/T1.csv'
             and source.get('local_raw_sha256') == RAW_SHA256 and source.get('local_archive_sha256') == ARCHIVE_SHA256,
             'Known local source/artifact identity changed')
    pending = proposal.get('pending_requirements')
    _require(isinstance(pending, list) and len(pending) == 14
             and {item['id'] for item in pending} == PENDING_IDS
             and all(isinstance(item.get('details'), str) and item['details'].strip() for item in pending),
             'Pending admission requirements are incomplete')
    _require(form.get('decision') == 'NOT_REVIEWED'
             and form.get('form_authorizes_execution') is False
             and form.get('form_authorizes_registry_installation') is False, 'Reviewer form cannot self-approve')
    _require(set(form.get('allowed_decisions', [])) == {'NOT_REVIEWED', 'REQUEST_EVIDENCE', 'REJECT',
                'CONDITIONAL_RETROSPECTIVE_REVIEW', 'APPROVE_RETROSPECTIVE_ONLY'}, 'Unsupported reviewer decision options')
    for field in ('reviewer', 'independence_statement', 'reviewed_at', 'approval_at', 'review_document',
                  'availability_mode', 'assumed_latency_scenario', 'conditions', 'unresolved_requirements', 'reviewer_notes'):
        _require(field in form and form[field] is None, f'Initial reviewer form must leave {field} null')
    blank_groups = {
        'actual_protocol_timestamps': {'protocol_created_at', 'protocol_approved_at', 'planned_execution_not_before', 'analysis_clock_evidence'},
        'actual_access_timestamps': {'acquired_at', 'first_access_at', 'recorded_at', 'access_evidence'},
        'replay_cutoffs': {'model_fitting_cutoff', 'model_available_at', 'static_calibration_target_cutoff'},
        'proposed_authorized_periods': {'train', 'calibration', 'development'}}
    for key, names in blank_groups.items():
        value = form.get(key)
        _require(isinstance(value, dict) and set(value) == names and _null_tree(value), f'Invented or incomplete {key}')
    for period in form['proposed_authorized_periods'].values():
        _require(isinstance(period, dict) and set(period) == {'start', 'end'}, 'Explicit blank authorized periods required')
    checklist = form.get('checklist')
    _require(isinstance(checklist, list) and len(checklist) == 22
             and {item['id'] for item in checklist} == CHECKLIST_IDS, 'Reviewer checklist is incomplete')
    for item in checklist:
        _require(item.get('status') == 'NOT_REVIEWED' and item.get('evidence_ids') == []
                 and item.get('reviewer_notes') is None and bool(item.get('question')), 'Checklist contains an invented review')
    _require(len(form.get('prohibited_claims', [])) >= 5, 'Claim limitations are missing')

    evidence = register.get('evidence')
    _require(isinstance(evidence, list) and len(evidence) == 25, 'Evidence register is incomplete')
    identifiers = [item['id'] for item in evidence]
    _require(len(set(identifiers)) == len(identifiers), 'Duplicate evidence identities')
    _require(set(identifiers) == EVIDENCE_IDS, 'Missing required evidence topics')
    _require(set(register.get('evidence_taxonomy', {})) == CATEGORIES, 'Evidence taxonomy changed')
    _require(register.get('independent_scientific_authentication') == {'status': 'NOT_ESTABLISHED', 'evidence_ids': []},
             'Independent authentication cannot be invented')
    for item in evidence:
        _require(item.get('category') in CATEGORIES and bool(item.get('topic')) and bool(item.get('status'))
                 and 'value' in item and bool(item.get('limitations'))
                 and bool(item.get('basis')) and bool(item.get('required_resolution')), 'Unclassified or unsupported evidence')
        _require(item['category'] != 'INDEPENDENTLY_AUTHENTICATED', 'This package establishes no independent scientific authentication')
        if item['category'] == 'MISSING_EVIDENCE':
            _require(item.get('status') == 'UNRESOLVED' and item.get('value') is None, 'Missing evidence cannot be populated as fact')
    by_id = {item['id']: item for item in evidence}
    _require(by_id['E02_LOCAL_RAW']['value']['sha256'] == RAW_SHA256
             and by_id['E03_LOCAL_ARCHIVE']['value']['sha256'] == ARCHIVE_SHA256, 'Register/proposal hash mismatch')
    profile = by_id['E05_RAW_STRUCTURE']['value']
    _require(profile.get('timezone_assigned') is False and profile.get('rows') == 50530
             and profile.get('duplicated_timestamps') == 0 and len(profile.get('gaps', [])) == 32
             and sum(g['missing_slots'] for g in profile['gaps']) == profile.get('missing_expected_slots') == 2030,
             'Local structure or unresolved clock was misrepresented')
    design = register.get('new_admission_design')
    _require(isinstance(design, dict) and set(design) == BLANK_DESIGN and _null_tree(design),
             'New admission dates, cutoffs, periods and transformations must remain pending')
    negative = register.get('negative_archived_comparison', {})
    for name, count, exceedance in (('uncontrolled', 1465, 317210.288),
                                    ('adaptive_one_sided', 1486, 323638.526),
                                    ('fixed_margin', 1502, 326158.296)):
        _require(negative.get(name) == {'violations': count, 'summed_exceedance_kw': exceedance},
                 'Archived negative comparison was changed or omitted')
    checks = register.get('public_metadata_checks')
    _require(isinstance(checks, list) and len(checks) >= 6, 'Public metadata access record missing')
    for check in checks:
        _require(check.get('status') in ('TITLE_ONLY_NO_READABLE_SUBSTANTIVE_METADATA', 'INACCESSIBLE_AUTOMATED_TOOL')
                 and check.get('limitation'), 'Public metadata access cannot be overstated')
    serialized = json.dumps((register, proposal, form), ensure_ascii=False)
    _require(not re.search(r'x-goog-(credential|signature|security-token|algorithm)', serialized, re.I),
             'Signed acquisition URL credentials must not be retained')
    return {'status': 'INTERNALLY_CONSISTENT_PENDING_REVIEW', 'scientific_admission': False,
            'experiments_authorized': False, 'confirmatory_status': BLOCKED,
            'evidence_items': len(evidence), 'review_checklist_items': len(checklist),
            'independent_scientific_authentication': 'NOT_ESTABLISHED'}


def validate_documents(register, proposal, form):
    try:
        return _validate_documents(register, proposal, form)
    except (KeyError, TypeError, AttributeError) as error:
        raise PackageError(f'Malformed or incomplete review-package metadata: {error}') from error


def verify_file_references(root, references):
    _require(isinstance(references, list) and references, 'Missing local evidence references')
    seen = set()
    for reference in references:
        _require(set(reference) >= {'path', 'sha256'} and reference['path'] not in seen, 'Duplicate/malformed local evidence reference')
        seen.add(reference['path'])
        _require(_hash(_inside(root, reference['path'])) == reference['sha256'], f'Evidence hash mismatch: {reference["path"]}')
    return len(seen)


def verify_archive(path, archive_sha256, raw_sha256):
    _require(_hash(path) == archive_sha256, 'Archive byte hash mismatch')
    try:
        with zipfile.ZipFile(path) as archive:
            _require(archive.namelist() == ['T1.csv'], 'Archive must contain exactly the known T1.csv member')
            with archive.open('T1.csv') as stream:
                _require(hashlib.file_digest(stream, 'sha256').hexdigest() == raw_sha256,
                         'Archive member does not match the local raw artifact')
    except (OSError, zipfile.BadZipFile) as error:
        raise PackageError('Unreadable acquisition archive') from error
    return {'status': 'LOCAL_BYTES_AND_MEMBER_MATCH', 'independent_authentication': False}


def validate_package(root, package_path, archive_path=None):
    root = Path(root).resolve()
    register = _json(Path(package_path) / 'evidence_register.json')
    proposal = _json(Path(package_path) / 'proposed_registry_entry.json')
    form = _json(Path(package_path) / 'reviewer_decision_form.json')
    result = validate_documents(register, proposal, form)
    result['local_evidence_files_checked'] = verify_file_references(root, register['file_evidence'])
    result['model_hashes_checked_without_loading'] = verify_file_references(root, register['preserved_model_identities'])
    policy = _json(root / 'publication_v2/stage2/provenance_policy.json')
    _require(policy.get('confirmatory_status') == BLOCKED and policy.get('real_data_reviews') == {},
             'Installed confirmation status or unapproved registry changed')
    result['installed_registry_empty'] = True
    result['archive'] = {'status': 'NOT_REQUESTED', 'independent_authentication': False} if archive_path is None else verify_archive(
        archive_path, ARCHIVE_SHA256, RAW_SHA256)
    result['scope'] = 'READ_ONLY_NON_EXPERIMENTAL_PACKAGE_CHECK'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--archive-path', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(validate_package(args.root, Path(__file__).parent, args.archive_path), indent=2))
    except (PackageError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'PACKAGE_CHECK_FAILED', 'scientific_admission': False, 'reason': str(error)}))
        raise SystemExit(2)
