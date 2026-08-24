'''Evidence-based delivery gates for Studies 03 through 08.'''

import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'config/study_delivery.yaml'
STUDY_IDS = [f'{number:02d}' for number in range(3, 9)]
STAGES = {'planned', 'offline_ready', 'engine_verified'}
EVIDENCE_KEYS = {
    'configuration',
    'scenario_generation',
    'analytical_checks',
    'plotting',
    'result_parser_contract',
    'builder_idempotency_tests',
    'offline_tests',
    'opt_in_engine_tests',
    'executed_results',
    'result_metadata',
    'pfd_archives',
    'pfd_hash_manifests',
}
ENGINE_GATES = {
    'executed_results',
    'result_metadata',
    'pfd_archives',
    'pfd_hash_manifests',
}
OFFLINE_GATES = EVIDENCE_KEYS - ENGINE_GATES


def _load_manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding='utf-8'))


def _declared_paths(study: dict, gate: str) -> list[Path]:
    values = study.get('evidence', {}).get(gate, [])
    study_id = study['id']
    assert isinstance(values, list), f'{study_id}:{gate} must be a list'
    paths: list[Path] = []
    for value in values:
        assert isinstance(value, str) and value.strip()
        relative = Path(value)
        assert not relative.is_absolute(), f'evidence path must be relative: {value}'
        candidate = (ROOT / relative).resolve()
        assert candidate.is_relative_to(ROOT.resolve()), f'evidence escapes repository: {value}'
        assert candidate.exists(), f'declared evidence does not exist: {value}'
        paths.append(candidate)
    return paths


def _metadata(path: Path) -> dict:
    if path.suffix.lower() == '.json':
        value = json.loads(path.read_text(encoding='utf-8'))
    else:
        value = yaml.safe_load(path.read_text(encoding='utf-8'))
    assert isinstance(value, dict), f'result metadata must be a mapping: {path}'
    return value


def _hash_is_versioned(archive: Path, manifests: list[Path]) -> bool:
    digest = hashlib.sha256(archive.read_bytes()).hexdigest().upper()
    for manifest in manifests:
        for line in manifest.read_text(encoding='utf-8').splitlines():
            fields = line.strip().replace('*', ' ').split()
            if (
                len(fields) >= 2
                and fields[0].upper() == digest
                and Path(fields[-1]).name == archive.name
            ):
                return True
    return False


def test_delivery_manifest_has_one_entry_per_study() -> None:
    data = _load_manifest()
    assert data['schema_version'] == 1
    assert data['required_studies'] == STUDY_IDS
    studies = data['studies']
    assert [study['id'] for study in studies] == STUDY_IDS
    assert len({study['id'] for study in studies}) == len(STUDY_IDS)

    for study in studies:
        assert study['stage'] in STAGES
        study_id = study['id']
        slug = study['slug']
        expected_directory = f'studies/{study_id}_{slug}'
        assert study['directory'] == expected_directory
        assert (ROOT / expected_directory / 'README.md').is_file()
        assert set(study.get('evidence', {})).issubset(EVIDENCE_KEYS)
        for gate in EVIDENCE_KEYS:
            _declared_paths(study, gate)


@pytest.mark.parametrize('study', _load_manifest()['studies'], ids=lambda item: item['id'])
def test_declared_stage_has_required_evidence(study: dict) -> None:
    stage = study['stage']
    readme = (ROOT / study['directory'] / 'README.md').read_text(encoding='utf-8')

    if stage == 'planned':
        assert re.search(r'Status:\s*planned', readme, flags=re.IGNORECASE)
        assert study['result_provenance'] == 'not_executed'
        assert all(not _declared_paths(study, gate) for gate in ENGINE_GATES)
        return

    for gate in OFFLINE_GATES:
        study_id = study['id']
        assert _declared_paths(study, gate), f'{study_id}:{gate} evidence is required'

    integration_sources = '\n'.join(
        path.read_text(encoding='utf-8')
        for path in _declared_paths(study, 'opt_in_engine_tests')
    )
    assert 'pytest.mark.powerfactory' in integration_sources
    assert 'PFEMT_RUN_INTEGRATION' in integration_sources

    if stage == 'offline_ready':
        assert study['result_provenance'] == 'not_executed'
        assert all(not _declared_paths(study, gate) for gate in ENGINE_GATES)
        return

    assert study['result_provenance'] == 'powerfactory_emt'
    for gate in ENGINE_GATES:
        study_id = study['id']
        assert _declared_paths(study, gate), f'{study_id}:{gate} evidence is required'


@pytest.mark.parametrize('study', _load_manifest()['studies'], ids=lambda item: item['id'])
def test_engine_verified_results_are_traceable_and_not_synthetic(study: dict) -> None:
    if study['stage'] != 'engine_verified':
        pytest.skip('study has no executed-result claim')

    metadata_files = _declared_paths(study, 'result_metadata')
    for path in metadata_files:
        data = _metadata(path)
        assert data.get('engine') == 'DIgSILENT PowerFactory'
        assert data.get('simulation_type') == 'EMT'
        assert data.get('execution_status') == 'executed'
        assert 'synthetic' not in json.dumps(data).lower()

    hash_manifests = _declared_paths(study, 'pfd_hash_manifests')
    for archive in _declared_paths(study, 'pfd_archives'):
        assert archive.suffix.lower() == '.pfd'
        assert archive.stat().st_size > 0
        assert _hash_is_versioned(archive, hash_manifests), (
            f'missing or incorrect SHA-256 for {archive.name}'
        )
