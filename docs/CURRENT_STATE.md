# Current State

## Phase

Current phase: Phase 7.

`TCG-MOBILE-001` Event Mobile Access is implemented. Event Mode runs FastAPI and
Vite locally, exposes one same-origin URL through a Cloudflare Named Tunnel protected
by Cloudflare Access, and keeps SQLite local. Use `docs/EVENT_MOBILE_ACCESS.md` for
one-time setup and event operation.

Phase 6 is closed. Magic LOTR Catalog + Wishlist v1 and Wishlist Planning Mode are
implemented. Multi-TCG Foundation + One Piece Catalog is implemented with a validated
database cut at `2026-08-27`. The next recommended task is historical market data:
repeated price snapshots and price-trend charts.

TCG-UX-001 Interaction Stability & English UI (`2026-09-02`): inline mutations now
use `useApi` background refreshes that preserve the current content and approximate
scroll position. The dashboard UI is English-only, and Collection Card Data uses the
ordered, non-empty metadata presentation without displaying Condition. No backend,
database, pricing, mapping or collection/wishlist model changes were made.

Pricing catalog coverage update (`2026-09-02`): the existing `./update-prices` workflow
now permits a productive `--scope catalog --apply` run. Its Magic catalog worklist
excludes the 45 active Art Series printings and targets the 2,305 principal LTR/LTC
printings. Pokémon 151 TCGplayer observations remain visible only as secondary USD
references in Catalog; they remain excluded from Collection, Overview and EUR valuation.

Pricing catalog resolution update (`2026-09-03`): the read-only Magic audit now treats
Scryfall Cardmarket IDs as non-authoritative hints and recovers only candidates proven
by the local expansion, compatible printing identity and finish metric. The dry-run
result is 970 EXACT, 1,153 AMBIGUOUS, 120 MISMATCH and 62 UNPRICED across the 2,305
principal printings; no apply was run. Pokémon 151 TCGplayer observations are now also
exposed in Collection as secondary USD data without changing Cardmarket-based valuation.

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

Overview / Collection / Catalog visual adjustments (`2026-08-28`):

- Overview no longer renders P/L, ROI or the value-by-TCG chart; existing backend
  calculations remain available for other consumers and detail views.
- `GET /api/overview` now returns up to 10 `top_cards`, ranked by current price per
  Collection row without multiplying by quantity. Each entry includes image metadata
  and variation against the immediately previous valid snapshot for the same pricing
  identity; insufficient history remains `null`.
- Collection and Catalog grids share a fixed-height card shell with aligned identity,
  metadata, price and action zones. Image-based hover decoration is frontend-only,
  limited to real hover devices and disabled motion where requested.
- Set codes use a centralized frontend formatter and display in uppercase across the
  requested views without changing persisted values.
- Verification: 128 backend tests passed; frontend build passed; lint passed with two
  existing Fast Refresh warnings in UI primitives; `git diff --check` passed. Manual
  browser checks passed at 1280px and 375px with no horizontal overflow and uniform
  grid card heights.

One Piece JP image fallback (`2026-08-28`):

- Root cause confirmed: 6,506 active JP rows had CardTrader image records marked
  `missing` because Blueprint language was not demonstrably exact; API and frontend
  correctly exposed no image for those rows.
- 6,487 deterministic EN display fallbacks were applied using shared Blueprint IDs;
  19 active JP rows remain missing because their artwork/printing match is ambiguous.
- Exact JP coverage remains 340/6,846 (4.97%); visual coverage is 6,827/6,846
  (99.72%). EN images and all pricing rows remain unchanged.

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
- Wishlist Planning Mode con filtros, prioridades, precios objetivo/máximos, resumen
  global, Buying Mode, CSV y transiciones wanted/acquired/removed sin tocar Collection.
- El resumen global cuenta filas: `wanted`, `acquired`, `missing_price` y `unmatched`;
  `estimated_total` usa únicamente `current_price * quantity_wanted` de filas wanted.
