# TCGdex — Pokémon catalog / images

## Purpose

Pokémon-only provider for:

- card identity support;
- sets / collector numbers;
- variants;
- metadata;
- images.

It is **not** a `current_price` provider for TCG Dashboard, even if TCGdex exposes
market-price fields.

## Authentication

Code: `auth.py`

No API key is currently required.

## Downloadable upstream material

TCGdex is the strongest provider here for reproducible reference material:

- official card database repository:
  https://github.com/tcgdex/cards-database
- official OpenAPI 3.1 definition:
  https://github.com/tcgdex/cards-database/blob/master/meta/definitions/openapi.yaml
- raw OpenAPI file:
  https://raw.githubusercontent.com/tcgdex/cards-database/master/meta/definitions/openapi.yaml
- releases:
  https://github.com/tcgdex/cards-database/releases

The repository is MIT licensed and can be built/self-hosted.

### Local-reference policy

Do not vendor the full Pokémon database into TCG Dashboard by default. It is large and
changes independently.

If a sprint needs a pinned API contract, download the official `openapi.yaml` into a
temporary/reference artifact and record the upstream commit/tag used. Do not edit that
vendor copy manually.

## Price boundary

Any TCGdex Cardmarket/TCGplayer price fields are secondary evidence only and may not
feed `current_price`.
