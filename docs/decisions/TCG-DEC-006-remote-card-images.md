# TCG-DEC-006 — Remote Card Images And Exact CardTrader Fallback

## Status

Implemented.

## Decision

Card images are stored as normalized remote metadata in `card_images`, independently
from Cardmarket prices and physical collection copies.

Scryfall is the primary Magic image provider. Existing `cards.scryfall_raw` data and
direct Cardmarket Product ID lookups are preferred. CardTrader is an exact fallback
for the validated LOTR Art Series catalog, initially expansion `3395` / `altr`.

The only permitted CardTrader match is:

```text
existing cards.cardmarket_id_product
    -> Blueprint.card_market_ids
    -> exactly one Blueprint
```

Zero matches are `missing`; more than one Blueprint is `ambiguous`. Names, fuzzy
matching, artwork similarity and collector-number guessing are prohibited.

## Stored Data

CardTrader stores its Blueprint ID in `source_card_id`, its exact `version` in
`source_variant`, and `fixed_properties.collector_number` in
`source_collector_number`. CardTrader's single official `image_url` is stored as
`image_url_large`; no thumbnail URL is fabricated, and `image_url_small` remains NULL.

Only HTTPS URLs whose host belongs to the finite allowlist observed and validated from
the CardTrader expansion catalog are accepted. Images are not downloaded, proxied or
stored as blobs.

## Operational Boundary

Provider calls run only from backend maintenance/backfill processes. Dashboard API
requests read resolved exact `card_images` rows and never call external providers.
CardTrader is not used for market prices, Cardmarket mappings or financial metrics.

## Validation

The current real collection has six Gold-Stamped cards resolved exactly with six valid
remote image URLs. The broader LOTR Art Series catalog contains 81 normal and 81
Gold-Stamped card Blueprints with unique Cardmarket Product IDs.
