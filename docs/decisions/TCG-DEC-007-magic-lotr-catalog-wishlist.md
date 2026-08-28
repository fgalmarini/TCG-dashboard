# TCG-DEC-007 — Magic LOTR Catalog + Wishlist

## Status

Implemented.

## Decision

Use the existing `cards` table as the canonical physical Magic catalog. Collection
and wishlist rows reference it through their existing `card_id` foreign key instead of
duplicating card metadata.

The initial catalog scope is physical LTR and LTC printings. Each real Scryfall finish
is represented independently. Treatment is descriptive metadata and never participates
in identity.

## Wishlist

Use `wishlist_items` with active wanted-card uniqueness. Removing an item sets
`status=removed` and records `removed_at`. Marking an item acquired sets
`status=acquired` and records `acquired_at`; it never creates or modifies a Collection
row. Historical acquired/removed rows can be explicitly restored to `wanted`, clearing
both transition timestamps.

Wishlist planning fields include optional `target_price` and `max_price`, with
`target_price <= max_price` enforced when both exist. The global wishlist summary
counts wanted/acquired rows, counts wanted rows missing prices or canonical matches,
and estimates only wanted rows using `current_price * quantity_wanted`.

Unmatched wishlist rows are not supported: `wishlist_items.card_id` remains NOT NULL.
Manual catalog resolution is supported for unmatched Collection rows and updates a
shared Cardmarket mapping only when that mapping is demonstrably legacy and unused by
other Collection rows; otherwise it only relinks the Collection row.

## Price and source rules

Scryfall supplies Magic catalog metadata and images through controlled paginated live
requests, local cache or fixtures. Cardmarket remains the price source. Catalog and
wishlist prices are NULL unless exactly one mapped Cardmarket product has a current
snapshot; ambiguous products are never selected.

## Scope

Included: Magic LOTR LTR/LTC physical printings, variants, Showcase, Borderless,
Extended Art, Surge Foil, Prerelease, Realms & Relics and Scene cards when identifiable
from source metadata/collector ranges.

Excluded: tokens, Art Series, digital cards, Secret Lair, sealed products, Pokémon,
One Piece, currency conversion and mass catalog price refresh.