- Resolver manual disponible para Collection unmatched; `collection_item_id=70` es el
  regression case de The Bath Song y los mappings compartidos no se reasignan sin
  comprobar su alcance.
- El pricing ambiguo permanece `null`; nunca se sustituye por cero.
- `collection_item_id=70` — The Bath Song queda disponible para resolución manual desde
  la interfaz de candidatos del catálogo.
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

Multi-TCG Foundation + One Piece Catalog (`2026-08-27`):

- Migration is additive; all 11,502 pre-existing One Piece rows and their `cards.id`
  values were preserved.
- Before: 11,502 rows, 2,847 card numbers, 0 Blueprint IDs, 0 exact images, 2,315
  unknown/ambiguous legacy variants and 26 legacy duplicate-identity groups.
- After: 22,083 rows total; 13,684 active, 38 commercial-identity collisions retained
  as `ambiguous`, and 8,361 unmatched legacy rows retained as `legacy`.
- 7,148 distinct Blueprints produced 6,850 EN and 6,872 JP external-ID printings;
  second import produced 0 inserts and 0 duplicate `Blueprint + language` groups.
- 3,210 One Piece canonical cards and 89 active releases are exposed by the API.
- 7,129 printings have an exact-language image; 6,593 language/image combinations
  remain explicitly missing.
- Pricing: 10,997 exact-language CardTrader median-5 decisions, 2,432 mixed Cardmarket
  prices rejected from valuation and 293 rows with no exact-language price. No exact
  Cardmarket product had a provable single-language scope in this source cut.
- Price confidence: 9,230 high, 740 medium and 1,027 low. Null prices remain null and
  no non-null zero prices were introduced.
- 90 of 98 provider releases were imported. Eight future/incomplete releases were
  excluded by registry or absent released-Cardmarket evidence.
- Magic regression remains LTR 1,544 + LTC 761 = 2,305.
- Catalog, Collection and Wishlist APIs/UI now support game/language filtering, dynamic
  sets, printing detail, reprint counts and pricing provenance. One Piece Collection
  entry remains disabled.

Pokémon Scarlet & Violet—151 Catalog Foundation (`2026-09-01`):

- `games.pokemon` is active and the generic catalog now exposes set `mew` / Scarlet &
  Violet—151, with Cardmarket expansion `5328` preserved only as set-level identity.
- The audited official checklist imported exactly 207 canonical numbered identities and
  all numbers `001–207`; same-name alternate numbers remain separate identities.
- 362 physical printings were imported from 362 `CONFIRMED` finish observations:
  128 normal, 81 holo and 153 reverse holo. The 23 `SUPPORTED` treatment observations
  remain provenance-only and were not promoted.
- 362 exact TCGdex image records are present, keyed by the numbered printing. No image
  fallback by Pokémon name/artwork is used.
- Pokémon has 137 canonical Cardmarket `EXACT` mappings, 73 canonical
  `AMBIGUOUS` mappings, 0 price snapshots, 0 pricing resolutions and 0 populated
  current/market values. The 73 ambiguous products remain intentionally deferred
  to controlled human review.
- Collection and Wishlist actions are disabled for Pokémon through catalog capabilities;
  Magic and One Piece behavior is unchanged. Catalog API returns both physical-row and
  distinct-identity counts.
- Import was applied on a validated SQLite copy with a backup; second dry-run is a
  no-op, database integrity and foreign-key checks pass.

Pokémon 151 Cardmarket Exact Mapping (`2026-09-01`):

- All 210 local Cardmarket products for expansion `5328` were re-evaluated against
  the authoritative 001 catalog: 137 `EXACT`, 73 `AMBIGUOUS`, 0 `PROBABLE`, 0
  `MISMATCH` and 0 `UNRESOLVED`. The 137 result is evidence-driven, not a quota.
