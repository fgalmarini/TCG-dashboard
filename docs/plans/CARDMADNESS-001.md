# CARDMADNESS-001 — Curated catalog and event Wishlist

Status: complete (`2026-09-23`).

## Contract

- Import only the user-curated rows in `CARDMADNESS_HOB_HOC.csv`; this is not full
  HOB/HOC set coverage.
- 116 logical identities: 50 HOB and 66 HOC. English only; Traditional Foil for all
  identities and Surge Foil only where the CSV gives a Surge number: 191 physical
  printings total. No Non-Foil printings.
- Traditional and Surge printings share the dataset-defined canonical identity.
- Manual Cardmarket observations are dated 2026-09-23, use snapshot key
  `cardmadness-2026-09-23`, and live only in `market_price_observations`. They are not
  global portfolio valuation or `current_price`; no Cardmarket product mapping is
  created.
- `events` and `event_wishlist_items` provide reusable event scoping. Wishlist is the
  sole source of card status, quantity, priority and target/max prices.
- First event: `cardmadness-2026` / `CARDMADNESS EVENT`, at `/events/cardmadness-2026`.

## Import and API

The read-only source-scope investigation and reconciliation evidence is retained in
`reports/hobbit_preflight_2026-09-22/`; it records the broader source checklist and
exclusions that informed the deliberately curated import. It contains no database
copy or temporary output.

Dry-run by default:

```bash
python3 backend/scripts/import_curated_magic_catalog.py --db /path/to/local-copy.db
python3 backend/scripts/import_curated_magic_catalog.py --db /path/to/local-copy.db --apply
```

The API lists only associated items at `GET /api/events/cardmadness-2026/wishlist`.
Associate a pre-existing item with `POST` to the same path and JSON body
`{"wishlist_item_id": 123}`; remove the association with
`DELETE /api/events/cardmadness-2026/wishlist/123`. Item status transitions continue
through the existing Wishlist endpoints.

The event view compares manual Surge Low/Avg30 with Traditional Foil Low only when
the canonical identity, set, English language and treatment resolve exactly. Missing
observations render as `—`.

## Verification

Acceptance targets: 86 non-null observations; 61 printings with at least one
observation after exact database mapping; Smaug the Magnificent HOB Surge #265 keeps
Low 24999.99 EUR and Avg30 10100.00 EUR. Import reruns must add no observations.
Verified: HOB 50 identities / 85 printings (35 Surge); HOC 66 identities / 106
printings (40 Surge); 116 identities / 191 printings total. The snapshot has 86 observations across 61 printings
(61 Low, 25 Avg30); the second import inserted none. Smaug #265 retains the exact
values above. The event exists once and currently has zero Wishlist associations.
Backend suite: 254 passed; frontend suite: 11 passed; frontend build, error registry
verifier, DB integrity/foreign-key checks and `git diff --check` passed.

DB SHA256 changed from
`d667fdf63b66a71a4dedbbd1893ca00f5bd357cf1fe42d0d57caef2b43295607` to
`8386e36c2ec1a67c052f037cbca54f2a27413a84d40089633a5dd5af82d57e31`.
Database data changed in `sets`, `expansions`, `canonical_cards`, `cards`,
`market_price_observations` and `events`; `event_wishlist_items` was created and is
empty. The expansions table was rebuilt additively to permit NULL Cardmarket expansion
IDs. No Cardmarket product IDs or product mappings were added.

## Next session

CARDMADNESS-003 — Wishlist del evento. Start with `docs/CURRENT_STATE.md` and
`docs/plans/CARDMADNESS-002.md`; review the existing Wishlist, decide which printings
to seek at Cardmadness, then associate those existing `wishlist_items` with
`cardmadness-2026` through the event API. Do not create a parallel event wishlist.
