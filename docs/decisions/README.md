# Decisions

Human-readable ADR index for structural decisions in TCG Dashboard.

`conventions.json` is kept as a historical/machine-readable snapshot. These Markdown
ADRs are the primary human index.

| ID | Decision | Status |
|---|---|---|
| [TCG-DEC-001](TCG-DEC-001-scryfall-magic-catalog.md) | Use Scryfall as authoritative Magic/LOTR catalog metadata source | Implemented |
| [TCG-DEC-002](TCG-DEC-002-cards-data-source-scryfall-raw.md) | Add `cards.data_source` and `cards.scryfall_raw` | Implemented |
| [TCG-DEC-003](TCG-DEC-003-supabase-deferred.md) | Defer Supabase migration | Deferred |
| [TCG-DEC-004](TCG-DEC-004-manual-collection-review-csv.md) | Manual collection review via CSV roundtrip and row hash idempotency | Implemented |
| [TCG-DEC-005](TCG-DEC-005-dashboard-basic-scope.md) | Phase 6 basic dashboard scope and Trend Price market metric | Implemented |
| [TCG-DEC-006](TCG-DEC-006-remote-card-images.md) | Scryfall primary images with exact CardTrader fallback | Implemented |
| [TCG-DEC-007](TCG-DEC-007-magic-lotr-catalog-wishlist.md) | Magic LOTR catalog and wishlist | Implemented |
| [TCG-DEC-008](TCG-DEC-008-multi-tcg-one-piece-foundation.md) | Multi-TCG foundation and One Piece provider policy | Implemented |
| [TCG-DEC-009](TCG-DEC-009-external-data-provider-policy.md) | External provider roles, fallback and authentication co-location | Accepted; runtime migration pending |
| [TCG-DEC-010](TCG-DEC-010-avg30-resolver-dry-run.md) | Temporal Avg30 resolver dry-run and backfill readiness criteria | Accepted |
| [POKEMON-151](POKEMON-151-pricing-and-cardmarket-limitations.md) | Pokémon 151 catalog, Cardmarket limitations and TCGplayer secondary pricing policy | Implemented |
| [TCG-MOBILE-001](TCG-MOBILE-001-event-mobile-access.md) | Single public origin with local Vite proxy and private FastAPI | Implemented |
