# Architecture

## Current Stack

Frontend:

- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts
- Vite

Backend:

- Python
- FastAPI
- Direct `sqlite3` access for the local API

Database:

- SQLite initially
- PostgreSQL/Supabase remains a future possibility, not current scope

## Data Flow

```text
Cardmarket
  -> Price Guide / Product Catalogue
  -> Market Data Importer
  -> Validation / Normalization
  -> SQLite database
  -> FastAPI read API
  -> React dashboard
```

Cardmarket remains the primary European price source. Scryfall is metadata only for
the physical Magic LOTR catalog. One Piece uses CardTrader Blueprints for catalog and
exact-language images, exact Cardmarket products when language scope is proven, and
CardTrader Marketplace is never a pricing source. Provider calls run only in
maintenance commands, never during normal API reads.

Image providers are independent from market data. Magic keeps Scryfall exact images
with CardTrader exact fallback. One Piece accepts a CardTrader Blueprint image only
when its language is demonstrable; a controlled EN display fallback may fill a JP
visual slot only when the printing/artwork match is deterministic and is recorded as
non-exact language provenance.

```text
Printing (cards.id)
  ├── Magic: validated Cardmarket id + Low -> null
  └── One Piece: validated Cardmarket id + Low -> null
```

Collection may additionally expose the latest `market_price_observations` grouped by
provider, market and source variant. These observations preserve their source currency
and remain secondary display data; they never enter Cardmarket valuation or portfolio
calculations.

The curated HOB/HOC manual Cardmarket snapshot is stored only in
`market_price_observations` with fixed provenance and snapshot key. Event comparison
may read those metrics; current-price and portfolio valuation paths do not.

## Multi-TCG Domain

`cards.id` is the stable internal identity of a physical printing. A provider ID never
replaces it. `canonical_cards` groups logical cards, `sets` represents neutral releases,
and external-ID tables attach provider identifiers to canonical cards, printings or
sets. Existing Collection and Wishlist FKs remain compatible.

```text
Game -> Set / Release -> Canonical Card -> Printing (cards.id)
                                      -> language
                                      -> release_kind + art_kind
                                      -> external IDs + images + price history
```

Magic canonical grouping uses Oracle ID when available. One Piece grouping uses a
validated canonical card number; same-number/name conflicts are split and reported.
Its natural commercial identity is canonical card + release + source variant/art kind
+ language. CardTrader Blueprint ID is the principal external identifier, not an
internal key. Collisions remain separate rows with `catalog_status=ambiguous`.

`printing_count` includes all active physical printings of a canonical card, including
languages separately. `reprint_count` includes only `release_kind=reprint`; alternate
art alone does not imply reprint.

## Catalog And Wishlist

`wishlist_items` references the same card rows. Active wanted rows are unique per card;
removed and acquired rows remain for history. Wishlist state is planning-only: marking
an item acquired never creates or modifies a `collection_items` row.

Wishlist timestamps are state invariants: `wanted` has both timestamps NULL,
`acquired` has only `acquired_at`, and `removed` has only `removed_at`. Restoring a
historical row to `wanted` clears both timestamps. `target_price` and `max_price` are
optional and, when both exist, `target_price <= max_price` is enforced by the database.

Generic `events` link existing Wishlist rows through `event_wishlist_items`; links do
not own status, quantity or purchase targets. Wishlist transitions remain authoritative.
CARDMADNESS-001 uses this foundation for `cardmadness-2026`.

Catalog prices are nullable. One Piece resolution is exact Cardmarket printing and
language, then exact CardTrader Blueprint and language, then null. Mixed Cardmarket
prices remain auditable but never enter valuation. Decisions preserve provider,
currency, method, sample metrics, confidence and evaluated external ID.

## Frontend

The current frontend lives in `frontend/` and runs locally on `http://localhost:3000`.

For Event Mobile Access, the frontend binds to `127.0.0.1:3000` and proxies `/api/*`
to the private FastAPI process at `127.0.0.1:8000`. Cloudflare Tunnel and Cloudflare
Access expose and protect only the frontend origin. Cloudflare is transport and
authentication only; application state and SQLite remain local.

Collection, Catalog and Wishlist reads are game-generic and filter by game/language.
Collection supports only ownership-metadata edits through a strict item PATCH. One
Piece personal Collection entry remains disabled; catalog identity changes, Trading,
Analytics and CARDMADNESS remain deferred.

## Backend

The current API lives in `backend/api/` and runs locally on `http://localhost:8000`.

Event Mode keeps FastAPI private on `127.0.0.1:8000`; it is never configured as a
separate Cloudflare Tunnel origin.

Overview and Catalog reads are read-only except for their explicitly scoped actions.
Collection writes are limited to `PATCH /api/collection/{item_id}` ownership metadata
and the separate manual catalog-match resolver. Wishlist writes are scoped to `POST`,
`PATCH`, `DELETE`, `mark-acquired` and `restore`.

