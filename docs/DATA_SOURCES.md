# Data Sources

Status: **authoritative external-provider map**.

If another document conflicts with this file about current external-provider roles,
this file plus `docs/decisions/TCG-DEC-009-external-data-provider-policy.md` governs
until the conflicting document is updated.

## Core rule

Internal card identity belongs to TCG Dashboard. External providers attach identifiers,
metadata, images, prices or analytics; they never become the internal primary key.

Provider calls run in maintenance/synchronization workflows. Normal FastAPI dashboard
reads consume normalized database rows and do not call external providers live.

## Provider matrix

| Concern | Provider | Role | Auth | Current status |
|---|---|---|---|---|
| Current EUR price | `cardmarketapi.com` | **PRIMARY** | `CARDMARKET_PRIMARY_API_KEY` | Accepted; POC/runtime migration pending |
| Current EUR price fallback | TCG Cardmarket API | **FALLBACK** | `TCG_CARDMARKET_API_KEY` | Accepted; POC/runtime migration pending |
| Pokémon catalog/images | TCGdex | Metadata/images only | none | Existing source; keep pricing excluded |
| Magic catalog/images | Scryfall | Metadata/images only | none | Existing source |
| Market analytics | TCG API | Secondary metrics / charts | `TCGAPI_KEY` | Free tier only |
| Pricing fallback | CardTrader | **Not used** | n/a | Outside new pricing architecture |

## Current-price policy

### PRIMARY — cardmarketapi.com

`cardmarketapi.com` is a third-party Cardmarket-data service, not Cardmarket's official
API.

Expected price filter:

- exact validated Cardmarket product ID;
- English;
- Near Mint or better;
- EUR.

The candidate field for official current value is the cheapest matching listing
(`prices.from`), subject to identity/filter validation.

A valid PRIMARY response wins. Do not query a second source merely because the price
looks high, low or surprising.

### FALLBACK — TCG Cardmarket API

Fallback activates only when PRIMARY:

1. times out / is unreachable;
2. returns HTTP/service failure;
3. returns no usable current price;
4. cannot resolve a Cardmarket product ID already validated by our DB.

Fallback does **not** activate to:

- resolve an ambiguous card identity;
- choose between variants/finishes;
- replace a valid PRIMARY result;
- select a more attractive price.

Decision flow:

```text
PRIMARY valid
  -> use PRIMARY

PRIMARY unavailable/invalid
  -> query FALLBACK

FALLBACK valid
  -> use FALLBACK and record provider provenance

PRIMARY invalid + FALLBACK invalid
  -> current_price = NULL
```

Never promote historical data to `current_price` merely because both providers fail.

## Valuation metric

During VAL-AVG30-005, `current_price` retains its existing Low-based semantics. A
validated Cardmarket product may additionally produce `valuation_value` from `avg30`
with `valuation_status=ESTIMATED` and `valuation_method=CARDMARKET_AVG30`, subject to
the existing physical-printing identity and metric-mapping evidence. This additive
field is not consumed by portfolio calculations or visible dashboard values yet.

## Pokémon — TCGdex

Use TCGdex for identity support, sets, collector numbers, variants, metadata and images.

Do not feed TCGdex market-price fields into official `current_price`.

Official downloadable/reproducible references:

- https://github.com/tcgdex/cards-database
- https://github.com/tcgdex/cards-database/blob/master/meta/definitions/openapi.yaml
- https://github.com/tcgdex/cards-database/releases

## Magic — Scryfall

Use Scryfall for Magic identity, sets, printings, finishes, metadata and images.

Do not feed Scryfall price fields into official `current_price`.

For bulk catalog work, use Scryfall's bulk-data mechanism rather than repetitive
per-card requests.

References:

- https://scryfall.com/docs/api
- https://api.scryfall.com/bulk-data
- https://github.com/scryfall/api-types

## Analytics — TCG API

TCG API is secondary market context, primarily TCGplayer/USD oriented.

Use it for:

- non-authoritative market metrics;
- movement/trend indicators;
- top movers;
- chart inputs;
- historical data only when the active Free tier actually exposes it.

Current plan restriction: **Free only**.

Free tier is documented at 100 requests/day. Public TCG API pages have not been fully
consistent about whether a short history window is included in Free. Therefore our
architecture must not depend on the `/history` endpoint while Free.

For guaranteed long-term charts without paying, store our own timestamped snapshots
from allowed endpoints. That history starts when we begin collecting it; it is not a
free backfill.

References:

- https://tcgapi.dev/authentication/
- https://tcgapi.dev/guides/rate-limits/
- https://tcgapi.dev/api-explorer/
- https://github.com/gordy-ftw/tcgapi-python

## Authentication rule

Authentication knowledge belongs beside the provider code:

```text
backend/integrations/<provider>/
  auth.py
  client.py
  README.md
```

`auth.py` defines **how** authentication works.

`.env` contains the actual secret.

`.env.example` lists only empty variable names and is safe to version.

No credential may be:

- hard-coded;
- committed;
- copied into provider README files;
- stored in fixtures;
- printed to logs;
- placed into query strings when a header is supported.

## Local documentation contract

Before changing a provider, an agent must read:

1. `AGENTS.md`;
2. this file;
3. `backend/integrations/<provider>/README.md`;
4. the relevant ADR under `docs/decisions/`.

If provider behavior, authentication, endpoint, limits, fallback semantics or scope
changes, update the provider README and this file in the same commit when the global
contract changes.

## Download / vendoring policy

Do not "download the API" into the repository.

Allowed:

- pin official OpenAPI/Swagger contracts when they materially help a sprint;
- use official SDK packages as dependencies;
- download bulk datasets into ignored cache/import locations;
- record upstream tag/commit/hash for reproducibility.

Avoid:

- vendoring changing full datasets into Git;
- copying whole documentation sites;
- committing third-party SDK source when a package is available;
- relying on undocumented endpoints.

## Runtime migration status

This document records the newly accepted provider architecture. It does **not** by
itself switch existing production pricing code.

Activation requires a controlled POC against known Magic, One Piece and Pokémon cards,
then explicit migration of the pricing synchronization path with tests and provenance.