- `cardmarket_products` remains source inventory independent of mapping state.
  The generic `cardmarket_product_printing_scopes` relation preserves canonical
  identity, nullable physical target, finish scope, compatible finishes, evidence
  and `pricing_eligible=0`.
- The 137 exact mappings are authoritative at canonical level; none is forced onto
  a physical `card_id` because current finish evidence is multi-scope or unknown.
  The remaining 73 products are present only in mapping reports/manual review.
- No Cardmarket price data, price history, pricing resolution, current value,
  Collection or Wishlist row was changed. Magic and One Piece remain unchanged.
- Mapping apply used a validated SQLite copy and backup; post-apply dry-run reports
  zero new products and zero new mappings. This canonical mapping remains separate
  from physical finish pricing.

Pokémon 151 Cardmarket Finish Semantics (`2026-09-01`):

- `POKEMON-151-002C` reviewed the 137 canonical `EXACT` products as 270 independent
  metric families: 137 `base` and 133 `foil`. The 73 canonical `AMBIGUOUS` products
  produced no metric rows.
- The local Price Guide snapshot is authoritative for field presence: `low`, `trend`,
  `avg1`, `avg7`, `avg30` and `low-holo`, `trend-holo`, `avg1-holo`, `avg7-holo`,
  `avg30-holo`. No numeric metric was persisted or converted into a current price.
- Result: 0 `EXACT`, 0 `SUPPORTED`, 266 `AMBIGUOUS`, 4 `UNRESOLVED`, 0 `MISMATCH`
  and 0 `pricing_eligible`. No global `base=normal` or `foil=reverse_holo` rule was
  applied; exclusivity remains unproven.
- Current Cardmarket Help Center semantics were cached successfully. The direct API
  documentation/legacy PriceGuide URLs returned `410 Gone`, and the 20 sampled
  public product pages returned `403 BLOCKED`; no bypass or undocumented request was
  attempted. Legacy documentation was not used as sole `EXACT` evidence.
- Apply required `--offline` and consumed only the cached, hashed evidence. It wrote
  only the metric relation schema/status state on a validated SQLite copy, inserted
  0 new metric rows, and left prices, snapshots, resolutions, Collection, Wishlist,
  Magic and One Piece unchanged. The operation is idempotent.

Pokémon 151 Reverse Holo Pricing Source Resolution (`2026-09-01`):

- `POKEMON-151-002D` was executed as a read-only source audit. It reviewed all 207
  numbered identities and all 362 physical printings without writing SQLite or
  enabling pricing.
- Route 1 Cardmarket public-page automation is `BLOCKED` for the 20-card sample
  (`403`). Reverse Holo remains a listing attribute, but direct finish-specific Low
  was not demonstrated and no bypass/manual automation was added.
- Pokémon TCG API returned current data for all 207 identities through cached bulk /
  documented individual-card fallback. `reverseHoloLow` is present in `207/207`
  responses and positive in `149/207`; positive Cardmarket-derived Reverse coverage
  intersects `142` local reverse printings after exact identity validation.
- Pokémon TCG API TCGplayer coverage is finish-specific for 123 normal, 72 holo and
  146 reverse identities with usable values. TCGdex independently returned 207 card
  records and finish-specific TCGplayer coverage for 123 normal, 72 holo and 148
  reverse identities. Source identity mismatches remain reported rather than merged.
- The recommendation is `OPTION C`: Cardmarket direct exact-finish EUR remains
  primary; Cardmarket-derived external Reverse is classified separately; TCGplayer
  remains USD secondary reference; unsupported Reverse dashboard prices remain NULL.
- All API/page/document responses were cached with URL, timestamp, HTTP status and
  SHA-256. A second offline run reproduced the same result. No price, snapshot,
  resolution, Collection, Wishlist, Magic or One Piece data changed. `POKEMON-151-003`
  was not executed.

Pokémon 151 Metric → Finish Resolution (`2026-09-01`):

