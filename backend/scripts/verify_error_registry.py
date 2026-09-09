"""Validate the permanent error registry without network, DB, or shell execution."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "docs/errors/error_registry.yaml"
SCHEMA_VERSION = 1
STATUSES = {"UNKNOWN", "OPEN", "IN_PROGRESS", "RESOLVED"}
CAUSE_STATUSES = {"UNKNOWN", "CONFIRMED"}
REGRESSION_STATUSES = {"UNKNOWN", "UNPROTECTED", "PROTECTED", "NOT_APPLICABLE"}
CHECK_TYPES = {"file_exists", "text_contains", "pytest_node", "git_commit_exists", "external_diagnostic"}
ID_RE = re.compile(r"^(API|CFG|VAL)-\d{3}$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
NODE_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
FORBIDDEN_KEYS = {"command", "shell", "cmd", "exec"}


class DuplicateKeyError(ValueError):
    pass


class StrictLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: StrictLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DuplicateKeyError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _err(errors: list[str], message: str) -> None:
    errors.append(message)


def _mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        _err(errors, f"{label} must be a mapping")
        return {}
    return value


def _safe_repo_path(raw: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(raw, str) or not raw:
        _err(errors, f"{label}.path must be a non-empty repository-relative string")
        return None
    candidate = Path(raw)
    if candidate.is_absolute() or ".." in candidate.parts:
        _err(errors, f"{label}.path escapes repository: {raw}")
        return None
    resolved = (ROOT / candidate).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        _err(errors, f"{label}.path escapes repository: {raw}")
        return None
    return resolved


def _tracked(path: Path, label: str, errors: list[str]) -> None:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", str(path.relative_to(ROOT))],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        _err(errors, f"{label} is not tracked by Git: {path.relative_to(ROOT)}")


def _reject_forbidden_keys(value: Any, label: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        forbidden = FORBIDDEN_KEYS.intersection(value)
        if forbidden:
            _err(errors, f"{label} contains forbidden shell field(s): {sorted(forbidden)}")
        for key, child in value.items():
            _reject_forbidden_keys(child, f"{label}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_keys(child, f"{label}[{index}]", errors)


def _validate_check(check: Any, label: str, errors: list[str]) -> None:
    item = _mapping(check, label, errors)
    check_type = item.get("type")
    if check_type not in CHECK_TYPES:
        _err(errors, f"{label}.type must be one of {sorted(CHECK_TYPES)}")
        return
    forbidden = FORBIDDEN_KEYS.intersection(item)
    if forbidden:
        _err(errors, f"{label} contains forbidden shell field(s): {sorted(forbidden)}")
    if check_type in {"file_exists", "text_contains", "pytest_node"}:
        path = _safe_repo_path(item.get("path"), label, errors)
        if path is not None:
            if not path.is_file():
                _err(errors, f"{label}.path does not exist: {item.get('path')}")
            else:
                _tracked(path, label, errors)
    if check_type == "text_contains":
        if not isinstance(item.get("text"), str):
            _err(errors, f"{label}.text must be a string")
        elif isinstance(path, Path) and path.is_file() and item["text"] not in path.read_text(encoding="utf-8"):
            _err(errors, f"{label}.text is not present in {item['path']}")
    if check_type == "pytest_node":
        node_id = item.get("node_id")
        if not isinstance(node_id, str) or not NODE_RE.fullmatch(node_id):
            _err(errors, f"{label}.node_id has an unsafe or invalid structure")
    if check_type == "git_commit_exists":
        sha = item.get("sha")
        if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
            _err(errors, f"{label}.sha must be a valid local Git SHA")
        else:
            result = subprocess.run(
                ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode != 0:
                _err(errors, f"{label}.sha is not a local commit: {sha}")
    if check_type == "external_diagnostic":
        if not isinstance(item.get("description"), str) and not isinstance(item.get("reference"), str):
            _err(errors, f"{label} needs description or reference")


def validate_registry(data: Any) -> list[str]:
    errors: list[str] = []
    _reject_forbidden_keys(data, "registry document", errors)
    root = _mapping(data, "registry document", errors)
    if root.get("schema_version") != SCHEMA_VERSION:
        _err(errors, f"schema_version must be {SCHEMA_VERSION}")
    registry = _mapping(root.get("registry"), "registry", errors)
    entries = registry.get("errors")
    if not isinstance(entries, list) or not entries:
        _err(errors, "registry.errors must be a non-empty list")
        return errors
    seen: set[str] = set()
    for index, raw_entry in enumerate(entries):
        label = f"registry.errors[{index}]"
        entry = _mapping(raw_entry, label, errors)
        error_id = entry.get("id")
        if not isinstance(error_id, str) or not ID_RE.fullmatch(error_id):
            _err(errors, f"{label}.id has invalid format")
        elif error_id in seen:
            _err(errors, f"duplicate error id: {error_id}")
        else:
            seen.add(error_id)
        for field in ("title", "observed_behavior", "discrepancy"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                _err(errors, f"{label}.{field} is required")
        if entry.get("status") not in STATUSES:
            _err(errors, f"{label}.status has invalid value")
        if entry.get("cause_status") not in CAUSE_STATUSES:
            _err(errors, f"{label}.cause_status has invalid value")
        if not isinstance(entry.get("cause"), str) or not entry["cause"].strip():
            _err(errors, f"{label}.cause is required")
        if entry.get("regression_status") not in REGRESSION_STATUSES:
            _err(errors, f"{label}.regression_status has invalid value")
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            _err(errors, f"{label}.evidence must be a non-empty list")
        else:
            for evidence_index, raw_evidence in enumerate(evidence):
                evidence_label = f"{label}.evidence[{evidence_index}]"
                item = _mapping(raw_evidence, evidence_label, errors)
                evidence_type = item.get("type")
                if evidence_type == "file":
                    path = _safe_repo_path(item.get("path"), evidence_label, errors)
                    if path is not None:
                        if not path.is_file():
                            _err(errors, f"{evidence_label}.path does not exist")
                        else:
                            _tracked(path, evidence_label, errors)
                elif evidence_type == "commit":
                    sha = item.get("sha")
                    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
                        _err(errors, f"{evidence_label}.sha is invalid")
                    else:
                        result = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                        if result.returncode != 0:
                            _err(errors, f"{evidence_label}.sha is not a local commit")
                else:
                    _err(errors, f"{evidence_label}.type must be file or commit")
        checks = entry.get("checks")
        if not isinstance(checks, list) or not checks:
            _err(errors, f"{label}.checks must be a non-empty list")
        else:
            for check_index, check in enumerate(checks):
                _validate_check(check, f"{label}.checks[{check_index}]", errors)
        if entry.get("cause_status") == "CONFIRMED":
            confirmed_evidence = [item for item in (evidence or []) if isinstance(item, dict) and item.get("type") in {"file", "commit"}]
            if not confirmed_evidence:
                _err(errors, f"{label} confirmed cause lacks offline evidence")
    return errors


def load_registry(path: Path = REGISTRY_PATH) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.load(handle, Loader=StrictLoader)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    args = parser.parse_args(argv)
    try:
        errors = validate_registry(load_registry(args.registry))
    except (OSError, yaml.YAMLError, DuplicateKeyError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: error registry valid ({args.registry.relative_to(ROOT)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
