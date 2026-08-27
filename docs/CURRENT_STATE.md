# Current State

## Phase

Current phase: Phase 7.

Phase 6 is closed. Magic LOTR Catalog + Wishlist v1 is implemented. The next
recommended task is historical market data: repeated price snapshots and price-trend
charts.

## Closed Work

- Phase 1: initial documentation and architecture.
- Phase 2: Cardmarket data investigation.
- Phase 3: SQLite schema in `backend/db/`.
- Phase 4: Cardmarket importer in `backend/importer/`.
- Additive Magic/Scryfall revision: Magic catalog backfill via Scryfall metadata.
- Phase 5: manual collection loading via CSV/script flow.
- Phase 6: basic dashboard with Overview and read-only Collection browsing.
- Additive Card Images revision: remote image metadata and exact CardTrader fallback,
  without renumbering the roadmap.

## Real Results

Phase 4 real importer run:

- 12,867 products in scope.
- 12,167 mapped cleanly.
- 700 flagged `ambiguous`, genuinely requiring review.
- 143 new expansions pending a name.

Magic/Scryfall backfill:

- 757 Magic/LOTR products processed.
- 550 resolved OK.
- 206 unmatched, mostly Art Series/tokens not indexed by Scryfall by Cardmarket ID.
- 1 unresolved `UNIQUE` collision deferred.
- `cards.data_source` and `cards.scryfall_raw` were added additively.

Phase 5 collection loading:

- 98/98 real rows processed.
- Current real collection is 100% Magic today.
- One Piece ambiguous batch UI was not needed for the real collection yet.

Phase 6 dashboard:

- `backend/api/` added as FastAPI API; Overview/Collection/Catalog are read-only and
  Wishlist has the explicitly scoped write operations.
- `frontend/` added as Vite/React/TypeScript/Tailwind/shadcn/ui/Recharts app.
- Verified `GET /api/overview`: `total_cards=101`, `unique_cards=98`,
  `cards_without_market_value.count=19`, `roi=-0.5212`.
- Verified `GET /api/collection`: `total=98` unfiltered, `total=79` with
  `?game=magic`.
- 20 backend API tests passed.
- Dark mode and 375px mobile width were verified with headless Chrome.
- Manual-entry detail rows never show an artificial zero for missing market prices.

Card Images / CardTrader fallback:

- `card_images` stores provider metadata and remote URLs without local image files.
- Scryfall remains primary; CardTrader is an exact fallback through Cardmarket Product ID.
- CardTrader expansion `3395` / `altr` exposes 81 normal and 81 Gold-Stamped card
  Blueprints, plus two set Blueprints without Cardmarket Product IDs.
- Apply resolved 45 CardTrader exact candidates, including 6 Gold-Stamped cards.
- Gold-Stamped owned coverage is `6/6` exact images, `0` missing and `0` ambiguous.
- CardTrader URLs are stored only in `image_url_large`; `image_url_small` is NULL.
- Existing collection, pricing, mapping and historical-price counts remained unchanged.
- Dashboard API reads `card_images` only and never performs provider network calls.

Catalog import result (2026-08-27):

- Scryfall returned 856 LTR and 591 LTC physical-set records before filtering.
- 2 digital LTR records were rejected; 854 LTR and 591 LTC records were accepted.
- Finish expansion produced 1,544 LTR and 761 LTC catalog rows.
- The live run was cached locally, applied to a validated DB copy and then synced to
  the project DB. Re-running from cache produced 0 inserts and 0 updates.
- Collection backfill reported 98 exact matches, 0 collector-only matches, 1
  unmatched legacy row without collector number and 0 ambiguous rows.

Magic LOTR Catalog + Wishlist v1:

- Catalog + Wishlist v1 está implementado.
- El catálogo físico LOTR de LTR/LTC contiene 2.305 registros por finish.
- Collection backfill: 98 matches exactos, 1 unmatched y 0 ambiguous.
- Wishlist funcional con add, remove, re-add y move-to-collection.
- El pricing ambiguo permanece `null`; nunca se sustituye por cero.
- Pendiente manual: `collection_item_id=70` — The Bath Song.
- `cards` is extended as the canonical catalog entity; existing `card_id` references
  remain compatible.
- Physical LTR/LTC cards are imported from controlled Scryfall pages or local
  fixture/cache files. Finish is part of identity; treatment is descriptive metadata.
- `wishlist_items` replaces the empty legacy `want_list_items` table and preserves
  removed/acquired history.
- Catalog and Wishlist screens/API are available. Prices remain NULL unless exactly
  one mapped Cardmarket product has a current snapshot.
- Catalog import and collection backfill are dry-run by default and report rejected,
  ambiguous and unmatched records.

## Display Currency

- The dashboard currently displays monetary values in USD.
- A USD/EUR display-currency selector is not implemented yet.
- No exchange-rate conversion is currently applied.

## Database Notes

- The real collection has 98 rows in `collection_items`.
- 79 rows have Cardmarket-backed Magic products and market prices.
- 19 rows are manual entries without market price.
- `purchase_currency` is currently `NULL` in the real collection; this stored field is
  unchanged and remains separate from the display currency.
- Market Value currently uses Cardmarket Trend Price.

## FUSE/SQLite Incident

During collection loading, the SQLite file lived in a bridge/FUSE-mounted folder that
did not support SQLite's journal cleanup at commit time, causing a `disk I/O error`.

The DB was recovered without data loss by copying the DB and journal to local disk,
letting SQLite roll back safely, checking integrity, and copying the healthy DB back.

Operational rule: future writes against this mounted SQLite DB should happen on a
local temporary copy, followed by `PRAGMA integrity_check` and
`PRAGMA foreign_key_check` before copying the DB back.

## Not In Scope Yet

- Trading, Trade Binder, Want List and Trade Calculator.
- Analytics and best/worst performer views.
- CARDMADNESS Mode.
- Collection-item editing from the web.
- Supabase/PostgreSQL migration.
- Scrapers or private Cardmarket API access.

## Next Recommended Task

Implement Phase 7: historical market data and price-trend charts.

Keep Cardmarket as the price source, preserve snapshots, report unmapped products and
avoid changing Trading/Analytics/CARDMADNESS scope during this phase.
