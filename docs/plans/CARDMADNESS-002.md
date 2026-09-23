# CARDMADNESS-002 — Set reconciliation and Scryfall images

Status: complete (`2026-09-23`). Scope was limited to HOB/HOC set identity and
Scryfall image metadata. Prices, Wishlist, event links, valuations, Collection,
Pokémon, One Piece and LTR/LTC were not changed.

## Set reconciliation

The discrepancy was in CARDMADNESS-001's final report, not the database. That report
misallocated ten Surge printings between HOB and HOC while preserving the total of 75.
The CSV-driven importer and catalog rows were correct. Exact comparison by set,
collector number, English language and treatment confirms:

| Set | Canonical identities | Traditional Foil | Surge Foil | Printings |
|---|---:|---:|---:|---:|
| HOB | 50 | 50 | 35 | 85 |
| HOC | 66 | 66 | 40 | 106 |
| Total | 116 | 116 | 75 | 191 |

Every curated printing's `set_code` and `set_id` match its CSV set. No catalog rows
were reassigned or rebuilt. CARDMADNESS-001's per-set report has been corrected.

## Scryfall images

Each lookup used Scryfall's set + collector-number + English-language endpoint and
validated set code, numeric collector identity, language and Surge treatment where
applicable. Numeric leading-zero formatting is normalized only for lookup (for
example, CSV `044` maps to Scryfall `44`); the CSV/card collector value remains intact.
No name-based matching or cross-printing fallback is used. Image URLs pass through
`backend/images/resolver.py`; only URLs and source metadata are stored.

- HOB checked: 85; exact images: 85; missing: 0.
- HOC checked: 106; exact images: 101; missing: 5.
- Total exact: 186/191 (97.38%); ambiguous: 0.
- Exact matches carry Scryfall ID and per-printing collector number in `cards` and
  `card_images`. Five unresolved rows have NULL URLs and `status=missing`.
- Regression pairs all resolve independently by collector number: Smaug #229/#265,
  Gleaming Splendor #239/#275, The Lonely Mountain #248/#284, The One Ring #044/#084,
  Sauron, the Dark Lord #036/#076 and Minas Tirith #049/#089. Each pair has distinct
  Scryfall IDs and image URLs.

Unresolved English printings (Scryfall returned HTTP 404 for the exact English key):

- HOC #093 — Dwarven Warriors (Traditional Foil)
- HOC #094 — The Reaver Cleaver (Traditional Foil)
- HOC #095 — Arcane Signet (Traditional Foil)
- HOC #096 — Mox Amber (Traditional Foil)
- HOC #097 — Treasure Vault (Traditional Foil)

The preflight evidence in `reports/hobbit_preflight_2026-09-22/excluded_hoc_dwarvish.csv`
records these collector identities as Dwarvish-only. No alternate-language image was
used.

The generic Catalog and event Wishlist image paths consume `card_images`; no frontend
branch specific to HOB/HOC was added. API regression tests cover Catalog and event
Wishlist exposure, and the event-page test confirms the shared thumbnail renderer shows
the returned image.

## Database and verification

The image apply was performed against a local temporary copy. `cards` (Scryfall IDs
for exact matches) and `card_images` changed; SQLite's internal `sqlite_sequence`
counter advanced for the new image rows. No market observation, Wishlist, event
association, Collection or valuation rows changed.

- DB SHA256 before: `8386e36c2ec1a67c052f037cbca54f2a27413a84d40089633a5dd5af82d57e31`
- Validated copy SHA256 after: `1569c5af44a71b1b1053ac85f08874671130427b8913f2818307fef54715c253`
- `integrity_check`: `ok`; `foreign_key_check`: no rows.
- Image importer rerun: 186 exact rows were no-op, 0 writes; the five unresolved
  English lookups remain explicitly missing.
- Backend/API/database/importer/images/scripts/integrations: 269 passed, 6 subtests;
  frontend: 11 passed; frontend production build passed. Error registry and
  `git diff --check` passed.

## Next start

CARDMADNESS-003 — Wishlist del evento. Start with `docs/CURRENT_STATE.md` and this
plan, review the existing Wishlist, decide which printings to seek at Cardmadness,
then associate those existing `wishlist_items` with `cardmadness-2026`. Do not begin
that work during this closeout and do not create a parallel event list.
