# Sprint Contract — Multi-TCG Foundation + One Piece Catalog

Status: Implemented  
Catalog cutoff: 2026-08-27

## Locked Scope

- Additive schema only; `cards.id` remains the internal physical-printing identity.
- Add neutral sets, canonical cards, provider external IDs, printing relationships and
  generic price-resolution history.
- Import One Piece catalog before personal Collection; keep EN/JP separate.
- No fuzzy matching, scraping, currency conversion or personal One Piece Collection
  import.
- Cardmarket exact language first; CardTrader exact Blueprint/language median-5 second;
  otherwise null. Mixed Cardmarket prices are audit-only.
- Preserve all 11,502 legacy One Piece rows and the complete Magic LOTR behavior.

## Acceptance Result

Implemented in schema, migration, provider adapter, importer, API and UI. The real
before/after evidence is versioned in
[`docs/audits/one-piece-catalog-2026-08-27.json`](../audits/one-piece-catalog-2026-08-27.json).
Architecture and source policy are recorded in
[`TCG-DEC-008`](../decisions/TCG-DEC-008-multi-tcg-one-piece-foundation.md).

The second import created zero rows. SQLite integrity/FK checks and the required Magic
regression passed before the validated local copy replaced the project database.