Importer and maintenance scripts live separately:

- `backend/importer/` for Cardmarket catalog/price importing.
- `backend/scripts/` for additive migrations, audits, manual collection loading and
  provider catalog backfills.

Do not couple the dashboard API to importer internals unnecessarily.

The repository-root `./update-prices` command is the source of truth for manual
pricing updates. It orchestrates Cardmarket for Magic and One Piece plus CardTrader's
exact-language One Piece fallback without importing or mutating the catalog. A dry
run is read-only. Apply creates an SQLite backup, acquires `BEGIN IMMEDIATE`, writes
only pricing/history tables in one transaction and validates integrity before and
after commit. It never replaces the database file, Collection or Wishlist.

## Database Principles

Use relational tables. Avoid storing the collection as one large JSON object.

Cards, sets/expansions, Cardmarket products, product mappings, price history,
collection entries and want-list entries should remain separate relational concepts.

`cardmarket_products` is source inventory and does not imply a resolved printing.
When one commercial product covers a canonical card across multiple physical
finishes, `cardmarket_product_printing_scopes` stores the canonical target, an
optional physical `card_id`, finish scope, compatible finishes, evidence and
`pricing_eligible`. A mapping can therefore be authoritative without becoming
price-eligible or being forced onto one physical printing.

When a product exposes separate Cardmarket metric families, such as `base` and
`foil`, `cardmarket_product_metric_mappings` stores one relationship per product
and metric family. It keeps canonical status, metric status, candidate physical
cards, source metric column names, evidence and `pricing_eligible` separate. It
does not store numeric prices and never implies that a metric was applied. A
`pricing_eligible` relationship requires product identity, canonical identity,
physical `card_id`, metric family and evidence of metric exclusivity; compatibility
alone is insufficient. Sampled product-page patterns may document a `SUPPORTED`
observation but never promote unobserved products to `EXACT`. Metric resolution is
offline-at-apply: external evidence is fetched, cached, hashed and reported before
any database copy is changed.

The schema must support multiple copies of the same card without duplicating the card
definition.

`card_images` stores remote image metadata per canonical card/printing, never per
physical collection copy. It stores provider, provider identifier, optional variant
and collector metadata, requested language, actual `image_language_scope`,
`is_language_fallback`, face index, match quality, status and remote URLs. CardTrader
exposes one URL, so it is stored as `image_url_large`; `image_url_small` remains NULL.
No image files, blobs, base64 data or proxy cache are stored. A One Piece JP row may
display an EN asset only when the printing/artwork match is deterministic; this is
presentation metadata and never changes language, identity or pricing.

## Historical Price Strategy

Market prices must be stored as historical snapshots. The application should not
replace an old price with a new price as the only record.

The legacy `current_price` remains Cardmarket Low during VAL-AVG30-005. Avg30 is stored
separately as additive `valuation_value` with `valuation_status` and
`valuation_method`; it does not yet replace portfolio calculations or visible values.
Trend and averages remain separate informational metrics. A current
`printing_price_resolutions` row, including a NULL price, has priority over all
historical rows; CardTrader is never a pricing fallback.
The Magic LOTR catalog pricing updater processes the 2,305 principal LTR/LTC printings;
the 45 active Art Series printings remain a separate scope and are not refreshed by
that run.

Initial update cadence is approximately weekly, with manual updates allowed. Failed or
ambiguous mappings must be reported instead of silently discarded.

`./update-prices` identifies the combined Cardmarket Product Catalogue and Price Guide
set by a stable manifest hash. Repeating the same source snapshot is idempotent; a
changed snapshot creates a new historical resolution, including an explicit null
decision when no exact price exists.

The first repair scope is `collection`. It creates exactly one current Cardmarket
resolution per `collection_item_id` and source, without changing global current
resolutions. Automatic EXACT evidence supersedes a manual Collection approval;
ambiguous, mismatched, missing and unpriced items receive an explicit current NULL.
Historical rows remain immutable evidence, and the API never falls back to them when
a scoped current NULL exists.

## Currency Handling

Monetary values must preserve their source currency. Display-currency conversion is a
presentation concern and must not alter the source data.

## Card Identification

Card identification should prefer stable identifiers:

- Internal `cards.id` for printing references
- Canonical card + release + variant/art + language for One Piece commercial identity
- Cardmarket Product ID
- CardTrader Blueprint ID as an external identifier
- Cardmarket expansion/product IDs
- Set code
- Card number
- Language and printing/version when available

Do not rely exclusively on card names. Different games and languages can have similar
or identical names.

## Data Integrity

Market data must never silently overwrite unrelated cards.

If a Cardmarket product cannot be confidently mapped:

- mark it as unmapped or ambiguous;
- report it;
- do not guess.