- The 137 canonical `EXACT` products were evaluated independently by metric family:
  137 `base` and 133 `foil` relationships, for 270 metric relationships total.
- The local Price Guide exposes only the real columns `low`, `trend`, `avg1`,
  `avg7`, `avg30` and their `-holo` counterparts. Numeric values were not stored.
- 266 metric relationships remain `AMBIGUOUS` and 4 `UNRESOLVED`; 0 were promoted
  to `EXACT` or `pricing_eligible` because no product-level Cardmarket evidence
  distinguishes a metric family from a physical finish.
- The generic `cardmarket_product_metric_mappings` relation stores one row per
  product/family and preserves candidate cards and provenance. The 73 canonical
  `AMBIGUOUS` products remain untouched.
- No prices, snapshots, resolutions, Collection, Wishlist, Magic or One Piece rows
  changed. Apply used a validated SQLite copy with backup and is idempotent.

## Display Currency

- Market prices are displayed in their stored source currency (current providers: EUR).
- A USD/EUR display-currency selector is not implemented yet.
- No exchange-rate conversion is currently applied.

## Database Notes

- The real collection currently has 99 rows in `collection_items`, referencing 98
  distinct Magic cards/products.
- All 98 distinct collection products have a current Cardmarket snapshot; no current
  Collection row is represented by an artificial zero price.
- `purchase_currency` is currently `NULL` in the real collection; this stored field is
  unchanged and remains separate from the display currency.
- Market Value uses Cardmarket Low. Cardmarket Trend remains exposed separately as
  an informational market reference; unresolved or unsafe current prices are NULL.
- The first repair invocation is explicitly `./update-prices --apply --scope collection`;
  catalog and wishlist remain outside that transaction until separately selected.

## FUSE/SQLite Incident

During collection loading, the SQLite file lived in a bridge/FUSE-mounted folder that
did not support SQLite's journal cleanup at commit time, causing a `disk I/O error`.

The DB was recovered without data loss by copying the DB and journal to local disk,
letting SQLite roll back safely, checking integrity, and copying the healthy DB back.

Operational rule: future writes against this mounted SQLite DB should happen on a
local temporary copy, followed by `PRAGMA integrity_check` and
`PRAGMA foreign_key_check` before copying the DB back.

## Not In Scope Yet

- Trading, Trade Binder and Trade Calculator.
- Analytics and best/worst performer views.
- CARDMADNESS Mode.
- Collection-item editing from the web.
- Supabase/PostgreSQL migration.
- Scrapers or private Cardmarket API access.

## Next Recommended Task

The manual pricing update workflow is implemented as the first Phase 7 maintenance
capability. Historical price-trend charts remain the next product-facing task.

Keep Cardmarket as the price source, preserve snapshots, report unmapped products and
avoid changing Trading/Analytics/CARDMADNESS scope during this phase.

## Manual Pricing Update Workflow

- `./update-prices --dry-run` and `./update-prices --apply` update Magic and One Piece;
  `--game magic|one_piece` narrows the run.
- Magic reuses Cardmarket's existing Price Guide and `market_price_history`.
- One Piece uses exact Cardmarket language first, then exact CardTrader Blueprint
  Marketplace median-5; mixed-language Cardmarket prices never enter valuation.
- Apply creates a recoverable SQLite backup, uses `BEGIN IMMEDIATE`, commits one
  logical transaction and never replaces the DB file or changes Collection/Wishlist.
- Repeated identical source snapshots are deduplicated by source timestamp/fingerprint.
- JSON audit logs are written to local `logs/pricing/` and backups to
  `backups/pricing/`; both paths are ignored by Git.

## Magic LOTR Art Series Catalog (`2026-08-28`)

- The existing 162 Cardmarket Art Series products (expansion `5308`) remain
  one-to-one with existing legacy `cards.id` rows; the backfill creates no cards.
