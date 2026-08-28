# Database

SQLite remains the source of truth. The Multi-TCG migration is additive and preserves
all existing primary keys and historical price rows.

## Core Model

| Table | Purpose | Stable identity |
|---|---|---|
| `games` | TCG registry and catalog activation | `id`; unique `code` |
| `sets` | Provider-neutral release | `id`; unique `game_id + code` |
| `canonical_cards` | Logical card grouping | `id`; unique `game_id + identity_key` |
| `cards` | Physical printing | `id` |
| `*_external_ids` | Provider identifiers for sets, canonical cards and printings | provider-specific unique constraints |
| `printing_relations` | Explicit printing relationships | source + target + relation |
| `card_images` | Exact/fallback remote image metadata | printing + provider + requested language + face |
| `printing_price_resolutions` | Historical selected/null pricing decision | printing + language + timestamp + method |

One Piece commercial identity is canonical card + release + source variant/art kind +
language. It is an audit identity, not a replacement primary key. A collision keeps
both `cards.id` rows and marks them `catalog_status=ambiguous`.

## Counts

`printing_count` and `reprint_count` are derived by the API:

- `printing_count`: active printings for the canonical card, counting languages
  separately.
- `reprint_count`: active printings whose `release_kind` is exactly `reprint`.

`art_kind=alternate_art` does not imply reprint. A row may independently be both a
reprint and alternate art.

## Pricing

`printing_price_resolutions` preserves source currency and may contain a null selected
price. Supported methods are:

- `cardmarket_exact_language`
- `cardtrader_marketplace_low_median_5`
- `mixed_price_rejected`
- `no_exact_language_price`

The latest resolution is the current printing price. Mixed Cardmarket rows are audit
evidence only. No currency conversion occurs during import.

The manual pricing workflow writes `market_price_history` for Magic and
`printing_price_resolutions` for One Piece. It does not modify catalog, collection or
wishlist rows. CardTrader fingerprints are stored in resolution `metadata` so an
identical source response does not create duplicate historical rows.

## Safe Maintenance

```bash
python3 backend/scripts/audit_one_piece_legacy.py --db backend/db/tcg_dashboard.db
python3 backend/scripts/migrate_multi_tcg.py --db /path/to/local-copy.db --apply
python3 backend/scripts/import_one_piece_catalog.py \
  --db /path/to/local-copy.db --apply --with-prices --as-of YYYY-MM-DD
```

The One Piece importer is dry-run by default and repeatable. Run writes on a local
temporary copy when the project DB is mounted through bridge/FUSE. Sync back only after:

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

Never delete, merge or reassign an ambiguous printing through automated matching.

## Image display fallback

`card_images.language` is the requested/display language of the printing. The
additive `image_language_scope` records the actual language of the remote asset and
`is_language_fallback` identifies a cross-language visual fallback. A Japanese
printing may therefore display an English asset without changing its language,
identity or pricing. Only shared CardTrader Blueprint IDs or a unique complete
printing identity (`canonical_card_id + set_id + card_number + release_kind +
art_kind + source_variant`) qualify; card number/name alone never qualifies.
