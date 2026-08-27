# TCG-DEC-002 — Cards Data Source And Scryfall Raw

## Metadata

- ID: `TCG-DEC-002`
- Date: 2026-08-24
- Type: schema decision
- Status: implemented

## Decision

Add nullable columns to `cards`:

- `data_source`: source confidence marker such as `scryfall`, `cardmarket_heuristic`
  or `manual`.
- `scryfall_raw`: JSON text containing the raw Scryfall object when available.

The change is additive and does not alter pricing, collection or mapping tables.

## Context

Magic/Scryfall enrichment needed traceability. `printing_variant='other'` can mean
different things depending on whether it came from Scryfall metadata or Cardmarket
heuristics, so the data source must be explicit.

The raw Scryfall payload preserves structured variant metadata that a short
`variant_label` cannot fully represent.

## Consequences

- New DB installs include these columns through `schema.sql`.
- Existing DBs are migrated idempotently by the backfill script.
- Magic cards enriched by Scryfall keep a stronger provenance trail.
- `cardmarket_products`, `cardmarket_product_mappings`, `market_price_history`,
  `collection_items` and `want_list_items` remain unchanged by this decision.

## References

- `docs/plans/fase5-scryfall-magic-backfill-sprint-contract.md`
- `docs/plans/Revisión-fases 2-4 — Catálogo externo .md`
- `conventions.json`