- Verified rows are promoted in place with `catalog_status=active`,
  `finish=nonfoil`, `release_kind=special`, `art_kind=special` and
  `catalog_source=cardmarket`. `data_source`, `scryfall_id` and `scryfall_raw`
  remain unchanged.
- Variant evidence is read from a local CardTrader export first and exact
  CardTrader image metadata second. Gold-Stamped uses `treatment` and
  `source_variant`; both variants keep technical finish `nonfoil`.
- The 45 Art Series currently owned by the user were physically confirmed as
  Gold-Stamped and are now represented as `treatment='Art Series Gold-Stamped'`
  and `source_variant='art_series_gold_stamped'`. The remaining 117 product rows
  stay legacy and are not promoted automatically.
- This Collection-only correction does not change `card_id`, mappings, snapshots,
  images, quantities, purchase prices, Wishlist or `match_status`.
- Manual candidates use the exact Cardmarket product mapping first and otherwise
  an exact Art Series name/set/`ART-n` fallback. Candidates are always active;
  Art Series names cannot resolve to playable cards with similar names.
- Apply runs operate on a temporary SQLite copy, validate integrity and foreign
  keys, save a recoverable backup, and only then copy the validated DB back.

## Collection-first Pricing Checkpoint (`2026-08-30`)

- Collection-first pricing is **COMPLETE**: 120 Collection items, with Magic `97/97`
  and One Piece `23/23` exact Cardmarket identities.
- Pricing outcome: `119` items priced from the selected Cardmarket Low metric and `1`
  item UNPRICED. Item 65 remains an exact foil identity with `current_price=NULL`
  because its Foil Low is unavailable; the base Low is never used as a fallback.
- One Piece resolved Cardmarket Low value is **EUR 58.55** (`23` exact rows, quantity
  applied). The generic aggregate is `SUM(selected Cardmarket Low * quantity)` over
  exact rows only; missing selected Low contributes zero to the aggregate while its
  persisted current price remains NULL.
- Reporting fix: manual Collection approvals now refresh contributions before
  aggregation, and reporting distinguishes exact-but-unpriced rows from identity
  status. Cardmarket Trend, AVG7, CardTrader, legacy prices, other finishes and
  language variants are excluded from Resolved Low.
- Dry-run and post-apply validation are read-only with respect to Collection/Wishlist;
  no new apply is part of this checkpoint. DB SHA-256 before/after remains
  `38959ecb8224c9c4e06c00dbc7ccda37d17660c828b72be0418f1419c1437aff`.
- Next recommended scope is Wishlist; this checkpoint does not claim Wishlist pricing
  is resolved.

## Wishlist Scope Safety (`2026-08-31`)

- The safe scoped pricing sprint is implemented and validated with temporary DB
  copies/fixtures only. No production apply or production migration was executed.
- `--scope wishlist` defaults to `--wishlist-status wanted`; it processes only active
  Wishlist targets and writes `resolution_scope='wishlist'` with
  `wishlist_item_id` set and `collection_item_id` NULL.
- Wishlist current rows, including NULL prices, block global/history fallback in the
  Wishlist API. Global, Collection and Wishlist resolution invariants are checked by
  schema, migration validation and writers.
- The production DB SHA-256 remains
  `38959ecb8224c9c4e06c00dbc7ccda37d17660c828b72be0418f1419c1437aff`.

## Pokémon 151 TCGplayer Secondary Pricing (`2026-09-01`)

- `POKEMON-151-003` is implemented using the generic
  `market_price_observations` table. It stores one positive metric per physical
  printing and source snapshot, with explicit provider, underlying market,
  currency, `source_updated_at`, local `observed_at` and `snapshot_key`.
- Pokémon TCG API is the persistence authority for TCGplayer USD observations;
  TCGdex is retained as a cross-check. Exact coverage is `339/362`: `121/128`
  normal, `72/81` holo and `146/153` reverse holo. `1,676` metric observations
  were imported: low, market, mid and high for all eligible printings, plus
  direct_low where documented and present.
