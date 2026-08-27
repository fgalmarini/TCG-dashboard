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
- Direct `sqlite3` access for the read-only API

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

Cardmarket remains the price source. Scryfall is metadata only for the physical Magic
LOTR catalog; maintenance uses controlled paginated requests or local fixtures/cache
and never runs during normal API reads.

Image providers are independent from market data. Scryfall is the primary Magic
image provider. CardTrader is an exact fallback currently scoped to the LOTR Art
Series expansion (CardTrader expansion `3395`, code `altr`), matched only through
an existing Cardmarket Product ID and a unique Blueprint.

```text
cards.cardmarket_id_product
          │
          ├── Scryfall direct lookup / cards.scryfall_raw
          │       └── exact image
          │
          └── CardTrader Blueprint lookup (fallback)
                  └── unique card_market_ids match → remote image_url
```

## Catalog And Wishlist

The existing `cards` table is the canonical catalog entity. It represents a printing,
including language and real finish. `treatment` is descriptive metadata and is not an
identity field. Existing `collection_items.card_id` remains the compatible FK.

`wishlist_items` references the same card rows. Active wanted rows are unique per card;
removed and acquired rows remain for history.

Catalog prices are nullable. A Cardmarket price is shown only when exactly one mapped
product with a current snapshot exists. The API never guesses between products.

## Frontend

The current frontend lives in `frontend/` and runs locally on `http://localhost:3000`.

Phase 6 implemented Overview and read-only Collection browsing. Phase 7 adds Catalog
and Wishlist writes only; collection editing, Trading, Analytics and CARDMADNESS remain
deferred.

## Backend

The current API lives in `backend/api/` and runs locally on `http://localhost:8000`.

Overview, Collection and Catalog reads are read-only. Wishlist writes are explicitly
scoped to `POST`, `PATCH`, `DELETE` and `move-to-collection`; collection editing itself
still uses the CSV/script flow.

Importer and maintenance scripts live separately:

- `backend/importer/` for Cardmarket catalog/price importing.
- `backend/scripts/` for manual collection loading and Magic/Scryfall backfill.

Do not couple the dashboard API to importer internals unnecessarily.

## Database Principles

Use relational tables. Avoid storing the collection as one large JSON object.

Cards, sets/expansions, Cardmarket products, product mappings, price history,
collection entries and want-list entries should remain separate relational concepts.

The schema must support multiple copies of the same card without duplicating the card
definition.

`card_images` stores remote image metadata per canonical card/printing, never per
physical collection copy. It stores provider, provider identifier, optional variant
and collector metadata, face index, match quality, status and remote URLs. CardTrader
exposes one URL, so it is stored as `image_url_large`; `image_url_small` remains NULL.
No image files, blobs, base64 data or proxy cache are stored.

## Historical Price Strategy

Market prices must be stored as historical snapshots. The application should not
replace an old price with a new price as the only record.

The current market value is derived from the latest relevant row in
`market_price_history`.

Initial update cadence is approximately weekly, with manual updates allowed. Failed or
ambiguous mappings must be reported instead of silently discarded.

## Currency Handling

Monetary values must preserve their source currency. Display-currency conversion is a
presentation concern and must not alter the source data.

## Card Identification

Card identification should prefer stable identifiers:

- Cardmarket Product ID
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

Dashboard requests only read resolved exact rows from `card_images`. They never call
Scryfall or CardTrader. Provider calls are restricted to backend maintenance/backfill
processes, with Cardmarket Product ID matching, HTTPS validation and a finite image
host allowlist derived from the validated CardTrader catalog.

## Cardmarket Role

Cardmarket is the primary source for European market prices.

Use the public downloadable Price Guide and Product Catalogue when available. Do not
build the app around private Cardmarket API credentials; current project assumptions
explicitly say not to ask the user for them.

Important price metrics should remain separate when present, such as low, average,
trend, 1-day average, 7-day average and 30-day average. Do not invent fields not
provided by the data source.

## Scryfall Role

Scryfall may be used for Magic metadata/catalog enrichment through direct lookup by
Cardmarket product ID.

It does not replace Cardmarket and must not be used as a price source in this project.
One Piece and Pokemon keep their existing self-healing/manual-entry approach until a
similarly reliable source is verified.

## CardTrader Role

CardTrader is not a price source. Its image fallback is exact only when one existing
Cardmarket Product ID maps to exactly one Blueprint. Zero matches are missing and
multiple matches are ambiguous. Blueprint `version` and `fixed_properties.collector_number`
are preserved for variant traceability; Gold Stamp is never inferred from a name.

## Current Limits

- Local-first SQLite remains the active storage engine.
- Supabase/PostgreSQL is deferred and should be treated as its own future phase.
- Collection editing is still performed via CSV/script flow, not the web UI.
- Trading, Analytics and CARDMADNESS are later phases.
- No scrapers or private Cardmarket API integrations are in scope.
