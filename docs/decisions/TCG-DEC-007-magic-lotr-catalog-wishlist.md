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
`status=removed`; moving it to Collection increments or creates a collection item and
sets the wishlist row to `acquired`.

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
