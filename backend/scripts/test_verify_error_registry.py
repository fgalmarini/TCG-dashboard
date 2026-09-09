from __future__ import annotations

from pathlib import Path

import pytest

from verify_error_registry import DuplicateKeyError, StrictLoader, load_registry, validate_registry


ROOT = Path(__file__).resolve().parents[2]


def _entry(**overrides):
    entry = {
        "id": "API-001",
        "title": "Test error",
        "status": "UNKNOWN",
        "cause": "UNKNOWN",
        "cause_status": "UNKNOWN",
        "regression_status": "UNKNOWN",
        "observed_behavior": "Observed behavior",
        "evidence": [{"type": "file", "path": "AGENTS.md", "note": "local evidence"}],
        "discrepancy": "No confirmed historical linkage",
        "checks": [{"type": "file_exists", "path": "AGENTS.md"}],
    }
    entry.update(overrides)
    return entry


def _document(*entries):
    return {"schema_version": 1, "registry": {"name": "test", "owner": "test", "errors": list(entries)}}


def test_repository_registry_is_valid():
    assert validate_registry(load_registry()) == []


def test_duplicate_yaml_keys_are_rejected():
    with pytest.raises(DuplicateKeyError):
        load_registry_from_text("schema_version: 1\nschema_version: 2\n")


def load_registry_from_text(text: str):
    import yaml

    return yaml.load(text, Loader=StrictLoader)


def test_duplicate_ids_are_rejected():
    errors = validate_registry(_document(_entry(), _entry()))
    assert any("duplicate error id" in error for error in errors)


def test_unknown_states_are_valid_and_resolved_is_independent_from_protection():
    entry = _entry(status="RESOLVED", regression_status="UNPROTECTED")
    assert validate_registry(_document(entry)) == []


def test_confirmed_cause_requires_offline_evidence():
    entry = _entry(cause_status="CONFIRMED", evidence=[{"type": "external_diagnostic", "description": "remote note"}])
    errors = validate_registry(_document(entry))
    assert any("confirmed cause lacks offline evidence" in error for error in errors)


def test_multiple_typed_checks_are_supported_without_running_pytest():
    entry = _entry(
        checks=[
            {"type": "file_exists", "path": "AGENTS.md"},
            {"type": "text_contains", "path": "AGENTS.md", "text": "Data Safety"},
            {"type": "pytest_node", "path": "backend/api/test_queries.py", "node_id": "test_latest_price_snapshot_picks_max_observed_at"},
            {"type": "git_commit_exists", "sha": "53fe74d5f99684c6b13f40d90ffdf655064bc880"},
            {"type": "external_diagnostic", "reference": "https://example.invalid/diagnostic"},
        ]
    )
    assert validate_registry(_document(entry)) == []


def test_external_diagnostic_does_not_need_a_local_path():
    entry = _entry(checks=[{"type": "external_diagnostic", "description": "not executed"}])
    assert validate_registry(_document(entry)) == []


def test_text_contains_checks_the_literal_content():
    entry = _entry(checks=[{"type": "text_contains", "path": "AGENTS.md", "text": "not present"}])
    errors = validate_registry(_document(entry))
    assert any("text is not present" in error for error in errors)


def test_missing_or_untracked_paths_fail():
    entry = _entry(checks=[{"type": "file_exists", "path": "does-not-exist.txt"}])
    errors = validate_registry(_document(entry))
    assert any("does not exist" in error for error in errors)


def test_paths_cannot_escape_repository():
    entry = _entry(checks=[{"type": "file_exists", "path": "../outside.txt"}])
    errors = validate_registry(_document(entry))
    assert any("escapes repository" in error for error in errors)


def test_shell_fields_are_rejected():
    entry = _entry(checks=[{"type": "file_exists", "path": "AGENTS.md", "command": "rm -rf ."}])
    errors = validate_registry(_document(entry))
    assert any("forbidden shell field" in error for error in errors)


def test_shell_fields_are_rejected_at_any_yaml_level():
    entry = _entry(evidence=[{"type": "file", "path": "AGENTS.md", "command": "pytest"}])
    errors = validate_registry(_document(entry))
    assert any("forbidden shell field" in error for error in errors)


def test_invalid_check_type_and_commit_fail():
    entry = _entry(checks=[{"type": "shell", "command": "pytest"}, {"type": "git_commit_exists", "sha": "not-a-sha"}])
    errors = validate_registry(_document(entry))
    assert any("must be one of" in error for error in errors)
    assert any("valid local Git SHA" in error for error in errors)
