# TCG-DEC-001 — Scryfall Magic Catalog Metadata

## Metadata

- ID: `TCG-DEC-001`
- Date: 2026-08-24
- Type: architecture decision
- Status: implemented

## Decision

Magic/LOTR catalog population pivots to Scryfall metadata through
`GET /cards/cardmarket/:id`, using Cardmarket `idProduct` as the direct lookup key.

One Piece and Pokemon keep the existing self-healing/manual-entry approach.

Cardmarket remains the only price source. Scryfall is catalog metadata only.

## Context

For Magic, Scryfall provides a stable, free, direct lookup by Cardmarket product ID and
returns metadata such as name, set, collector number, variants and images.

For One Piece, no equivalent source was verified with the same confidence. The real
Phase 4 issue was not missing catalog metadata; it was 700 genuine ambiguous variant
groups where prices were too close to infer the correct product automatically.

For Pokemon, the collection was small and no direct Cardmarket product lookup was
available, so name/set matching was not justified.

## Consequences

- Magic catalog data can be enriched authoritatively without expanding the Cardmarket
  price model.
- One Piece ambiguity remains a manual review problem.
- Pokemon remains manual unless the collection grows enough to justify integration.
- Reopen this decision only if new evidence provides a direct, reliable lookup source.

## References

- `docs/plans/Revisión-fases 2-4 — Catálogo externo .md`
- `docs/plans/fase5-scryfall-magic-backfill-sprint-contract.md`
- `conventions.json`
