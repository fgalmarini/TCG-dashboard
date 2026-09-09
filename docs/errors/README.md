# Error Feedback & Regression Registry

`error_registry.yaml` is the canonical, versioned registry for known error and
regression feedback. It is deliberately separate from runtime data and does not
read or write the SQLite database.

## Lifecycle

`status` describes the lifecycle of the report: `UNKNOWN`, `OPEN`, `IN_PROGRESS`
or `RESOLVED`. `cause_status` is independently `UNKNOWN` or `CONFIRMED`, and
`regression_status` is independently `UNKNOWN`, `UNPROTECTED`, `PROTECTED` or
`NOT_APPLICABLE`. A resolved error is not automatically protected.

Unknown causes are valid. Do not infer a root cause from a symptom, a similar
commit, or an external URL. `CONFIRMED` requires offline-verifiable evidence.

## Typed checks

The verifier accepts only these check types:

- `file_exists`: an existing repository-relative file;
- `text_contains`: an existing repository-relative file and literal text;
- `pytest_node`: an existing repository-relative test file and node id; it is
  validated but never executed by the verifier;
- `git_commit_exists`: a commit SHA checked through local Git;
- `external_diagnostic`: declarative context only; it is never executed and does
  not confirm a cause by itself.

There is no shell or command field in the registry. Local files must be tracked
by Git and paths must remain inside the repository.

## Usage

Install the script-only dependency and run:

```bash
python3 -m pip install -r backend/scripts/requirements.txt
python3 backend/scripts/verify_error_registry.py
```

The baseline SHA, DB protection, diff allowlist and clean-state checks for
FBK-001 are temporary contract gates. They belong in
`docs/plans/FBK-001-progress.json` and the closeout procedure, not in the
permanent registry verifier.
