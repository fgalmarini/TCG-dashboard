# TCG-DEC-004 — Manual Collection Review CSV

## Metadata

- ID: `TCG-DEC-004`
- Date: 2026-08-24
- Type: architecture decision
- Status: implemented

## Decision

Manual collection loading uses a CSV review roundtrip for ambiguous candidates instead
of terminal prompts or automatic assignment.

Idempotency between loader runs is handled by a local row-hash state file, not by a new
database uniqueness constraint.

## Context

`collection_items` intentionally has no natural unique key because the collection may
contain multiple copies of the same card. The loader still needed protection from
duplicate imports across repeated CSV runs.

The review queue was designed for One Piece ambiguous variants, but the real
collection loaded during Phase 5 was 100% Magic and still used review mechanics for
Magic ambiguous candidates.

## Consequences

- Ambiguous rows are exported for human choice with `chosen_card_id`.
- `--apply-review` inserts chosen rows and skips incomplete choices without silently
  losing them.
- The local state file avoids duplicate imports without changing the schema.
- Future One Piece additions may reuse the same review flow.
- A FUSE/SQLite incident during this phase created the operational rule to write DB
  changes on a local copy before syncing back.

## References

- `docs/plans/fase5-alta-manual-coleccion-sprint-contract.md`
- `conventions.json`
