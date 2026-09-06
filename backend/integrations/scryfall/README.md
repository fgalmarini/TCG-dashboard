# Scryfall — Magic catalog / images

## Purpose

Magic-only provider for:

- identity / Scryfall IDs;
- sets and collector numbers;
- physical printings;
- finishes;
- metadata;
- images.

Scryfall pricing is not TCG Dashboard `current_price`.

## Authentication

Code: `auth.py`

No API key is required.

Scryfall asks API clients to send an explicit relevant `User-Agent` and `Accept`
header. Keep those request rules beside this integration.

## Downloadable upstream material

Useful official resources:

- API docs: https://scryfall.com/docs/api
- Bulk-data index: https://api.scryfall.com/bulk-data
- Official TypeScript API types: https://github.com/scryfall/api-types

For large catalog refreshes, prefer Scryfall bulk data instead of issuing repetitive
per-card requests. Bulk data is external source data and should be downloaded/cache
managed by the importing workflow; do not commit changing bulk datasets to this repo.

The official `api-types` package is useful as schema reference, but this backend is
Python, so do not vendor a TypeScript dependency solely for documentation.

## Rate-limit policy

Keep API traffic below Scryfall's documented threshold and avoid redundant requests.
Large lookup/image workloads should use their bulk offerings where applicable.
