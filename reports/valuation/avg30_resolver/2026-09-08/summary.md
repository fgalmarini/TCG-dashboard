# VAL-AVG30-006 — Avg30 resolver dry-run

- as_of: `2026-09-08`
- read-only: `YES`
- recommendation: `NOT_READY_FOR_BACKFILL`
- eligible rows: `367`
- ineligible rows: `3150`

## Technical correctness vs usefulness

- technical resolver correctness: `PASS`
- backfill usefulness requires at least one eligible valuation in the proposed scope; no minimum coverage percentage is imposed.

## Coverage by scope and game

| Scope / game | Total | ESTIMATED | EXACT | NULL | Eligible | Coverage |
|---|---:|---:|---:|---:|---:|---:|
| catalog:magic | 2991 | 367 | 0 | 2624 | 367 | 12.27% |
| catalog:pokemon | 362 | 0 | 0 | 362 | 0 | 0.0% |
| collection:magic | 97 | 0 | 0 | 97 | 0 | 0.0% |
| collection:one_piece | 23 | 0 | 0 | 23 | 0 | 0.0% |
| collection:pokemon | 5 | 0 | 0 | 5 | 0 | 0.0% |
| wishlist:magic | 19 | 0 | 0 | 19 | 0 | 0.0% |
| wishlist:pokemon | 20 | 0 | 0 | 20 | 0 | 0.0% |

Observation age (days; min/max by group):

- `catalog:magic`: `5` / `10`
- `catalog:pokemon`: `None` / `None`
- `collection:magic`: `5` / `10`
- `collection:one_piece`: `10` / `10`
- `collection:pokemon`: `None` / `None`
- `wishlist:magic`: `5` / `8`
- `wishlist:pokemon`: `None` / `None`

## NULL reasons

- `FINISH_UNRESOLVED`: 14
- `IDENTITY_UNRESOLVED`: 1050
- `LANGUAGE_UNRESOLVED`: 97
- `MISSING_AVG30`: 303
- `PRODUCT_UNRESOLVED`: 1686
- `VARIANT_UNRESOLVED`: 0

## Portfolio simulation

| Scope | Legacy value | Proposed Avg30 value | Valued units | Unvalued units | Coverage |
|---|---:|---:|---:|---:|---:|
| collection | EUR 223.78 | EUR 0.00 | 0 | 128 | 0.0% |
| wishlist | EUR 155.25 | EUR 0.00 | 0 | 39 | 0.0% |

## Backfill usefulness by scope

- `catalog:magic`: `READY_FOR_BACKFILL`
- `catalog:pokemon`: `NOT_READY_FOR_BACKFILL`
- `collection:magic`: `NOT_READY_FOR_BACKFILL`
- `collection:one_piece`: `NOT_READY_FOR_BACKFILL`
- `collection:pokemon`: `NOT_READY_FOR_BACKFILL`
- `wishlist:magic`: `NOT_READY_FOR_BACKFILL`
- `wishlist:pokemon`: `NOT_READY_FOR_BACKFILL`

## Audited examples

- `ESTIMATED`: magic / Gandalf the Grey / product `1`
- `POKEMON_FINISH_UNRESOLVED`: no encontrado en este run
- `ONE_PIECE_LANGUAGE_UNRESOLVED`: no encontrado en este run
- `MAGIC_NONFOIL`: magic / Gandalf the Grey / product `1`
- `MAGIC_FOIL_RESOLVED`: no encontrado en este run
- `MAGIC_FOIL_BLOCKED`: magic / Tale of Tinúviel / product `208`
- `MISSING_AVG30`: magic / Gandalf the Grey / product `8`