- Numeric differences are diagnostic only. The reports include p50, p75, p90
  and max distributions; `20%` remains a `diagnostic_threshold_candidate` and
  does not block exact identity/finish mappings. TCGdex identity or finish
  conflicts remain blocked.
- TCGplayer observations never participate in Overview, Collection, Wishlist,
  Top Cards, valuation, P&L, ROI, `current_price` or `market_value`. Cardmarket
  remains the primary valuation source and all USD values remain unconverted.
- Apply completed on a validated temporary SQLite copy with backup. Integrity
  check and foreign-key check pass. The second apply is a no-op. DB SHA-256:
  `e2336e47d414f10729ab4d1f78cffbb941d23f4b0dc8e57fe7282c5d4b8e2633` before,
  `bce907591a43dbbff620fced5ef192fa08c94d303aa14991d486077706f25b73` after.

## Pokémon 151 Cardmarket Manual Mapping Resolution (`2026-09-01`)

- Manual review workflow prepared: COMPLETE. The sole editable source is
  `reports/pokemon_151/cardmarket_manual_resolution/03_manual_review.csv`, with
  exactly 73 rows and `approved=false` by default.
- Manual mappings actually resolved: `0` in the current source cut. All 73
  products remain pending human approval; generating the workspace does not
  count a product as reviewed or resolved.
- The apply gate validates immutable CSV evidence, candidate membership,
  duplicate `idProduct` rows and the protected existing 137 EXACT mappings.
  With zero valid approvals, apply is a true NO-OP: no backup, SQLite copy,
  transaction or database replacement; the DB SHA remains unchanged.
- No Cardmarket prices, physical finishes, metric mappings, `pricing_eligible`,
  TCGplayer observations, Magic, One Piece, Collection or Wishlist data changed.

## Pokémon 151 Foundation & Pricing Discovery — Consolidated Closeout (`2026-09-02`)

- `POKEMON-151-000`, `000B`, `001`, `002`, `002B`, `002C`, `002D`, `003` and
  `004B` are COMPLETE for the implemented scope.
- Catalog: `207/207` canonical identities, `362` physical printings (`128`
  normal, `81` holo, `153` reverse holo) and `362/362` exact TCGdex images.
- Cardmarket: `210` products, `137` canonical `EXACT`, `73` canonical
  `AMBIGUOUS`, `0` exact physical metric mappings and `0` pricing-eligible
  mappings. The 73 unresolved products are a known source limitation, not a
  system defect, and remain deferred rather than guessed.
- The live DB also retains the later `004B` canonical-scope apply: all `210`
  products have canonical scope rows, while physical finish evidence remains
  non-exclusive and pricing eligibility remains `0`. The `002C` metric audit
  tests therefore use the immutable pre-`004B` DB backup as their explicit
  137-product baseline.
- TCGplayer: `339/362` physical printings with `1,676` secondary observations in
  USD, stored through `market_price_observations` with Pokémon TCG API authority
  and TCGdex cross-check only.
- Primary pricing policy is unchanged: exact Cardmarket Low for the physical
  printing is the only source for `current_price` and `market_value`; otherwise
  both remain `NULL`. TCGplayer never enters valuation or primary-price fallback.
- Protected behavior: Magic, One Piece, Collection, Wishlist, existing mappings,
  Cardmarket pricing and TCGplayer observations are unchanged by closeout.
- Audit evidence is retained under `reports/pokemon_151/` in the directories
  `cardmarket_discovery`, `identity_discovery`, `catalog_import`,
  `cardmarket_mapping`, `cardmarket_metric_mapping`, `cardmarket_semantics`,
  `finish_pricing_sources`, `tcgplayer_pricing` and `cardmarket_manual_resolution`.
- Deferred: resolve the 73 Cardmarket ambiguous products only when deterministic
  Cardmarket-specific or otherwise trustworthy evidence becomes available.