Incorrect pricing is worse than missing pricing.

## External Sources

Before implementing an external data integration:

1. Investigate the official or public source.
2. Verify current availability.
3. Verify the data format.
4. Verify update frequency.
5. Verify usage restrictions.
6. Document the source.
7. Only then implement the importer.

Do not implement unauthorized access methods, scrapers or undocumented endpoint
dependencies.

Dashboard requests only read resolved display rows from `card_images`. They never call
Scryfall or CardTrader. Provider calls are restricted to backend maintenance/backfill
processes, with Cardmarket Product ID matching, HTTPS validation and a finite image
host allowlist derived from the validated CardTrader catalog.

The Pokémon 151 finish-source audit is read-only and cache-first. Cardmarket public
listing access may document Reverse Holo semantics but must not be treated as a
finish-specific price unless the filtered listing result is reproducible. Structured
sources may be recorded as explicit secondary provenance: `source=pokemon_tcg_api`
with `underlying_market=cardmarket` for Cardmarket-derived Reverse fields, or
`source=tcgplayer` with `source_currency=USD` for finish-specific reference values.
Neither source silently populates Cardmarket EUR `current_price`.

Pokémon 151 TCGplayer secondary observations are stored in the generic
`market_price_observations` table, keyed by physical `cards.id`, provider, underlying
market, metric, currency and source snapshot. `source_updated_at` remains the
provider timestamp and `observed_at` records local ingestion. Catalog reads may show
these observations as a clearly secondary USD reference; Overview, Collection,
Wishlist, Top Cards and all valuation/P&L/ROI queries deliberately exclude them.

## Cardmarket Role

Cardmarket is the primary source for European market prices.

Use the public downloadable Price Guide and Product Catalogue when available. Do not
build the app around private Cardmarket API credentials; current project assumptions
explicitly say not to ask the user for them.

Important price metrics should remain separate when present, such as low, average,
trend, 1-day average, 7-day average and 30-day average. Do not invent fields not
provided by the data source.

For Pokémon 151, `reverseHolo*` fields from an external structured source remain a
separate candidate until exact identity, physical finish and source semantics are
reviewed. A present field with value zero is unavailable for pricing purposes, and
USD values are never converted implicitly to EUR.

## Scryfall Role

Scryfall may be used for Magic metadata/catalog enrichment through direct lookup by
Cardmarket product ID.

It does not replace Cardmarket and must not be used as a price source. It is not used
for One Piece or Pokémon.

## CardTrader Role

CardTrader remains an image/catalog evidence provider where explicitly documented;
it cannot assign current prices, populate pricing history, or act as a fallback.

Bandai EN/JP validates releases and card-number metadata through a versioned registry.
It is not scraped and is not a runtime dependency.

## Current Limits

- Local-first SQLite remains the active storage engine.
- Supabase/PostgreSQL is deferred and should be treated as its own future phase.
- Collection ownership metadata is editable via the strict item PATCH; changing card,
  language, finish, treatment, mappings or other catalog identity still uses controlled
  workflows and is not supported by the Collection editor.
- Trading, Analytics and CARDMADNESS are later phases.
- Pokémon 151 catalog is active in the neutral model; Collection/Wishlist actions
  remain disabled for Pokémon and no Pokémon primary pricing is populated.
- No scrapers or private Cardmarket API integrations are in scope.

## Scoped Pricing Resolution (`2026-08-31`)

Pricing work is explicitly separated into `collection`, `wishlist`, `catalog` and
the composite `all` scope. `printing_price_resolutions` uses the same table for all
three target types and enforces these mutually exclusive invariants:

- `global`: both target IDs are `NULL`;
- `collection`: only `collection_item_id` is set;
- `wishlist`: only `wishlist_item_id` is set.

The Wishlist writer selects `wanted` items by default and accepts `acquired`,
`removed` or `all` explicitly. Its current resolution is authoritative even when
`current_price` is `NULL`, so the API does not fall back to a global resolution or
history. Cardmarket product and history tables remain global source tables, but
writes are limited to product IDs selected by the active target. The additive
Wishlist migration is validated only on temporary copies/fixtures; it is not run
against the production SQLite database in this sprint.

## Pokémon 151 Manual Cardmarket Resolution

`POKEMON-151-004B` resolves only the canonical numbered identity of the 73
remaining Pokémon 151 Cardmarket products. The controlled review workspace is
`reports/pokemon_151/cardmarket_manual_resolution/03_manual_review.csv`; only
`approved`, `approved_collector_number` and `review_notes` are editable.

The apply gate verifies immutable evidence, requires the approved number to be
one of the presented candidates, and protects the existing 137 EXACT mappings
with a dynamically computed before/after hash. Canonical promotion never
infers or overwrites physical card or finish information and never enables
pricing. With zero valid approvals, apply is a true NO-OP and does not create
or replace a SQLite database.
