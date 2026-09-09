# VAL-AVG30-006C — Candidate Backfill Manifest

- Readiness: `READY_FOR_PARTIAL_BACKFILL`
- Scope: `global / magic / base`
- as_of: `2026-09-08`
- SAFE_FOR_BACKFILL: `367`
- PROVENANCE_INCOMPLETE / rejected: `0`
- PROVENANCE_RECOVERABLE: `67`
- Provenance source: `{'market_price_history': 300, 'printing_price_resolutions': 67}`
- DB SHA-256: `4ad4736ddfae13931c634ff4c8b6e3b417a2359005e65b2e1729a0f29b336f3b`
- Manifest SHA-256: `946b36ee1ca55755774ef44c97fd464c1a564d43049ea5bcf752aa33e19887ba`

## Apply simulation

- rows_to_insert: `367`
- rows_to_update: `0`
- rows_unchanged: `0`
- rows_rejected: `0`

Only `valuation_status`, `valuation_method`, `valuation_value` and `reason` are candidate fields. `current_price` is not touched. No SQLite write occurred.

## Provenance gate

The original 367 eligible rows are all Magic catalog/base/ESTIMATED. `67` rows without history provenance were deterministically recovered from the unique prior `printing_price_resolutions` evidence tuple; no evidence was inferred or created. The resulting manifest contains all `367` safe rows.

NULL results remain NULL and are excluded from this manifest. Collection, Wishlist, Pokémon, One Piece and foil/alt remain outside scope.
